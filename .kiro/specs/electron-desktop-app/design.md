# Design Document: Electron Desktop Application for GOGRepoc

## Overview

This design describes the architecture and implementation approach for packaging the GOGRepoc Python application as a cross-platform Electron desktop application. The solution bundles a PyInstaller-packaged Python backend with an Electron frontend, providing seamless process management, native OS integrations, and a single-file distribution model.

### Key Design Decisions

1. **Hybrid Architecture**: Electron frontend + Python backend subprocess
2. **PyInstaller for Python Bundling**: Creates standalone executables without requiring Python installation
3. **Dynamic Port Assignment**: Backend runs on a random available port to avoid conflicts
4. **Health Check Pattern**: Ensures backend is ready before showing UI
5. **IPC with Context Isolation**: Secure communication between Electron processes
6. **Electron Builder**: Cross-platform packaging and distribution

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Application                      │
│                                                              │
│  ┌────────────────────┐         ┌─────────────────────┐    │
│  │   Main Process     │         │  Renderer Process   │    │
│  │                    │         │                     │    │
│  │  - Window Mgmt     │◄───IPC──┤  - React UI         │    │
│  │  - Subprocess Mgmt │         │  - API Client       │    │
│  │  - Native Dialogs  │         │  - User Interface   │    │
│  │  - Health Checks   │         │                     │    │
│  └─────────┬──────────┘         └─────────────────────┘    │
│            │                                                 │
│            │ spawn/manage                                    │
│            ▼                                                 │
│  ┌─────────────────────┐                                    │
│  │  Python Backend     │                                    │
│  │  (PyInstaller)      │                                    │
│  │                     │                                    │
│  │  - FastAPI Server   │                                    │
│  │  - GOG API Client   │                                    │
│  │  - Download Manager │                                    │
│  └─────────────────────┘                                    │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Startup Sequence**:
   - User launches Electron app
   - Main process spawns Python backend subprocess
   - Main process polls health endpoint
   - Once healthy, main process creates window
   - Renderer loads and connects to backend

2. **Runtime Operation**:
   - User interacts with React UI in renderer
   - Renderer makes HTTP requests to Python backend
   - Renderer uses IPC for native operations (file dialogs)
   - Main process manages subprocess lifecycle

3. **Shutdown Sequence**:
   - User closes window
   - Main process receives close event
   - Main process sends SIGTERM to Python subprocess
   - Main process waits for graceful shutdown
   - Main process exits

## Components and Interfaces

### 1. Main Process (main.js)

**Responsibilities**:
- Application lifecycle management
- Window creation and management
- Python subprocess spawning and monitoring
- Health check coordination
- IPC handler registration
- Native dialog management
- Settings persistence

**Key Functions**:

```javascript
// Spawn Python backend subprocess
async function startBackend() {
  const port = await findAvailablePort();
  const backendPath = getBackendExecutablePath();
  
  backendProcess = spawn(backendPath, ['--port', port], {
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  
  // Capture logs
  backendProcess.stdout.on('data', (data) => log.info(data.toString()));
  backendProcess.stderr.on('data', (data) => log.error(data.toString()));
  
  // Handle exit
  backendProcess.on('exit', (code) => handleBackendExit(code));
  
  return port;
}

// Wait for backend to be ready
async function waitForBackend(port, maxAttempts = 10) {
  const url = `http://localhost:${port}/health`;
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch (error) {
      await sleep(Math.min(1000 * Math.pow(2, i), 10000));
    }
  }
  
  throw new Error('Backend failed to start');
}

// Create application window
function createWindow(backendPort) {
  mainWindow = new BrowserWindow({
    width: 1024,
    height: 768,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });
  
  // Store backend URL for renderer
  global.backendUrl = `http://localhost:${backendPort}`;
  
  mainWindow.loadFile('index.html');
}

// IPC Handlers
ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    defaultPath: settings.get('lastDirectory')
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const selectedPath = result.filePaths[0];
    settings.set('lastDirectory', selectedPath);
    return selectedPath;
  }
  
  return null;
});

ipcMain.handle('get-backend-url', () => {
  return global.backendUrl;
});
```

### 2. Preload Script (preload.js)

**Responsibilities**:
- Expose safe IPC APIs to renderer
- Bridge between main and renderer processes
- Enforce security boundaries

**Interface**:

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // File system operations
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  // Backend communication
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  
  // Settings
  getSetting: (key) => ipcRenderer.invoke('get-setting', key),
  setSetting: (key, value) => ipcRenderer.invoke('set-setting', key, value),
  
  // Application info
  getVersion: () => ipcRenderer.invoke('get-version'),
  getPlatform: () => process.platform
});
```

### 3. Renderer Process (React Application)

**Responsibilities**:
- User interface rendering
- API client for backend communication
- State management
- User interaction handling

**Key Components**:

```javascript
// API Client
class APIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }
  
  async login(username, password, twoFactorCode) {
    const response = await fetch(`${this.baseUrl}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, two_factor_code: twoFactorCode })
    });
    return response.json();
  }
  
  async getManifest(filters) {
    const params = new URLSearchParams(filters);
    const response = await fetch(`${this.baseUrl}/api/manifest?${params}`);
    return response.json();
  }
  
  async startDownload(gameIds, saveDir, options) {
    const response = await fetch(`${this.baseUrl}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_ids: gameIds, save_dir: saveDir, ...options })
    });
    return response.json();
  }
}

// App initialization
async function initializeApp() {
  // Get backend URL from main process
  const backendUrl = await window.electronAPI.getBackendUrl();
  
  // Initialize API client
  const apiClient = new APIClient(backendUrl);
  
  // Load saved settings
  const lastDirectory = await window.electronAPI.getSetting('lastDirectory');
  
  // Render app
  ReactDOM.render(
    <App apiClient={apiClient} initialDirectory={lastDirectory} />,
    document.getElementById('root')
  );
}

// Directory selection handler
async function handleSelectDirectory() {
  const directory = await window.electronAPI.selectDirectory();
  if (directory) {
    setDownloadDirectory(directory);
  }
}
```

### 4. Python Backend (PyInstaller Bundle)

**Responsibilities**:
- FastAPI server execution
- GOG API integration
- Download management
- Manifest management

**Modifications for Electron**:

```python
# main.py - Entry point for PyInstaller bundle
import sys
import argparse
import uvicorn
from gogrepoc.api.main import app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    
    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level='info',
        access_log=False  # Reduce noise in Electron logs
    )

if __name__ == '__main__':
    main()
```

**PyInstaller Spec File**:

```python
# gogrepoc.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gogrepoc', 'gogrepoc'),  # Include package
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gogrepoc-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 5. Build System

**Package.json Configuration**:

```json
{
  "name": "gogrepoc-desktop",
  "version": "2.0.0",
  "description": "GOG Game Repository Manager",
  "main": "electron/main.js",
  "scripts": {
    "start": "electron .",
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:electron\"",
    "dev:backend": "cd ../.. && uvicorn gogrepoc.api.main:app --reload --port 8000",
    "dev:electron": "electron . --dev",
    "build": "npm run build:backend && npm run build:electron",
    "build:backend": "pyinstaller gogrepoc.spec",
    "build:electron": "electron-builder",
    "build:win": "electron-builder --win",
    "build:mac": "electron-builder --mac",
    "build:linux": "electron-builder --linux"
  },
  "build": {
    "appId": "com.gogrepoc.desktop",
    "productName": "GOGRepoc",
    "directories": {
      "output": "dist",
      "buildResources": "build"
    },
    "files": [
      "electron/**/*",
      "build/**/*",
      "package.json"
    ],
    "extraResources": [
      {
        "from": "backend/dist/",
        "to": "backend",
        "filter": ["**/*"]
      }
    ],
    "win": {
      "target": ["nsis", "portable"],
      "icon": "build/icon.ico"
    },
    "mac": {
      "target": ["dmg", "zip"],
      "icon": "build/icon.icns",
      "category": "public.app-category.utilities"
    },
    "linux": {
      "target": ["AppImage", "deb", "rpm"],
      "icon": "build/icon.png",
      "category": "Utility"
    }
  },
  "dependencies": {
    "electron-store": "^8.1.0",
    "electron-log": "^5.0.0"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.0",
    "concurrently": "^8.2.0"
  }
}
```

## Data Models

### Settings Schema

```typescript
interface AppSettings {
  // Download settings
  lastDirectory: string | null;
  defaultDownloadPath: string | null;
  
  // Window state
  windowBounds: {
    width: number;
    height: number;
    x: number;
    y: number;
  };
  
  // Backend settings
  backendPort: number | null;
  
  // UI preferences
  theme: 'light' | 'dark' | 'system';
  
  // Update settings
  autoUpdate: boolean;
  checkUpdateOnStartup: boolean;
}
```

### Backend Process State

```typescript
interface BackendState {
  process: ChildProcess | null;
  port: number | null;
  status: 'starting' | 'running' | 'stopped' | 'error';
  lastError: string | null;
  startTime: Date | null;
  restartCount: number;
}
```

## Data Flow

### 1. Application Startup

```
User launches app
    ↓
Main process starts
    ↓
Load settings from electron-store
    ↓
Find available port (8000-9000 range)
    ↓
Spawn Python backend subprocess
    ↓
Poll /health endpoint (max 10 attempts, exponential backoff)
    ↓
Backend responds 200 OK
    ↓
Create BrowserWindow
    ↓
Load React app in renderer
    ↓
Renderer requests backend URL via IPC
    ↓
Renderer initializes API client
    ↓
App ready for user interaction
```

### 2. Directory Selection

```
User clicks "Select Directory" button
    ↓
Renderer calls window.electronAPI.selectDirectory()
    ↓
IPC message sent to main process
    ↓
Main process shows native dialog
    ↓
User selects directory
    ↓
Main process saves to settings
    ↓
Main process returns path via IPC
    ↓
Renderer updates UI with selected path
```

### 3. Download Operation

```
User selects games and clicks "Download"
    ↓
Renderer validates selection
    ↓
Renderer sends POST /api/download to backend
    ↓
Backend starts download task
    ↓
Backend returns task_id
    ↓
Renderer opens SSE connection to /api/download-progress/{task_id}
    ↓
Backend streams progress events
    ↓
Renderer updates progress UI
    ↓
Download completes
    ↓
Renderer closes SSE connection
    ↓
Renderer shows completion notification
```

### 4. Application Shutdown

```
User closes window
    ↓
Main process receives 'close' event
    ↓
Save window bounds to settings
    ↓
Send SIGTERM to Python subprocess
    ↓
Wait up to 5 seconds for graceful shutdown
    ↓
If still running, send SIGKILL
    ↓
Clean up resources
    ↓
Main process exits
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Backend Port Assignment

*For any* system state, when the main process needs to spawn the backend, it should successfully find and assign an available port in the valid range (8000-9000).

**Validates: Requirements 3.2**

### Property 2: IPC Round-Trip Communication

*For any* valid IPC message type (directory selection, backend URL request, settings access), sending a request from the renderer process should result in a response from the main process without errors.

**Validates: Requirements 2.3, 6.3**

### Property 3: Subprocess Cleanup on Exit

*For any* running backend subprocess, when the Electron app closes, the subprocess should be terminated before the main process exits.

**Validates: Requirements 3.4, 9.4**

### Property 4: Absolute Path Return from Dialog

*For any* directory selected through the native dialog, the path returned to the renderer process should be an absolute path (not relative).

**Validates: Requirements 5.3**

### Property 5: API Request Routing

*For any* API request made by the renderer process, the request should be sent to the backend URL with the dynamically assigned port.

**Validates: Requirements 7.1**

### Property 6: Window Bounds Persistence

*For any* window size and position, when the app is closed and reopened, the window should restore to the same bounds (within reasonable tolerance for screen size changes).

**Validates: Requirements 9.2, 15.5**

### Property 7: Error Logging

*For any* error that occurs in the main process, the error should be written to the log file in the user's application data directory.

**Validates: Requirements 10.1**

### Property 8: Subprocess Output Capture

*For any* output (stdout or stderr) from the backend subprocess, the output should be captured and logged by the main process.

**Validates: Requirements 10.2, 10.3**

### Property 9: Exponential Backoff Retry

*For any* health check retry sequence, the delay between attempts should follow an exponential backoff pattern (doubling each time) up to a maximum delay.

**Validates: Requirements 4.5**

### Property 10: Environment-Specific Path Resolution

*For any* environment (development or production), when the main process needs to locate the backend executable, it should resolve the correct path for that environment.

**Validates: Requirements 12.1**

### Property 11: Path Normalization

*For any* file path used in the application, the path should be normalized to use the correct separator for the current platform (backslash on Windows, forward slash on Unix).

**Validates: Requirements 12.4**

### Property 12: Settings Persistence

*For any* user setting (download directory, window bounds, preferences), when the setting is changed and the app is restarted, the setting should be restored to the saved value.

**Validates: Requirements 15.1**

## Error Handling

### Backend Startup Failures

**Scenario**: Backend fails to start or health checks timeout

**Handling**:
1. Display error dialog with diagnostic information:
   - Port number attempted
   - Error message from subprocess
   - Path to backend executable
   - Link to log file
2. Offer options:
   - Retry with different port
   - Open log file
   - Exit application
3. Log full error details for debugging

**Implementation**:
```javascript
async function handleBackendStartupError(error, port, backendPath) {
  log.error('Backend startup failed', { error, port, backendPath });
  
  const response = await dialog.showMessageBox(mainWindow, {
    type: 'error',
    title: 'Backend Startup Failed',
    message: 'The GOGRepoc backend failed to start.',
    detail: `Port: ${port}\nPath: ${backendPath}\nError: ${error.message}`,
    buttons: ['Retry', 'View Logs', 'Exit'],
    defaultId: 0,
    cancelId: 2
  });
  
  switch (response.response) {
    case 0: // Retry
      return startBackend();
    case 1: // View Logs
      shell.openPath(log.transports.file.getFile().path);
      return handleBackendStartupError(error, port, backendPath);
    case 2: // Exit
      app.quit();
  }
}
```

### Backend Crashes During Runtime

**Scenario**: Backend subprocess exits unexpectedly while app is running

**Handling**:
1. Detect subprocess exit via event listener
2. Log exit code and any error output
3. Display notification to user
4. Offer automatic restart with exponential backoff
5. After 3 failed restarts, require manual intervention

**Implementation**:
```javascript
let backendRestartCount = 0;
const MAX_AUTO_RESTARTS = 3;

backendProcess.on('exit', async (code, signal) => {
  if (code !== 0 && !isShuttingDown) {
    log.error('Backend crashed', { code, signal, restartCount: backendRestartCount });
    
    if (backendRestartCount < MAX_AUTO_RESTARTS) {
      backendRestartCount++;
      const delay = Math.min(1000 * Math.pow(2, backendRestartCount), 10000);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      
      try {
        await startBackend();
        backendRestartCount = 0; // Reset on successful restart
      } catch (error) {
        await handleBackendStartupError(error, backendPort, backendPath);
      }
    } else {
      const response = await dialog.showMessageBox(mainWindow, {
        type: 'error',
        title: 'Backend Repeatedly Crashing',
        message: 'The backend has crashed multiple times.',
        detail: 'Please check the logs for more information.',
        buttons: ['View Logs', 'Restart Backend', 'Exit'],
        defaultId: 1
      });
      
      if (response.response === 0) {
        shell.openPath(log.transports.file.getFile().path);
      } else if (response.response === 1) {
        backendRestartCount = 0;
        await startBackend();
      } else {
        app.quit();
      }
    }
  }
});
```

### IPC Communication Errors

**Scenario**: IPC calls fail or timeout

**Handling**:
1. Catch errors in IPC handlers
2. Return error objects instead of throwing
3. Renderer handles errors gracefully
4. Log errors for debugging

**Implementation**:
```javascript
// Main process
ipcMain.handle('select-directory', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
      defaultPath: settings.get('lastDirectory')
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
      const selectedPath = result.filePaths[0];
      settings.set('lastDirectory', selectedPath);
      return { success: true, path: selectedPath };
    }
    
    return { success: false, error: 'User cancelled' };
  } catch (error) {
    log.error('Directory selection failed', error);
    return { success: false, error: error.message };
  }
});

// Renderer process
async function selectDirectory() {
  try {
    const result = await window.electronAPI.selectDirectory();
    
    if (result.success) {
      setDownloadDirectory(result.path);
    } else if (result.error !== 'User cancelled') {
      showError(`Failed to select directory: ${result.error}`);
    }
  } catch (error) {
    showError(`Unexpected error: ${error.message}`);
  }
}
```

### Backend API Errors

**Scenario**: HTTP requests to backend fail

**Handling**:
1. Catch network errors in API client
2. Distinguish between network errors and API errors
3. Display appropriate error messages
4. Offer retry for transient failures

**Implementation**:
```javascript
class APIClient {
  async request(endpoint, options = {}) {
    const maxRetries = options.retries || 3;
    let lastError;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await fetch(`${this.baseUrl}${endpoint}`, options);
        
        if (!response.ok) {
          const error = await response.json();
          throw new APIError(error.detail || 'API request failed', response.status);
        }
        
        return await response.json();
      } catch (error) {
        lastError = error;
        
        if (error instanceof APIError && error.status < 500) {
          // Client error, don't retry
          throw error;
        }
        
        if (attempt < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
        }
      }
    }
    
    throw new NetworkError(`Failed after ${maxRetries} attempts: ${lastError.message}`);
  }
}
```

### Resource Not Found Errors

**Scenario**: Backend executable or other resources missing

**Handling**:
1. Check for resource existence before use
2. Provide clear error messages with expected paths
3. Offer guidance for resolution
4. Log full diagnostic information

**Implementation**:
```javascript
function getBackendExecutablePath() {
  const isDev = process.env.NODE_ENV === 'development';
  
  let backendPath;
  if (isDev) {
    // Development: expect backend running separately
    return null; // Will connect to localhost:8000
  } else {
    // Production: bundled executable
    const platform = process.platform;
    const exeName = platform === 'win32' ? 'gogrepoc-backend.exe' : 'gogrepoc-backend';
    backendPath = path.join(process.resourcesPath, 'backend', exeName);
  }
  
  if (!fs.existsSync(backendPath)) {
    const error = new Error(`Backend executable not found at: ${backendPath}`);
    log.error('Backend executable missing', { backendPath, platform: process.platform });
    
    dialog.showErrorBox(
      'Backend Not Found',
      `The backend executable could not be found.\n\nExpected location: ${backendPath}\n\nPlease reinstall the application.`
    );
    
    throw error;
  }
  
  return backendPath;
}
```

## Testing Strategy

### Dual Testing Approach

The application will use both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Specific startup sequences
- Error handling scenarios
- IPC message handling
- UI component behavior
- Edge cases (timeouts, cancellations, missing resources)

**Property Tests**: Verify universal properties across all inputs
- Port assignment for any system state
- IPC communication for any message type
- Path normalization for any file path
- Settings persistence for any setting value
- Subprocess cleanup for any running process

### Testing Tools

**JavaScript/Electron Testing**:
- **Jest**: Unit testing framework
- **Spectron** or **Playwright**: Electron app testing
- **fast-check**: Property-based testing library for JavaScript

**Python Backend Testing**:
- **pytest**: Unit testing framework
- **Hypothesis**: Property-based testing library for Python
- **httpx**: Async HTTP client for API testing

### Property-Based Test Configuration

Each property test will:
- Run minimum 100 iterations to ensure comprehensive input coverage
- Use appropriate generators for test data (ports, paths, settings, etc.)
- Tag tests with feature name and property number
- Reference the design document property

**Example Property Test**:

```javascript
// Feature: electron-desktop-app, Property 11: Path Normalization
const fc = require('fast-check');

describe('Path Normalization Property', () => {
  it('should normalize any file path to use platform-specific separators', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 1, maxLength: 5 }),
        (pathSegments) => {
          const mixedPath = pathSegments.join(Math.random() > 0.5 ? '/' : '\\');
          const normalized = normalizePath(mixedPath);
          
          const expectedSeparator = process.platform === 'win32' ? '\\' : '/';
          const wrongSeparator = process.platform === 'win32' ? '/' : '\\';
          
          // Property: normalized path should not contain wrong separator
          expect(normalized).not.toContain(wrongSeparator);
          
          // Property: normalized path should use correct separator
          if (pathSegments.length > 1) {
            expect(normalized).toContain(expectedSeparator);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

**Example Unit Test**:

```javascript
describe('Backend Startup', () => {
  it('should spawn backend subprocess on app start', async () => {
    const app = await startElectronApp();
    
    // Wait for backend to be ready
    await waitForBackendReady(app);
    
    // Verify subprocess is running
    const backendProcess = app.getBackendProcess();
    expect(backendProcess).toBeDefined();
    expect(backendProcess.pid).toBeGreaterThan(0);
    
    await app.close();
  });
  
  it('should display error dialog when backend fails to start', async () => {
    // Mock backend executable to fail
    mockBackendExecutable({ exitCode: 1 });
    
    const app = await startElectronApp();
    
    // Wait for error dialog
    const dialog = await app.waitForDialog();
    expect(dialog.title).toBe('Backend Startup Failed');
    expect(dialog.buttons).toContain('Retry');
    
    await app.close();
  });
  
  it('should handle health check timeout', async () => {
    // Mock backend to not respond to health checks
    mockBackendExecutable({ noHealthResponse: true });
    
    const app = await startElectronApp();
    
    // Wait for timeout (30 seconds)
    const dialog = await app.waitForDialog({ timeout: 35000 });
    expect(dialog.message).toContain('failed to start');
    
    await app.close();
  });
});
```

### Integration Testing

Integration tests will verify the complete flow:

1. **End-to-End Startup**: Launch app → backend starts → health check passes → window shows → UI loads
2. **Download Flow**: Select games → choose directory → start download → monitor progress → completion
3. **Error Recovery**: Backend crash → automatic restart → UI reconnection
4. **Settings Persistence**: Change settings → close app → reopen → verify settings restored

### Manual Testing Checklist

Some aspects require manual verification:

- [ ] Native dialogs appear correctly on each platform
- [ ] Window controls (minimize, maximize, close) work properly
- [ ] Application menu items function correctly
- [ ] UI is responsive and displays correctly
- [ ] Installers work on each platform
- [ ] Application icon displays correctly
- [ ] Auto-update flow works (if implemented)
- [ ] Application appears in system application list
- [ ] Uninstaller removes all files correctly

### Platform-Specific Testing

Each platform requires specific testing:

**Windows**:
- [ ] .exe installer works
- [ ] Portable .exe works
- [ ] Application installs to Program Files
- [ ] Start menu shortcut created
- [ ] Uninstaller works
- [ ] Backend executable runs without console window

**macOS**:
- [ ] DMG mounts and installs correctly
- [ ] .app bundle is signed (if applicable)
- [ ] Application appears in Applications folder
- [ ] Dock icon displays correctly
- [ ] Application menu works
- [ ] Gatekeeper allows execution

**Linux**:
- [ ] AppImage runs without installation
- [ ] .deb package installs correctly
- [ ] .rpm package installs correctly
- [ ] Desktop entry created
- [ ] Application appears in launcher
- [ ] File permissions correct

## Build and Deployment

### Build Pipeline

```bash
# 1. Build Python backend with PyInstaller
cd backend
pyinstaller gogrepoc.spec --clean

# 2. Build Electron app with electron-builder
cd ../electron
npm run build

# 3. Package for specific platforms
npm run build:win   # Windows
npm run build:mac   # macOS
npm run build:linux # Linux
```

### Directory Structure

```
gogrepoc-desktop/
├── electron/                 # Electron app source
│   ├── main.js              # Main process
│   ├── preload.js           # Preload script
│   ├── package.json         # Electron dependencies
│   └── build/               # Build resources (icons, etc.)
├── backend/                  # Python backend
│   ├── main.py              # Entry point for PyInstaller
│   ├── gogrepoc.spec        # PyInstaller spec file
│   └── dist/                # PyInstaller output
│       └── gogrepoc-backend # Executable
├── ui/                       # React frontend (existing)
│   ├── src/
│   ├── public/
│   └── build/               # Production build
└── dist/                     # Final packaged apps
    ├── win/
    ├── mac/
    └── linux/
```

### Release Process

1. **Version Bump**: Update version in package.json and pyproject.toml
2. **Build Backend**: Run PyInstaller for each platform
3. **Build Frontend**: Build React app for production
4. **Package Electron**: Run electron-builder for each platform
5. **Test Installers**: Install and test on each platform
6. **Create Release**: Tag version in git
7. **Upload Artifacts**: Upload installers to release page
8. **Update Documentation**: Update README with download links

### Continuous Integration

Recommended CI/CD setup:

```yaml
# .github/workflows/build.yml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-backend:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install -r requirements.txt pyinstaller
      - name: Build backend
        run: pyinstaller backend/gogrepoc.spec
      - name: Upload backend artifact
        uses: actions/upload-artifact@v3
        with:
          name: backend-${{ matrix.os }}
          path: backend/dist/

  build-electron:
    needs: build-backend
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Download backend artifact
        uses: actions/download-artifact@v3
        with:
          name: backend-${{ matrix.os }}
          path: electron/backend/
      - name: Install dependencies
        run: |
          cd ui && npm install && npm run build
          cd ../electron && npm install
      - name: Build Electron app
        run: cd electron && npm run build
      - name: Upload installer
        uses: actions/upload-artifact@v3
        with:
          name: installer-${{ matrix.os }}
          path: electron/dist/

  release:
    needs: build-electron
    runs-on: ubuntu-latest
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v3
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            installer-*/*
```

## Security Considerations

### Context Isolation

- **Enabled**: `contextIsolation: true` in BrowserWindow
- **Purpose**: Prevents renderer from accessing Node.js APIs directly
- **Implementation**: Use preload script with contextBridge

### Node Integration

- **Disabled**: `nodeIntegration: false` in BrowserWindow
- **Purpose**: Prevents arbitrary code execution in renderer
- **Alternative**: Use IPC for privileged operations

### Content Security Policy

```javascript
// Set CSP headers
session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
  callback({
    responseHeaders: {
      ...details.responseHeaders,
      'Content-Security-Policy': [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "connect-src 'self' http://localhost:*"
      ].join('; ')
    }
  });
});
```

### Backend Communication

- **Localhost Only**: Backend binds to 127.0.0.1, not 0.0.0.0
- **Random Port**: Reduces risk of port conflicts and unauthorized access
- **No Authentication**: Not needed since backend is local and not exposed

### Code Signing

- **Windows**: Sign executable with code signing certificate
- **macOS**: Sign with Apple Developer ID and notarize
- **Linux**: Not required but recommended for some distributions

### Update Security

- **Signature Verification**: Verify update signatures before installation
- **HTTPS Only**: Download updates over HTTPS
- **Rollback**: Support rollback if update fails
