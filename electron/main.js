// Main process entry point for GOGRepoc Electron application
// This file will be expanded in subsequent tasks

const { app, BrowserWindow } = require('electron');
const path = require('path');

// Placeholder for main window
let mainWindow = null;

// Determine if running in development mode
const isDevelopment = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');

/**
 * Create the main application window
 * This is a placeholder implementation that will be expanded in Task 6
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1024,
    height: 768,
    minWidth: 800,
    minHeight: 600,
    title: 'GOGRepoc',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Load a placeholder HTML file for now
  // In later tasks, this will load the React app
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Open DevTools in development mode
  if (isDevelopment) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App lifecycle handlers
app.whenReady().then(() => {
  createWindow();

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

// Log startup mode
console.log(`GOGRepoc starting in ${isDevelopment ? 'development' : 'production'} mode`);
