// Main process entry point for GOGRepoc Electron application

const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const log = require('electron-log');
const Store = require('electron-store');
const { getBackendExecutablePath, normalizePath } = require('./path-utils');
const { createMenuTemplate } = require('./menu-template');
const { getStoreConfig, validateWindowBounds: validateWindowBoundsSchema } = require('./settings-schema');

// Initialize electron-store for settings persistence
// Task 12.1: Use settings schema with defaults and validation
// Requirements: 15.3 (store in platform-appropriate location), 15.4 (use sensible defaults)
const store = new Store(getStoreConfig());

// Configure electron-log
log.transports.file.level = 'info';
log.transports.file.maxSize = 10 * 1024 * 1024; // 10MB
log.transports.file.format = '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}';

// Determine if running in development mode
const isDevelopment = process.env.NODE_ENV === 'development' || 
                      process.argv.includes('--dev') || 
                      (typeof app !== 'undefined' && app && !app.isPackaged);

// Global state
let mainWindow = null;
let backendProcess = null;
let backendPort = null;
let isShuttingDown = false;
let backendRestartCount = 0;
const MAX_AUTO_RESTARTS = 3;

/**
 * Find an available port in the range 8000-9000
 * @returns {Promise<number>} Available port number
 */
async function findAvailablePort() {
  const MIN_PORT = 8000;
  const MAX_PORT = 9000;

  for (let port = MIN_PORT; port <= MAX_PORT; port++) {
    if (await isPortAvailable(port)) {
      log.info(`Found available port: ${port}`);
      return port;
    }
  }

  throw new Error(`No available ports found in range ${MIN_PORT}-${MAX_PORT}`);
}

/**
 * Check if a port is available
 * @param {number} port - Port to check
 * @returns {Promise<boolean>} True if port is available
 */
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(false);
      } else {
        resolve(false);
      }
    });

    server.once('listening', () => {
      server.close();
      resolve(true);
    });

    server.listen(port, '127.0.0.1');
  });
}

/**
 * Start the Python backend subprocess
 * @returns {Promise<number>} Port number the backend is running on
 */
async function startBackend() {
  log.info('Starting backend subprocess...');

  // Find an available port
  const port = await findAvailablePort();
  backendPort = port;

  // Get backend executable path (from path-utils module)
  const backendPath = getBackendExecutablePath();
  
  if (!backendPath) {
    // Development mode - backend should be running separately
    log.info('Development mode: skipping backend spawn, expecting backend on port 8000');
    backendPort = 8000;
    return backendPort;
  }

  // Spawn the backend process
  log.info(`Spawning backend: ${backendPath} --port ${port}`);
  
  backendProcess = spawn(backendPath, ['--port', port.toString(), '--host', '127.0.0.1'], {
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  // Capture stdout
  backendProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    if (output) {
      log.info(`[Backend stdout] ${output}`);
    }
  });

  // Capture stderr
  backendProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    if (output) {
      log.error(`[Backend stderr] ${output}`);
    }
  });

  // Handle process exit
  backendProcess.on('exit', (code, signal) => {
    log.info(`Backend process exited with code ${code}, signal ${signal}`);
    
    if (!isShuttingDown && code !== 0) {
      log.error('Backend crashed unexpectedly');
      // Task 11.2: Implement crash recovery
      handleBackendCrash(code, signal).catch(err => {
        log.error('Error in crash recovery handler:', err);
      });
    }
    
    backendProcess = null;
  });

  // Handle spawn errors
  backendProcess.on('error', (err) => {
    log.error('Failed to spawn backend process:', err);
    throw err;
  });

  log.info(`Backend subprocess started with PID ${backendProcess.pid}`);
  return port;
}

/**
 * Stop the backend subprocess gracefully
 * @returns {Promise<void>}
 */
async function stopBackend() {
  if (!backendProcess) {
    log.info('No backend process to stop');
    return;
  }

  log.info('Stopping backend subprocess...');

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      if (backendProcess) {
        log.warn('Backend did not exit gracefully, forcing kill');
        backendProcess.kill('SIGKILL');
      }
      resolve();
    }, 5000); // 5 second timeout

    backendProcess.once('exit', () => {
      clearTimeout(timeout);
      log.info('Backend subprocess stopped');
      resolve();
    });

    // Send SIGTERM for graceful shutdown
    backendProcess.kill('SIGTERM');
  });
}

/**
 * Wait for the backend to be ready by polling the health endpoint
 * @param {number} port - Port the backend is running on
 * @param {number} maxAttempts - Maximum number of health check attempts (default 10)
 * @returns {Promise<boolean>} True if backend is ready
 * @throws {Error} If backend doesn't respond within timeout
 */
async function waitForBackend(port, maxAttempts = 10) {
  const url = `http://localhost:${port}/health`;
  log.info(`Waiting for backend health check at ${url}`);

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      log.info(`Health check attempt ${attempt + 1}/${maxAttempts}`);
      
      const response = await fetch(url, {
        method: 'GET',
        signal: AbortSignal.timeout(5000) // 5 second timeout per request
      });

      if (response.ok) {
        log.info('Backend health check passed');
        return true;
      } else {
        log.warn(`Health check returned status ${response.status}`);
      }
    } catch (error) {
      log.warn(`Health check attempt ${attempt + 1} failed: ${error.message}`);
    }

    // Exponential backoff with cap at 10 seconds
    // Delays: 1s, 2s, 4s, 8s, 10s, 10s, ...
    if (attempt < maxAttempts - 1) {
      const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
      log.info(`Waiting ${delay}ms before next attempt`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  const error = new Error(`Backend failed to respond to health checks after ${maxAttempts} attempts (timeout: 30s)`);
  log.error(error.message);
  throw error;
}

/**
 * Handle backend startup errors
 * Task 11.1: Implement backend startup error handling
 * Requirements: 3.5 (detect backend failure and notify user), 10.4 (provide actionable error info), 10.5 (display user-friendly error dialogs)
 * 
 * @param {Error} error - The error that occurred during backend startup
 * @param {number|null} port - Port number attempted (may be null if port finding failed)
 * @param {string|null} backendPath - Path to backend executable (may be null in dev mode)
 * @returns {Promise<void>}
 */
async function handleBackendStartupError(error, port, backendPath) {
  const { shell } = require('electron');
  
  log.error('Backend startup failed', { 
    error: error.message, 
    stack: error.stack,
    port, 
    backendPath 
  });
  
  // Build diagnostic information
  const diagnosticInfo = [
    `Error: ${error.message}`,
    port ? `Port: ${port}` : 'Port: Not assigned',
    backendPath ? `Path: ${backendPath}` : 'Path: Development mode (no bundled backend)',
    `Platform: ${process.platform}`,
    `Log file: ${log.transports.file.getFile().path}`
  ].join('\n');
  
  // Display error dialog with options
  const response = await dialog.showMessageBox({
    type: 'error',
    title: 'Backend Startup Failed',
    message: 'The GOGRepoc backend failed to start.',
    detail: diagnosticInfo,
    buttons: ['Retry', 'View Logs', 'Exit'],
    defaultId: 0,  // Default to Retry
    cancelId: 2    // Cancel means Exit
  });
  
  // Handle user choice
  switch (response.response) {
    case 0: // Retry
      log.info('User chose to retry backend startup');
      try {
        // Kill any existing backend process before retrying
        if (backendProcess) {
          log.info('Killing existing backend process before retry');
          backendProcess.kill('SIGKILL');
          backendProcess = null;
        }
        
        // Try to start backend with a new port
        const newPort = await startBackend();
        await waitForBackend(newPort);
        
        log.info('Backend started successfully after retry');
        return; // Success, continue with app startup
        
      } catch (retryError) {
        log.error('Retry failed:', retryError);
        // Recursive call to show error dialog again
        return handleBackendStartupError(retryError, backendPort, backendPath);
      }
      
    case 1: // View Logs
      log.info('User chose to view logs');
      try {
        const logPath = log.transports.file.getFile().path;
        await shell.openPath(logPath);
        log.info(`Opened log file: ${logPath}`);
      } catch (openError) {
        log.error('Failed to open log file:', openError);
      }
      
      // After viewing logs, show the error dialog again
      return handleBackendStartupError(error, port, backendPath);
      
    case 2: // Exit
      log.info('User chose to exit application');
      app.quit();
      break;
      
    default:
      log.warn(`Unexpected dialog response: ${response.response}`);
      app.quit();
  }
}

/**
 * Handle backend crashes during runtime
 * Task 11.2: Implement backend crash detection and recovery
 * Requirements: 3.5 (detect backend failure and notify user), 3.6 (log error and provide restart options)
 * 
 * Implements automatic restart with exponential backoff, limited to 3 attempts.
 * After max restarts exceeded, displays error dialog requiring manual intervention.
 * 
 * @param {number} exitCode - Exit code from the crashed process
 * @param {string|null} signal - Signal that terminated the process (if any)
 * @returns {Promise<void>}
 */
async function handleBackendCrash(exitCode, signal) {
  const { shell } = require('electron');
  
  log.error('Backend crashed during runtime', { 
    exitCode, 
    signal, 
    restartCount: backendRestartCount,
    maxRestarts: MAX_AUTO_RESTARTS
  });
  
  // Check if we should attempt automatic restart
  if (backendRestartCount < MAX_AUTO_RESTARTS) {
    backendRestartCount++;
    
    // Calculate exponential backoff delay: 1s, 2s, 4s
    // Delays: 2^0 = 1s, 2^1 = 2s, 2^2 = 4s
    const delay = 1000 * Math.pow(2, backendRestartCount - 1);
    
    log.info(`Attempting automatic restart ${backendRestartCount}/${MAX_AUTO_RESTARTS} after ${delay}ms delay`);
    
    // Show notification to user (non-blocking)
    if (mainWindow && mainWindow.webContents) {
      mainWindow.webContents.send('backend-restarting', {
        attempt: backendRestartCount,
        maxAttempts: MAX_AUTO_RESTARTS,
        delay
      });
    }
    
    // Wait for exponential backoff delay
    await new Promise(resolve => setTimeout(resolve, delay));
    
    try {
      // Attempt to restart backend
      log.info('Starting backend after crash...');
      const newPort = await startBackend();
      await waitForBackend(newPort);
      
      // Success! Reset restart counter
      log.info('Backend restarted successfully after crash');
      backendRestartCount = 0;
      
      // Update global backend URL
      global.backendUrl = `http://localhost:${newPort}`;
      
      // Notify renderer of successful restart
      if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send('backend-restarted', {
          url: global.backendUrl
        });
      }
      
      return; // Success
      
    } catch (restartError) {
      log.error(`Automatic restart attempt ${backendRestartCount} failed:`, restartError);
      
      // If we haven't hit max restarts yet, the next crash will trigger another attempt
      // If we have hit max restarts, fall through to show error dialog
      if (backendRestartCount < MAX_AUTO_RESTARTS) {
        return; // Will try again on next crash
      }
    }
  }
  
  // Max restarts exceeded or all attempts failed
  log.error(`Backend has crashed ${backendRestartCount} times, requiring manual intervention`);
  
  // Build diagnostic information
  const diagnosticInfo = [
    `The backend has crashed multiple times and automatic restart has failed.`,
    `Exit code: ${exitCode}`,
    signal ? `Signal: ${signal}` : '',
    `Restart attempts: ${backendRestartCount}`,
    `Log file: ${log.transports.file.getFile().path}`,
    '',
    'Please check the logs for more information.'
  ].filter(line => line).join('\n');
  
  // Display error dialog requiring manual intervention
  const response = await dialog.showMessageBox(mainWindow || null, {
    type: 'error',
    title: 'Backend Repeatedly Crashing',
    message: 'The GOGRepoc backend has crashed multiple times.',
    detail: diagnosticInfo,
    buttons: ['View Logs', 'Restart Backend', 'Exit'],
    defaultId: 1,  // Default to Restart Backend
    cancelId: 2    // Cancel means Exit
  });
  
  // Handle user choice
  switch (response.response) {
    case 0: // View Logs
      log.info('User chose to view logs after repeated crashes');
      try {
        const logPath = log.transports.file.getFile().path;
        await shell.openPath(logPath);
        log.info(`Opened log file: ${logPath}`);
      } catch (openError) {
        log.error('Failed to open log file:', openError);
      }
      
      // After viewing logs, show the error dialog again
      return handleBackendCrash(exitCode, signal);
      
    case 1: // Restart Backend
      log.info('User chose to manually restart backend after repeated crashes');
      
      // Reset restart counter for manual restart
      backendRestartCount = 0;
      
      try {
        // Kill any existing backend process
        if (backendProcess) {
          log.info('Killing existing backend process before manual restart');
          backendProcess.kill('SIGKILL');
          backendProcess = null;
        }
        
        // Attempt to start backend
        const newPort = await startBackend();
        await waitForBackend(newPort);
        
        log.info('Backend restarted successfully after manual intervention');
        
        // Update global backend URL
        global.backendUrl = `http://localhost:${newPort}`;
        
        // Notify renderer of successful restart
        if (mainWindow && mainWindow.webContents) {
          mainWindow.webContents.send('backend-restarted', {
            url: global.backendUrl
          });
        }
        
        return; // Success
        
      } catch (restartError) {
        log.error('Manual restart failed:', restartError);
        
        // Show startup error dialog
        const backendPath = getBackendExecutablePath();
        return handleBackendStartupError(restartError, backendPort, backendPath);
      }
      
    case 2: // Exit
      log.info('User chose to exit application after repeated backend crashes');
      app.quit();
      break;
      
    default:
      log.warn(`Unexpected dialog response: ${response.response}`);
      app.quit();
  }
}

/**
 * Validate and sanitize window bounds to ensure window is visible on screen
 * Handles edge cases: window off-screen, invalid bounds
 * Task 12.1: Use settings schema validation
 * @param {Object} bounds - Window bounds to validate
 * @returns {Object} Validated bounds
 */
function validateWindowBounds(bounds) {
  const { screen } = require('electron');
  
  // Use settings schema validation with screen module
  return validateWindowBoundsSchema(bounds, screen);
}

/**
 * Save current window bounds to persistent storage
 * Implements Task 6.2: Save window bounds to electron-store on close
 * Requirements: 9.2, 15.5
 */
function saveWindowBounds() {
  if (!mainWindow) {
    return;
  }
  
  try {
    const bounds = mainWindow.getBounds();
    log.info(`Saving window bounds: ${JSON.stringify(bounds)}`);
    store.set('windowBounds', bounds);
  } catch (error) {
    log.error('Failed to save window bounds:', error);
  }
}

/**
 * Handle directory selection from menu
 * Task 10.1: Wire "Select Download Directory" to IPC directory selection
 * Requirement 14.2: When user selects "Select Download Directory" from File menu, display native dialog
 */
async function handleMenuSelectDirectory() {
  try {
    log.info('Menu: Select Download Directory clicked');
    
    if (!mainWindow) {
      log.error('Menu: Cannot select directory, mainWindow is null');
      return;
    }
    
    // Get last selected directory from settings
    const lastDirectory = store.get('lastDirectory');
    
    // Show native directory selection dialog
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
      defaultPath: lastDirectory || undefined,
      title: 'Select Download Directory'
    });
    
    // Handle cancellation
    if (result.canceled) {
      log.info('Menu: Directory selection cancelled by user');
      return;
    }
    
    // Handle successful selection
    if (result.filePaths && result.filePaths.length > 0) {
      const selectedPath = result.filePaths[0];
      log.info(`Menu: Directory selected: ${selectedPath}`);
      
      // Save to settings
      store.set('lastDirectory', selectedPath);
      
      // Notify renderer of the new directory
      if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send('directory-selected', selectedPath);
      }
    }
  } catch (error) {
    log.error('Menu: Error in directory selection:', error);
  }
}

/**
 * Create and set the application menu
 * Task 10.1: Create menu template
 * Requirements: 14.1, 14.4, 14.5
 */
function createApplicationMenu() {
  const menuTemplate = createMenuTemplate({
    isDevelopment,
    mainWindow,
    onSelectDirectory: handleMenuSelectDirectory
  });
  
  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);
  
  log.info('Application menu created');
}

/**
 * Create the main application window
 * Implements Task 6.1: Create main application window
 * Implements Task 6.2: Load saved window bounds from electron-store on startup
 * Requirements: 9.1 (minimum size 1024x768), 9.2 (remember size and position), 9.3 (title), 9.5 (window controls), 15.5 (window state persistence)
 */
function createWindow() {
  // Load saved window bounds
  const savedBounds = store.get('windowBounds');
  log.info(`Loaded saved window bounds: ${JSON.stringify(savedBounds)}`);
  
  // Validate and sanitize bounds (handles edge cases: off-screen, invalid bounds)
  const bounds = validateWindowBounds(savedBounds);
  log.info(`Using validated window bounds: ${JSON.stringify(bounds)}`);
  
  mainWindow = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    minWidth: 1024,  // Requirement 9.1: minimum width 1024
    minHeight: 768,  // Requirement 9.1: minimum height 768
    title: 'GOGRepoc',  // Requirement 9.3: window title
    webPreferences: {
      nodeIntegration: false,  // Security: disable node integration
      contextIsolation: true,  // Security: enable context isolation
      preload: path.join(__dirname, 'preload.js')
    }
    // Requirement 9.5: Standard window controls (minimize, maximize, close) are enabled by default
  });

  // Store backend URL for renderer
  global.backendUrl = `http://localhost:${backendPort}`;

  // Load index.html from build directory
  // For now, using renderer directory as placeholder until React build is integrated
  const indexPath = path.join(__dirname, 'renderer', 'index.html');
  log.info(`Loading index.html from: ${indexPath}`);
  mainWindow.loadFile(indexPath);

  // Open DevTools in development mode
  if (isDevelopment) {
    mainWindow.webContents.openDevTools();
  }

  // Save window bounds when window is resized or moved
  // Debounce to avoid excessive writes
  let saveBoundsTimeout = null;
  const debouncedSave = () => {
    if (saveBoundsTimeout) {
      clearTimeout(saveBoundsTimeout);
    }
    saveBoundsTimeout = setTimeout(() => {
      saveWindowBounds();
    }, 500); // Save 500ms after last resize/move
  };
  
  mainWindow.on('resize', debouncedSave);
  mainWindow.on('move', debouncedSave);
  
  // Task 6.4: Implement window close handler
  // Requirements: 9.4 - When user closes window, terminate backend subprocess before exiting
  mainWindow.on('close', async (event) => {
    // Clear any pending save timeout
    if (saveBoundsTimeout) {
      clearTimeout(saveBoundsTimeout);
    }
    
    // Save window state before closing
    saveWindowBounds();
    
    // If we're already shutting down, allow the close
    if (isShuttingDown) {
      return;
    }
    
    // Prevent the window from closing immediately
    event.preventDefault();
    
    // Mark that we're shutting down
    isShuttingDown = true;
    log.info('Window close requested, initiating shutdown');
    
    // Trigger backend subprocess termination
    try {
      await stopBackend();
      log.info('Backend stopped, closing window');
    } catch (error) {
      log.error('Error stopping backend during window close:', error);
    }
    
    // Now allow the window to close
    mainWindow.destroy();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  log.info('Main window created with minimum size 1024x768');
  
  // Create application menu
  // Task 10.1: Create menu template
  createApplicationMenu();
}

// ============================================================================
// IPC Handlers
// Task 8.2: Implement IPC handlers in main process
// Requirements: 6.1 (IPC handlers for native operations), 6.3 (directory selection), 6.5 (no arbitrary code execution)
// ============================================================================

/**
 * Register all IPC handlers
 * Should be called after app is ready
 */
function registerIpcHandlers() {
  // Skip registration if ipcMain is not available (e.g., in test environment)
  if (!ipcMain) {
    log.warn('ipcMain not available, skipping IPC handler registration');
    return;
  }
  
  /**
   * Register 'select-directory' handler with native dialog
   * Requirement 6.3: When renderer requests directory selection, main process handles native dialog and returns result
   * Requirement 5.1: Display native dialog for directory selection
   * Requirement 5.3: Return absolute path to renderer
   * Requirement 5.4: Remember last selected directory
   * Requirement 5.5: Handle cancellation gracefully
   */
  ipcMain.handle('select-directory', async () => {
    try {
      log.info('IPC: select-directory called');
      
      if (!mainWindow) {
        log.error('IPC: select-directory called but mainWindow is null');
        return { success: false, error: 'Main window not available' };
      }
      
      // Get last selected directory from settings
      const lastDirectory = store.get('lastDirectory');
      log.info(`IPC: Last directory from settings: ${lastDirectory}`);
      
      // Show native directory selection dialog
      const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
        defaultPath: lastDirectory || undefined
      });
      
      // Handle cancellation
      if (result.canceled) {
        log.info('IPC: Directory selection cancelled by user');
        return { success: false, error: 'User cancelled' };
      }
      
      // Handle successful selection
      if (result.filePaths && result.filePaths.length > 0) {
        const selectedPath = result.filePaths[0];
        log.info(`IPC: Directory selected: ${selectedPath}`);
        
        // Save to settings for next time
        store.set('lastDirectory', selectedPath);
        
        return { success: true, path: selectedPath };
      }
      
      // Unexpected case: not cancelled but no paths
      log.warn('IPC: Dialog not cancelled but no paths returned');
      return { success: false, error: 'No directory selected' };
      
    } catch (error) {
      log.error('IPC: Error in select-directory handler:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Register 'get-backend-url' handler to return backend URL
   * Requirement 7.2: Main process provides backend URL to renderer via IPC
   */
  ipcMain.handle('get-backend-url', async () => {
    try {
      log.info('IPC: get-backend-url called');
      
      const backendUrl = global.backendUrl;
      
      if (!backendUrl) {
        log.error('IPC: Backend URL not available');
        return { success: false, error: 'Backend URL not available' };
      }
      
      log.info(`IPC: Returning backend URL: ${backendUrl}`);
      return { success: true, url: backendUrl };
      
    } catch (error) {
      log.error('IPC: Error in get-backend-url handler:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Register 'get-setting' handler for settings access
   * Requirement 15.2: Load settings on app startup
   */
  ipcMain.handle('get-setting', async (event, key) => {
    try {
      log.info(`IPC: get-setting called with key: ${key}`);
      
      if (!key || typeof key !== 'string') {
        log.error('IPC: Invalid setting key');
        return { success: false, error: 'Invalid setting key' };
      }
      
      const value = store.get(key);
      log.info(`IPC: Setting '${key}' = ${JSON.stringify(value)}`);
      
      return { success: true, value };
      
    } catch (error) {
      log.error(`IPC: Error in get-setting handler for key '${key}':`, error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Register 'set-setting' handler for settings access
   * Requirement 15.1: Save user settings to persistent storage
   */
  ipcMain.handle('set-setting', async (event, key, value) => {
    try {
      log.info(`IPC: set-setting called with key: ${key}, value: ${JSON.stringify(value)}`);
      
      if (!key || typeof key !== 'string') {
        log.error('IPC: Invalid setting key');
        return { success: false, error: 'Invalid setting key' };
      }
      
      store.set(key, value);
      log.info(`IPC: Setting '${key}' saved successfully`);
      
      return { success: true };
      
    } catch (error) {
      log.error(`IPC: Error in set-setting handler for key '${key}':`, error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Register 'get-version' handler to return app version
   */
  ipcMain.handle('get-version', async () => {
    try {
      log.info('IPC: get-version called');
      
      const version = app.getVersion();
      log.info(`IPC: Returning app version: ${version}`);
      
      return { success: true, version };
      
    } catch (error) {
      log.error('IPC: Error in get-version handler:', error);
      return { success: false, error: error.message };
    }
  });
  
  log.info('IPC handlers registered');
}

// App lifecycle handlers
if (app && app.whenReady) {
  app.whenReady().then(async () => {
    log.info(`GOGRepoc starting in ${isDevelopment ? 'development' : 'production'} mode`);
    log.info(`Electron version: ${process.versions.electron}`);
    log.info(`Node version: ${process.versions.node}`);
    log.info(`Platform: ${process.platform}`);
    log.info(`App path: ${app.getAppPath()}`);
    log.info(`User data path: ${app.getPath('userData')}`);
    log.info(`Log file path: ${log.transports.file.getFile().path}`);

    // Register IPC handlers
    registerIpcHandlers();

    try {
      // Start backend subprocess
      const port = await startBackend();
      
      // Wait for backend to be ready
      await waitForBackend(port);
      
      // Backend is ready, create window
      createWindow();
    } catch (error) {
      log.error('Failed to start application:', error);
      
      // Task 11.1: Handle backend startup error with user-friendly dialog
      const backendPath = getBackendExecutablePath();
      await handleBackendStartupError(error, backendPort, backendPath);
    }

    app.on('activate', () => {
      // On macOS, re-create window when dock icon is clicked and no windows are open
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  });

  // Quit when all windows are closed (except on macOS)
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });

  // Handle app quit
  // Note: Window close handler (Task 6.4) now handles backend shutdown
  // This handler is for cases where app.quit() is called directly (e.g., from menu)
  app.on('before-quit', async (event) => {
    if (!isShuttingDown) {
      event.preventDefault();
      isShuttingDown = true;
      log.info('Application shutting down via before-quit');
      
      // Stop backend before quitting
      await stopBackend();
      
      // Now quit for real
      app.quit();
    }
  });
}

// Export for testing
module.exports = {
  store,
  log,
  isDevelopment,
  findAvailablePort,
  startBackend,
  stopBackend,
  waitForBackend,
  handleBackendStartupError,
  handleBackendCrash,
  validateWindowBounds,
  saveWindowBounds,
  registerIpcHandlers,
  handleMenuSelectDirectory,
  createApplicationMenu,
  MAX_AUTO_RESTARTS,
  // Test helpers
  setMainWindow: (window) => { mainWindow = window; },
  getMainWindow: () => mainWindow,
  getBackendRestartCount: () => backendRestartCount,
  setBackendRestartCount: (count) => { backendRestartCount = count; },
  resetBackendRestartCount: () => { backendRestartCount = 0; }
};
