# GOGRepoc Desktop - Electron Application

This directory contains the Electron desktop application wrapper for GOGRepoc, providing a native desktop experience with seamless Python backend integration.

## Project Structure

```
electron/
├── main.js              # Main process (manages app lifecycle, windows, backend)
├── preload.js           # Preload script (exposes safe APIs to renderer)
├── menu-template.js     # Application menu configuration
├── path-utils.js        # Path resolution utilities
├── settings-schema.js   # Settings schema and defaults
├── renderer/            # Renderer process files
│   ├── index.html       # Main HTML entry point
│   └── api-client.js    # Backend API client
├── __tests__/           # Test files (unit and property-based tests)
├── build/               # Build resources (icons, etc.)
├── package.json         # Electron dependencies and build configuration
└── README.md           # This file
```

## Development Setup

### Prerequisites

- **Node.js**: Version 18 or higher
- **Python**: Version 3.13 or higher (for backend)
- **npm**: Comes with Node.js (or use yarn)
- **Git**: For version control
- **Platform-specific tools**:
  - **Windows**: Visual Studio Build Tools (for native modules)
  - **macOS**: Xcode Command Line Tools
  - **Linux**: build-essential package

### Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd gogrepoc
   ```

2. **Install Python dependencies** (from project root):
   ```bash
   # Create virtual environment (recommended)
   python -m venv .venv
   
   # Activate virtual environment
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Install Electron dependencies**:
   ```bash
   cd electron
   npm install
   ```

4. **Verify installation**:
   ```bash
   # Check Node.js version
   node --version  # Should be 18+
   
   # Check Python version
   python --version  # Should be 3.13+
   
   # Check npm packages
   npm list --depth=0
   ```

### Running in Development Mode

Development mode runs the Electron app with the Python backend running separately, enabling hot reload and DevTools.

**Option 1: Combined script (recommended)**
```bash
cd electron
npm run dev
```

This automatically:
- Starts the Python backend on port 8000
- Starts the Electron app in development mode
- Enables hot reload for both backend and frontend
- Opens DevTools automatically

**Option 2: Manual (two terminals)**
```bash
# Terminal 1: Start Python backend
cd <project-root>
python -m uvicorn gogrepoc.api.main:app --reload --port 8000

# Terminal 2: Start Electron app
cd electron
npm run dev:electron
```

**Development Mode Features**:
- DevTools enabled by default
- Backend connects to localhost:8000
- Hot reload for code changes
- Detailed console logging
- View menu includes "Reload" and "Toggle DevTools"

### Running Tests

The project includes both unit tests and property-based tests.

**Run all tests**:
```bash
npm test
```

**Run tests in watch mode**:
```bash
npm run test:watch
```

**Run specific test file**:
```bash
npm test -- path-utils.test.js
```

**Run with coverage**:
```bash
npm run test:coverage
```

**Test categories**:
- **Unit tests**: Test specific examples and edge cases
- **Property tests**: Test universal properties across all inputs (marked with `.property.test.js`)
- **Integration tests**: Test end-to-end flows

## Building for Production

For detailed build instructions, see [BUILD.md](BUILD.md).

### Prerequisites for Building

- All development dependencies installed
- Python backend dependencies installed
- Platform-specific build tools (see Development Setup)
- Application icons in `build/` directory

### Complete Build Process

**Step 1: Build Python Backend**
```bash
cd <project-root>/backend
npm run build:backend
# or manually:
pyinstaller gogrepoc.spec --clean
```

This creates a standalone executable in `backend/dist/`.

**Step 2: Build React Frontend** (if applicable)
```bash
cd <project-root>/ui
npm install
npm run build
```

This creates optimized production files in `ui/build/`.

**Step 3: Build Electron App**
```bash
cd <project-root>/electron
npm run build:electron
```

This packages the Electron app with electron-builder.

**All-in-one build**:
```bash
cd electron
npm run build
```

This runs all build steps in sequence.

### Platform-Specific Builds

Build for specific platforms:

**Windows**:
```bash
npm run build:win
```
Creates:
- NSIS installer (`.exe`)
- Portable executable (`.exe`)

**macOS**:
```bash
npm run build:mac
```
Creates:
- DMG disk image (`.dmg`)
- ZIP archive (`.zip`)
- Supports both Intel and Apple Silicon

**Linux**:
```bash
npm run build:linux
```
Creates:
- AppImage (`.AppImage`)
- Debian package (`.deb`)
- RPM package (`.rpm`)

**Cross-platform notes**:
- Windows builds require Windows or Wine
- macOS builds require macOS
- Linux builds can be done on any platform

### Build Output

Built applications are in `electron/dist/`:
```
dist/
├── win-unpacked/          # Windows unpacked files
├── mac/                   # macOS app bundle
├── linux-unpacked/        # Linux unpacked files
├── GOGRepoc-Setup-2.0.0.exe      # Windows installer
├── GOGRepoc-2.0.0-portable.exe   # Windows portable
├── GOGRepoc-2.0.0.dmg            # macOS disk image
├── GOGRepoc-2.0.0-mac.zip        # macOS ZIP
├── GOGRepoc-2.0.0.AppImage       # Linux AppImage
├── gogrepoc-desktop_2.0.0_amd64.deb  # Debian package
└── gogrepoc-desktop-2.0.0.x86_64.rpm # RPM package
```

### Build Configuration

The `build` section in `package.json` configures electron-builder:

```json
{
  "build": {
    "appId": "com.gogrepoc.desktop",
    "productName": "GOGRepoc",
    "extraResources": [
      {
        "from": "../backend/dist/",
        "to": "backend"
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
  }
}
```

### Customizing the Build

**Change app name**:
Edit `productName` in `package.json`

**Change app ID**:
Edit `appId` in `package.json` (reverse domain notation)

**Add file associations**:
Add to platform-specific config in `package.json`

**Code signing** (macOS/Windows):
Add signing configuration to `package.json`:
```json
{
  "mac": {
    "identity": "Developer ID Application: Your Name (TEAM_ID)"
  },
  "win": {
    "certificateFile": "path/to/cert.pfx",
    "certificatePassword": "password"
  }
}
```

## Configuration

### Package.json Scripts

- `start`: Run Electron app (production mode)
- `dev`: Run both backend and Electron in development mode (uses concurrently)
- `dev:backend`: Run Python backend only (port 8000)
- `dev:electron`: Run Electron app only (development mode)
- `test`: Run all tests with Jest
- `test:watch`: Run tests in watch mode
- `test:coverage`: Run tests with coverage report
- `build`: Build backend and Electron app (complete build)
- `build:backend`: Build Python backend with PyInstaller
- `build:electron`: Build Electron app with electron-builder
- `build:win`: Build for Windows (NSIS + portable)
- `build:mac`: Build for macOS (DMG + ZIP)
- `build:linux`: Build for Linux (AppImage + deb + rpm)

### Electron Builder Configuration

The `build` section in `package.json` configures electron-builder:

- **appId**: `com.gogrepoc.desktop`
- **productName**: `GOGRepoc`
- **Windows**: NSIS installer + portable executable
- **macOS**: DMG + ZIP (supports both Intel and Apple Silicon)
- **Linux**: AppImage, deb, and rpm packages

### Icons

Place application icons in the `build/` directory:

- `icon.ico` - Windows icon (256x256 recommended)
- `icon.icns` - macOS icon (512x512@2x recommended)
- `icon.png` - Linux icon (512x512 recommended)

## Architecture

### Main Process (main.js)

Responsibilities:
- Application lifecycle management
- Window creation and management
- Python backend subprocess spawning and monitoring
- IPC handler registration
- Native dialog management
- Settings persistence

### Preload Script (preload.js)

Responsibilities:
- Expose safe IPC APIs to renderer via contextBridge
- Bridge between main and renderer processes
- Enforce security boundaries (context isolation)

### Renderer Process

Responsibilities:
- User interface rendering (React app)
- API client for backend communication
- State management
- User interaction handling

## Security

The application follows Electron security best practices:

- **Context Isolation**: Enabled (`contextIsolation: true`)
- **Node Integration**: Disabled (`nodeIntegration: false`)
- **Preload Script**: Uses `contextBridge` to expose only necessary APIs
- **Content Security Policy**: Restricts resource loading
- **Localhost Backend**: Backend binds to 127.0.0.1 only
- **Random Port**: Backend uses dynamic port assignment

## Troubleshooting

### Backend fails to start

**Symptoms**: Error dialog on startup, "Backend failed to start"

**Solutions**:
1. **Check logs**:
   - Windows: `%APPDATA%/gogrepoc-desktop/logs/`
   - macOS: `~/Library/Logs/gogrepoc-desktop/`
   - Linux: `~/.config/gogrepoc-desktop/logs/`

2. **Verify backend executable exists**:
   - Development: Backend should run separately on port 8000
   - Production: Check `resources/backend/gogrepoc-backend` exists

3. **Check port availability**:
   - Backend tries ports 8000-9000
   - Close other applications using these ports
   - Check with: `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows)

4. **Verify Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Rebuild backend**:
   ```bash
   cd backend
   pyinstaller gogrepoc.spec --clean
   ```

### Health check timeout

**Symptoms**: "Backend failed to start" after 30 seconds

**Solutions**:
1. Backend may be starting slowly - check logs for errors
2. Firewall may be blocking localhost connections - add exception
3. Antivirus may be blocking the executable - add exception
4. Try increasing timeout in `main.js` (development only)

### Window doesn't appear

**Symptoms**: App starts but no window shows

**Solutions**:
1. Check if window is off-screen (multi-monitor setup):
   - Delete settings file to reset window position
   - Windows: `%APPDATA%/gogrepoc-desktop/config.json`
   - macOS: `~/Library/Application Support/gogrepoc-desktop/config.json`
   - Linux: `~/.config/gogrepoc-desktop/config.json`

2. Check console for errors:
   ```bash
   npm run dev:electron
   ```

### DevTools not opening

**Symptoms**: DevTools menu item doesn't work

**Solutions**:
1. Ensure you're in development mode:
   ```bash
   NODE_ENV=development npm start
   ```
   Or use:
   ```bash
   npm run dev:electron
   ```

2. DevTools is disabled in production builds (by design)

### Build fails

**Symptoms**: `npm run build` fails with errors

**Solutions**:

1. **"Backend executable not found"**:
   ```bash
   cd backend
   npm run build:backend
   ```

2. **"Icon not found"**:
   - Ensure icons exist in `build/` directory
   - Required: `icon.ico`, `icon.icns`, `icon.png`

3. **"Module not found"**:
   ```bash
   npm install
   ```

4. **PyInstaller fails**:
   - Check Python version: `python --version` (need 3.13+)
   - Reinstall PyInstaller: `pip install --upgrade pyinstaller`
   - Check for hidden imports in `gogrepoc.spec`

5. **electron-builder fails**:
   - Check Node.js version: `node --version` (need 18+)
   - Clear cache: `npm run build:electron -- --clean`
   - Check disk space (builds can be large)

### Native dialogs don't appear

**Symptoms**: Directory selection doesn't show dialog

**Solutions**:
1. Check IPC communication in DevTools console
2. Verify preload script is loaded:
   ```javascript
   console.log(window.electronAPI)  // Should be defined
   ```
3. Check main process logs for IPC errors

### Backend crashes repeatedly

**Symptoms**: "Backend repeatedly crashing" error dialog

**Solutions**:
1. Check logs for crash reason
2. Verify all Python dependencies installed
3. Check for port conflicts
4. Verify backend executable has correct permissions:
   ```bash
   chmod +x backend/dist/gogrepoc-backend  # macOS/Linux
   ```

### Settings not persisting

**Symptoms**: Settings reset on each launch

**Solutions**:
1. Check settings file permissions
2. Verify electron-store is installed: `npm list electron-store`
3. Check for errors in logs related to settings
4. Delete corrupted settings file (see "Window doesn't appear")

### App won't start after installation

**Symptoms**: Double-click does nothing or shows error

**Platform-specific solutions**:

**Windows**:
- Run as administrator
- Check Windows Defender / antivirus logs
- Verify .NET Framework installed
- Check Event Viewer for errors

**macOS**:
- Right-click → Open (first time only, bypasses Gatekeeper)
- Check System Preferences → Security & Privacy
- Verify app is not quarantined: `xattr -d com.apple.quarantine /Applications/GOGRepoc.app`

**Linux**:
- Make AppImage executable: `chmod +x GOGRepoc-2.0.0.AppImage`
- Install FUSE for AppImage: `sudo apt install fuse` (Ubuntu/Debian)
- Check for missing libraries: `ldd GOGRepoc-2.0.0.AppImage`

### Performance issues

**Symptoms**: App is slow or unresponsive

**Solutions**:
1. Check backend logs for errors
2. Monitor CPU/memory usage
3. Check for large log files (rotate logs)
4. Verify adequate disk space
5. Close other resource-intensive applications

### Getting Help

If you encounter issues not covered here:

1. **Check logs** (see locations above)
2. **Search existing issues** on GitHub
3. **Create a new issue** with:
   - Operating system and version
   - App version
   - Steps to reproduce
   - Log files (redact sensitive information)
   - Screenshots if applicable

## Next Steps

This Electron application is feature-complete and includes:

✅ Python backend bundling with PyInstaller (Task 2)
✅ Backend subprocess management with health checking (Task 4)
✅ Resource path resolution for dev and production (Task 5)
✅ Window management with state persistence (Task 6)
✅ Preload script and IPC handlers (Task 8)
✅ Native file system integration (Task 9)
✅ Application menu (Task 10)
✅ Error handling and recovery (Task 11)
✅ Settings persistence (Task 12)
✅ React frontend integration (Task 14)
✅ Cross-platform build configuration (Task 15)
✅ Build and development scripts (Task 16)
✅ Logging and diagnostics (Task 18)
✅ Comprehensive test suite (Task 22)

### For Users

See [USER_GUIDE.md](USER_GUIDE.md) for installation and usage instructions.

### For Developers

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for architecture details and contribution guidelines.

## Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [Electron Builder Documentation](https://www.electron.build/)
- [Electron Security Best Practices](https://www.electronjs.org/docs/tutorial/security)
