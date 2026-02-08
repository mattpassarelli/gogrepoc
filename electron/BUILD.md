# Production Build Guide

This document describes the production build process for the GOGRepoc Desktop application.

## Overview

The production build process consists of three main steps:
1. **Backend Build**: Package the Python backend using PyInstaller
2. **Frontend Build**: Build the React frontend (done separately in ui/ directory)
3. **Electron Build**: Package the Electron app with electron-builder

## Prerequisites

### System Requirements
- **Node.js**: v18 or higher
- **Python**: 3.13 or higher
- **npm**: v9 or higher
- **PyInstaller**: Installed in Python environment

### Platform-Specific Requirements

#### Windows
- Visual Studio Build Tools (for native modules)
- NSIS (for installer creation, installed automatically by electron-builder)

#### macOS
- Xcode Command Line Tools
- Apple Developer ID (optional, for code signing)

#### Linux
- Standard build tools (gcc, make)
- fpm (for deb/rpm packages, installed automatically by electron-builder)

## Build Scripts

### Main Build Script

```bash
npm run build
```

This runs all build steps in sequence:
1. `npm run build:backend` - Builds the Python backend
2. `npm run build:electron` - Packages the Electron app

### Individual Build Scripts

#### Backend Build
```bash
npm run build:backend
```

- Runs PyInstaller with `gogrepoc.spec`
- Creates standalone executable in `backend/dist/`
- Includes all Python dependencies and data files
- Platform-specific output:
  - Windows: `gogrepoc-backend.exe`
  - macOS/Linux: `gogrepoc-backend`

#### Electron Build
```bash
npm run build:electron
```

- Runs electron-builder with default configuration
- Builds for current platform
- Includes backend executable from `backend/dist/`
- Output in `electron/dist/`

### Platform-Specific Builds

#### Windows Build
```bash
npm run build:win
```

Creates:
- NSIS installer: `GOGRepoc-{version}-x64.exe`
- Portable executable: `GOGRepoc-{version}-portable.exe`

#### macOS Build
```bash
npm run build:mac
```

Creates:
- DMG image: `GOGRepoc-{version}.dmg`
- ZIP archive: `GOGRepoc-{version}-mac.zip`
- Supports both x64 and arm64 architectures

#### Linux Build
```bash
npm run build:linux
```

Creates:
- AppImage: `GOGRepoc-{version}.AppImage`
- Debian package: `gogrepoc-desktop_{version}_amd64.deb`
- RPM package: `gogrepoc-desktop-{version}.x86_64.rpm`

## Build Process Details

### Step 1: Backend Build

The backend build uses PyInstaller to create a standalone executable:

```bash
cd backend
pyinstaller gogrepoc.spec
```

**What it does:**
- Analyzes Python dependencies
- Bundles FastAPI, uvicorn, and all GOGRepoc modules
- Includes hidden imports for uvicorn
- Creates single-file executable (or directory bundle)
- Sets `console=False` to prevent console window on Windows

**Output:**
- `backend/dist/gogrepoc-backend` (or `.exe` on Windows)
- `backend/build/` (temporary build files)

### Step 2: Frontend Build

The React frontend must be built separately before the Electron build:

```bash
cd ui
npm install
npm run build
```

**Output:**
- `ui/build/` - Production-optimized React app

**Note:** This step is not included in the Electron build scripts because the frontend is a separate project. Make sure to build it before running `npm run build:electron`.

### Step 3: Electron Build

The Electron build packages everything together:

```bash
cd electron
npm run build:electron
```

**What it does:**
- Copies backend executable from `backend/dist/` to `extraResources/backend/`
- Packages Electron app with main.js, preload.js, and renderer files
- Includes build resources (icons, etc.)
- Creates platform-specific installers/packages
- Signs executables (if certificates configured)

**Output:**
- `electron/dist/` - Platform-specific packages

## Build Configuration

The build configuration is defined in `electron/package.json` under the `build` key:

```json
{
  "build": {
    "appId": "com.gogrepoc.desktop",
    "productName": "GOGRepoc",
    "directories": {
      "output": "dist",
      "buildResources": "build"
    },
    "extraResources": [
      {
        "from": "../backend/dist/",
        "to": "backend",
        "filter": ["**/*"]
      }
    ],
    "win": { ... },
    "mac": { ... },
    "linux": { ... }
  }
}
```

### Key Configuration Options

- **appId**: Unique application identifier
- **productName**: Display name for the application
- **directories.output**: Where to place built packages
- **directories.buildResources**: Where to find icons and other build resources
- **extraResources**: Additional files to include (backend executable)
- **files**: Which files to include in the app package

## Complete Build Workflow

### For Development Testing

1. Build backend:
   ```bash
   cd backend
   pyinstaller gogrepoc.spec
   ```

2. Build frontend:
   ```bash
   cd ui
   npm run build
   ```

3. Build Electron app:
   ```bash
   cd electron
   npm run build:electron
   ```

4. Test the built application:
   - Windows: Run `electron/dist/GOGRepoc-{version}-x64.exe`
   - macOS: Open `electron/dist/GOGRepoc-{version}.dmg`
   - Linux: Run `electron/dist/GOGRepoc-{version}.AppImage`

### For Release

1. Update version in `electron/package.json`

2. Build all components:
   ```bash
   cd electron
   npm run build
   ```

3. Build for all platforms (requires platform-specific machines or CI/CD):
   ```bash
   npm run build:win    # On Windows or with Wine
   npm run build:mac    # On macOS
   npm run build:linux  # On Linux
   ```

4. Test installers on each platform

5. Create GitHub release and upload artifacts

## Troubleshooting

### Backend Build Issues

**Problem**: PyInstaller fails with missing modules
- **Solution**: Add missing modules to `hiddenimports` in `gogrepoc.spec`

**Problem**: Backend executable is too large
- **Solution**: Enable UPX compression in `gogrepoc.spec` (already enabled)

**Problem**: Backend fails to start in packaged app
- **Solution**: Check logs in `~/.config/GOGRepoc/logs/` (Linux) or equivalent

### Electron Build Issues

**Problem**: electron-builder fails with "Cannot find backend executable"
- **Solution**: Run `npm run build:backend` first

**Problem**: Build fails with "Icon not found"
- **Solution**: Ensure icon files exist in `electron/build/`:
  - `icon.ico` (Windows)
  - `icon.icns` (macOS)
  - `icon.png` (Linux)

**Problem**: App crashes on startup in production
- **Solution**: Check resource path resolution in `main.js`
- **Solution**: Verify backend executable has correct permissions

### Platform-Specific Issues

**Windows**:
- Antivirus may flag the executable - add exception or sign the executable
- NSIS installer requires admin privileges - configure `perMachine: false` for user-level install

**macOS**:
- Gatekeeper may block unsigned apps - sign with Apple Developer ID
- Notarization required for distribution outside App Store

**Linux**:
- AppImage may not run - ensure FUSE is installed
- deb/rpm packages may have dependency issues - test on target distributions

## Build Optimization

### Reducing Build Size

1. **Backend**:
   - Exclude unnecessary Python packages
   - Use `--exclude-module` in PyInstaller
   - Enable UPX compression

2. **Frontend**:
   - Use production build (`npm run build`)
   - Enable tree shaking
   - Minimize assets

3. **Electron**:
   - Use `asar` packaging (enabled by default)
   - Exclude dev dependencies
   - Compress resources

### Improving Build Speed

1. **Use caching**:
   - Cache PyInstaller build directory
   - Cache node_modules
   - Cache electron-builder downloads

2. **Parallel builds**:
   - Build backend and frontend in parallel
   - Use CI/CD matrix builds for multiple platforms

3. **Incremental builds**:
   - Only rebuild changed components
   - Use `--no-clean` flag for electron-builder during development

## CI/CD Integration

The build process can be automated using GitHub Actions or other CI/CD platforms. See `.github/workflows/electron-build.yml` for an example workflow.

### Example GitHub Actions Workflow

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Build backend
        run: |
          cd backend
          pip install -r requirements.txt pyinstaller
          pyinstaller gogrepoc.spec
      
      - name: Build frontend
        run: |
          cd ui
          npm install
          npm run build
      
      - name: Build Electron app
        run: |
          cd electron
          npm install
          npm run build:electron
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: electron/dist/
```

## Validation

After building, validate the package:

1. **Installation**: Install the package on a clean system
2. **Startup**: Verify the app starts without errors
3. **Backend**: Verify the backend starts and responds to health checks
4. **UI**: Verify the UI loads and displays correctly
5. **Functionality**: Test core features (login, manifest, download)
6. **Logs**: Check logs for errors or warnings
7. **Uninstall**: Verify the uninstaller works correctly

## References

- [electron-builder Documentation](https://www.electron.build/)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [Electron Documentation](https://www.electronjs.org/docs)
- [Requirements 11.2](../.kiro/specs/electron-desktop-app/requirements.md#requirement-11-development-and-production-modes)
