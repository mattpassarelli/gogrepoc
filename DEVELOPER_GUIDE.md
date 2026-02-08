# GOGRepoc Desktop - Developer Guide

This guide provides detailed information for developers working on the GOGRepoc Desktop application.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Component Details](#component-details)
- [IPC API Reference](#ipc-api-reference)
- [Build and Release Process](#build-and-release-process)
- [Testing Strategy](#testing-strategy)
- [Contributing Guidelines](#contributing-guidelines)
- [Troubleshooting Development Issues](#troubleshooting-development-issues)

## Architecture Overview

### High-Level Architecture

GOGRepoc Desktop uses a hybrid architecture combining Electron (frontend) with a Python FastAPI backend:

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

### Design Principles

1. **Security First**: Context isolation, no node integration in renderer
2. **Process Isolation**: Main and renderer processes communicate only via IPC
3. **Graceful Degradation**: App remains functional even if backend has issues
4. **Platform Agnostic**: Code works across Windows, macOS, and Linux
5. **Testability**: Comprehensive unit and property-based tests

### Technology Stack

**Frontend**:
- Electron 28+
- Node.js 18+
- React (renderer UI)
- electron-store (settings persistence)
- electron-log (logging)

**Backend**:
- Python 3.13+
- FastAPI (web framework)
- uvicorn (ASGI server)
- PyInstaller (bundling)

**Testing**:
- Jest (JavaScript testing)
- fast-check (property-based testing)
- pytest (Python testing)
- Hypothesis (Python property-based testing)

## Component Details

### Main Process (main.js)

The main process is the entry point and orchestrator of the application.

**Key Responsibilities**:
- Application lifecycle management (startup, shutdown)
- Window creation and management
- Backend subprocess spawning and monitoring
- Health check coordination
- IPC handler registration
- Native dialog management
- Settings persistence via electron-store
- Error handling and recovery

**Key Functions**:

#### `startBackend()`
Spawns the Python backend subprocess.

```javascript
async function startBackend() {
  const port = await findAvailablePort();
  const backendPath = getBackendExecutablePath();
  
  backendProcess = spawn(backendPath, ['--port', port], {
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  
  // Capture and log output
  backendProcess.stdout.on('data', (data) => log.info(data.toString()));
  backendProcess.stderr.on('data', (data) => log.error(data.toString()));
  
  // Handle exit
  backendProcess.on('exit', (code) => handleBackendExit(code));
  
  return port;
}
```

**Parameters**: None
**Returns**: `Promise<number>` - The port number the backend is running on
**Throws**: Error if backend executable not found or spawn fails

#### `waitForBackend(port, maxAttempts)`
Polls the backend health endpoint until it responds.

```javascript
async function waitForBackend(port, maxAttempts = 10) {
  const url = `http://localhost:${port}/health`;
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch (error) {
      const delay = Math.min(1000 * Math.pow(2, i), 10000);
      await sleep(delay);
    }
  }
  
  throw new Error('Backend failed to start');
}
```

**Parameters**:
- `port` (number): Backend port to check
- `maxAttempts` (number): Maximum retry attempts (default: 10)

**Returns**: `Promise<boolean>` - True if backend is healthy
**Throws**: Error if health check times out

#### `createWindow(backendPort)`
Creates the main application window.

```javascript
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
  
  global.backendUrl = `http://localhost:${backendPort}`;
  mainWindow.loadFile('renderer/index.html');
}
```

**Parameters**:
- `backendPort` (number): Port where backend is running

**Returns**: void

#### `findAvailablePort(startPort, endPort)`
Finds an available port in the specified range.

```javascript
async function findAvailablePort(startPort = 8000, endPort = 9000) {
  for (let port = startPort; port <= endPort; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error('No available ports in range');
}
```

**Parameters**:
- `startPort` (number): Start of port range (default: 8000)
- `endPort` (number): End of port range (default: 9000)

**Returns**: `Promise<number>` - Available port number
**Throws**: Error if no ports available

### Preload Script (preload.js)

The preload script bridges the main and renderer processes securely.

**Security Model**:
- Uses `contextBridge` to expose APIs
- No direct access to Node.js APIs from renderer
- Only whitelisted functions exposed
- All IPC calls validated

**Exposed APIs**:

```javascript
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

### Renderer Process

The renderer process displays the UI and handles user interactions.

**Key Components**:

#### API Client (api-client.js)
Handles all HTTP communication with the backend.

```javascript
class APIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }
  
  async request(endpoint, options = {}) {
    const maxRetries = options.retries || 3;
    let lastError;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await fetch(`${this.baseUrl}${endpoint}`, options);
        
        if (!response.ok) {
          const error = await response.json();
          throw new APIError(error.detail, response.status);
        }
        
        return await response.json();
      } catch (error) {
        lastError = error;
        
        // Don't retry client errors (4xx)
        if (error instanceof APIError && error.status < 500) {
          throw error;
        }
        
        // Exponential backoff for retries
        if (attempt < maxRetries - 1) {
          await sleep(1000 * Math.pow(2, attempt));
        }
      }
    }
    
    throw new NetworkError(`Failed after ${maxRetries} attempts: ${lastError.message}`);
  }
  
  // API methods
  async login(username, password, twoFactorCode) { /* ... */ }
  async getManifest(filters) { /* ... */ }
  async startDownload(gameIds, saveDir, options) { /* ... */ }
  // ... more methods
}
```

### Path Utilities (path-utils.js)

Handles path resolution for different environments and platforms.

**Key Functions**:

#### `getBackendExecutablePath()`
Returns the path to the backend executable.

```javascript
function getBackendExecutablePath() {
  const isDev = process.env.NODE_ENV === 'development';
  
  if (isDev) {
    return null; // Backend runs separately in dev mode
  }
  
  const platform = process.platform;
  const exeName = platform === 'win32' ? 'gogrepoc-backend.exe' : 'gogrepoc-backend';
  const backendPath = path.join(process.resourcesPath, 'backend', exeName);
  
  if (!fs.existsSync(backendPath)) {
    throw new Error(`Backend executable not found: ${backendPath}`);
  }
  
  return backendPath;
}
```

#### `normalizePath(filePath)`
Normalizes a path to use platform-specific separators.

```javascript
function normalizePath(filePath) {
  const separator = process.platform === 'win32' ? '\\' : '/';
  return filePath.split(/[/\\]/).join(separator);
}
```

### Settings Schema (settings-schema.js)

Defines the application settings structure and defaults.

```javascript
const defaultSettings = {
  // Download settings
  lastDirectory: null,
  defaultDownloadPath: null,
  
  // Window state
  windowBounds: {
    width: 1024,
    height: 768,
    x: undefined,
    y: undefined
  },
  
  // Backend settings
  backendPort: null,
  
  // UI preferences
  theme: 'system',
  
  // Update settings
  autoUpdate: true,
  checkUpdateOnStartup: true
};

function getSettings() {
  const store = new Store({ defaults: defaultSettings });
  return store.store;
}

function setSetting(key, value) {
  const store = new Store({ defaults: defaultSettings });
  store.set(key, value);
}
```

### Menu Template (menu-template.js)

Defines the application menu structure.

```javascript
function getMenuTemplate(mainWindow, isDev) {
  return [
    {
      label: 'File',
      submenu: [
        {
          label: 'Select Download Directory',
          click: () => mainWindow.webContents.send('select-directory')
        },
        { type: 'separator' },
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        ...(isDev ? [{ role: 'toggleDevTools' }] : [])
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation',
          click: () => shell.openExternal('https://github.com/your-repo/gogrepoc')
        },
        {
          label: 'View Logs',
          click: () => shell.openPath(log.transports.file.getFile().path)
        },
        { type: 'separator' },
        {
          label: 'About',
          click: () => showAboutDialog(mainWindow)
        }
      ]
    }
  ];
}
```

## IPC API Reference

### Main → Renderer

These events are sent from the main process to the renderer process.

#### `backend-status`
Notifies renderer of backend status changes.

**Payload**:
```javascript
{
  status: 'starting' | 'running' | 'stopped' | 'error',
  port: number | null,
  error: string | null
}
```

### Renderer → Main

These handlers are invoked by the renderer process.

#### `select-directory`
Opens a native directory selection dialog.

**Parameters**: None

**Returns**:
```javascript
{
  success: boolean,
  path: string | null,
  error: string | null
}
```

**Example**:
```javascript
const result = await window.electronAPI.selectDirectory();
if (result.success) {
  console.log('Selected:', result.path);
}
```

#### `get-backend-url`
Gets the backend URL.

**Parameters**: None

**Returns**: `string` - Backend URL (e.g., `http://localhost:8000`)

**Example**:
```javascript
const url = await window.electronAPI.getBackendUrl();
```

#### `get-setting`
Retrieves a setting value.

**Parameters**:
- `key` (string): Setting key

**Returns**: `any` - Setting value

**Example**:
```javascript
const lastDir = await window.electronAPI.getSetting('lastDirectory');
```

#### `set-setting`
Saves a setting value.

**Parameters**:
- `key` (string): Setting key
- `value` (any): Setting value

**Returns**: `void`

**Example**:
```javascript
await window.electronAPI.setSetting('lastDirectory', '/path/to/dir');
```

#### `get-version`
Gets the application version.

**Parameters**: None

**Returns**: `string` - Version string (e.g., `2.0.0`)

**Example**:
```javascript
const version = await window.electronAPI.getVersion();
```

## Build and Release Process

### Development Build

For local development and testing:

```bash
# 1. Start backend separately
cd <project-root>
python -m uvicorn gogrepoc.api.main:app --reload --port 8000

# 2. Start Electron in dev mode
cd electron
npm run dev:electron
```

### Production Build

Complete build process for distribution:

```bash
# 1. Build Python backend
cd backend
pyinstaller gogrepoc.spec --clean

# 2. Build React frontend (if applicable)
cd ../ui
npm install
npm run build

# 3. Build Electron app
cd ../electron
npm run build:electron
```

### Platform-Specific Builds

#### Windows Build

**Requirements**:
- Windows 10+ or Wine on Linux/macOS
- Visual Studio Build Tools

**Build**:
```bash
npm run build:win
```

**Output**:
- `dist/GOGRepoc-Setup-2.0.0.exe` - NSIS installer
- `dist/GOGRepoc-2.0.0-portable.exe` - Portable executable

#### macOS Build

**Requirements**:
- macOS 10.15+
- Xcode Command Line Tools
- Apple Developer ID (for code signing)

**Build**:
```bash
npm run build:mac
```

**Output**:
- `dist/GOGRepoc-2.0.0.dmg` - Disk image
- `dist/GOGRepoc-2.0.0-mac.zip` - ZIP archive

**Code Signing** (optional):
```bash
export CSC_LINK=/path/to/certificate.p12
export CSC_KEY_PASSWORD=your_password
npm run build:mac
```

#### Linux Build

**Requirements**:
- Modern Linux distribution
- build-essential package

**Build**:
```bash
npm run build:linux
```

**Output**:
- `dist/GOGRepoc-2.0.0.AppImage` - AppImage
- `dist/gogrepoc-desktop_2.0.0_amd64.deb` - Debian package
- `dist/gogrepoc-desktop-2.0.0.x86_64.rpm` - RPM package

### Release Checklist

Before releasing a new version:

- [ ] Update version in `package.json`
- [ ] Update version in `backend/main.py`
- [ ] Update CHANGELOG.md
- [ ] Run all tests: `npm test`
- [ ] Build for all platforms
- [ ] Test installers on each platform
- [ ] Verify backend starts correctly
- [ ] Verify UI loads and functions
- [ ] Test download functionality
- [ ] Check logs for errors
- [ ] Create Git tag: `git tag v2.0.0`
- [ ] Push tag: `git push origin v2.0.0`
- [ ] Create GitHub release
- [ ] Upload build artifacts
- [ ] Generate checksums
- [ ] Update documentation

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0): Breaking changes
- **Minor** (0.X.0): New features, backwards compatible
- **Patch** (0.0.X): Bug fixes, backwards compatible

### Continuous Integration

The project uses GitHub Actions for automated builds.

**Workflow** (`.github/workflows/electron-build.yml`):

```yaml
name: Build Electron App

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          cd electron && npm install
      
      - name: Build backend
        run: cd backend && pyinstaller gogrepoc.spec --clean
      
      - name: Build Electron app
        run: cd electron && npm run build:electron
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: electron/dist/*
```

## Testing Strategy

### Test Types

The project uses multiple testing approaches:

1. **Unit Tests**: Test individual functions and components
2. **Property-Based Tests**: Test universal properties across all inputs
3. **Integration Tests**: Test end-to-end flows

### Running Tests

```bash
# All tests
npm test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage

# Specific test file
npm test -- path-utils.test.js

# Property tests only
npm test -- --testNamePattern="property"
```

### Writing Unit Tests

**Example**:

```javascript
describe('Path Utilities', () => {
  describe('normalizePath', () => {
    it('should normalize Windows paths', () => {
      const input = 'C:/Users/test/file.txt';
      const expected = process.platform === 'win32' 
        ? 'C:\\Users\\test\\file.txt'
        : 'C:/Users/test/file.txt';
      
      expect(normalizePath(input)).toBe(expected);
    });
    
    it('should handle empty paths', () => {
      expect(normalizePath('')).toBe('');
    });
  });
});
```

### Writing Property-Based Tests

**Example**:

```javascript
const fc = require('fast-check');

describe('Path Normalization Property', () => {
  it('should normalize any file path to use platform-specific separators', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1, maxLength: 20 }), { 
          minLength: 1, 
          maxLength: 5 
        }),
        (pathSegments) => {
          // Create path with mixed separators
          const mixedPath = pathSegments.join(
            Math.random() > 0.5 ? '/' : '\\'
          );
          
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

### Test Coverage Goals

- **Unit Tests**: 80%+ code coverage
- **Property Tests**: All critical properties validated
- **Integration Tests**: All major user flows covered

### Mocking

**Electron APIs**:

```javascript
jest.mock('electron', () => ({
  app: {
    getPath: jest.fn(() => '/mock/path'),
    quit: jest.fn()
  },
  BrowserWindow: jest.fn(),
  ipcMain: {
    handle: jest.fn()
  }
}));
```

**File System**:

```javascript
jest.mock('fs', () => ({
  existsSync: jest.fn(() => true),
  readFileSync: jest.fn(() => '{}')
}));
```

## Contributing Guidelines

### Code Style

**JavaScript**:
- Use ES6+ features
- 2-space indentation
- Semicolons required
- Single quotes for strings
- Trailing commas in objects/arrays

**Python**:
- Follow PEP 8
- 4-space indentation
- Type hints for function signatures
- Docstrings for public functions

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

**Examples**:
```
feat(main): add automatic backend restart on crash

Implements exponential backoff retry logic with max 3 attempts.
Displays error dialog after max retries exceeded.

Closes #123
```

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feat/my-feature`
3. **Make changes** with clear commit messages
4. **Add tests** for new functionality
5. **Run tests**: `npm test`
6. **Update documentation** if needed
7. **Push to your fork**: `git push origin feat/my-feature`
8. **Create pull request** with description

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No console.log statements (use logger)
- [ ] Error handling implemented
- [ ] Security considerations addressed
- [ ] Performance impact considered

## Troubleshooting Development Issues

### Backend won't start in dev mode

**Check**:
1. Python backend is running: `curl http://localhost:8000/health`
2. Port 8000 is available: `lsof -i :8000`
3. Python dependencies installed: `pip list`
4. Backend logs for errors

### Electron app won't start

**Check**:
1. Node modules installed: `npm install`
2. Node version: `node --version` (need 18+)
3. Check console for errors
4. Try: `npm start -- --enable-logging`

### Tests failing

**Check**:
1. All dependencies installed
2. Test environment variables set
3. Mock data is correct
4. Run single test to isolate issue

### Build fails

**Check**:
1. Backend built: `ls backend/dist/`
2. Icons exist: `ls electron/build/`
3. Disk space available
4. electron-builder cache: `rm -rf ~/Library/Caches/electron-builder`

### Hot reload not working

**Check**:
1. Using `npm run dev` (not `npm start`)
2. Backend running with `--reload` flag
3. File watchers not exhausted (increase limit on Linux)

---

**Questions?** Open an issue on GitHub or check the [README](README.md) for more information.
