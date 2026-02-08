# GOGRepoc Desktop - Electron Application

This directory contains the Electron desktop application wrapper for GOGRepoc.

## Project Structure

```
electron/
├── main.js              # Main process (manages app lifecycle, windows, backend)
├── preload.js           # Preload script (exposes safe APIs to renderer)
├── renderer/            # Renderer process files
│   └── index.html       # Placeholder HTML (will be replaced with React app)
├── build/               # Build resources (icons, etc.)
├── package.json         # Electron dependencies and build configuration
└── README.md           # This file
```

## Development Setup

### Prerequisites

- Node.js 18 or higher
- Python 3.13 or higher (for backend)
- npm or yarn

### Installation

1. Install dependencies:
   ```bash
   cd electron
   npm install
   ```

2. Install Python backend dependencies (from project root):
   ```bash
   pip install -r requirements.txt
   ```

### Running in Development Mode

Development mode runs the Electron app with the Python backend running separately:

```bash
# Terminal 1: Start Python backend
cd ..
python -m uvicorn gogrepoc.api.main:app --reload --port 8000

# Terminal 2: Start Electron app
cd electron
npm run dev:electron
```

Or use the combined script:
```bash
npm run dev
```

This will:
- Start the Python backend on port 8000
- Start the Electron app in development mode
- Enable hot reload for both backend and frontend
- Open DevTools automatically

## Building for Production

For detailed build instructions, see [BUILD.md](BUILD.md).

### Quick Start

Build everything:
```bash
npm run build
```

This will:
1. Build the Python backend with PyInstaller (`npm run build:backend`)
2. Package the Electron app with electron-builder (`npm run build:electron`)

### Platform-Specific Builds

Build for specific platforms:
```bash
npm run build:win    # Windows (NSIS installer + portable)
npm run build:mac    # macOS (DMG + ZIP)
npm run build:linux  # Linux (AppImage, deb, rpm)
```

**Note**: The React frontend must be built separately before running the Electron build:
```bash
cd ../ui
npm install
npm run build
cd ../electron
npm run build
```

Output will be in `electron/dist/`.

## Configuration

### Package.json Scripts

- `start`: Run Electron app (production mode)
- `dev`: Run both backend and Electron in development mode
- `dev:backend`: Run Python backend only
- `dev:electron`: Run Electron app only (development mode)
- `build`: Build backend and Electron app
- `build:backend`: Build Python backend with PyInstaller
- `build:electron`: Build Electron app with electron-builder
- `build:win`: Build for Windows
- `build:mac`: Build for macOS
- `build:linux`: Build for Linux

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

Check logs in:
- Windows: `%APPDATA%/gogrepoc-desktop/logs/`
- macOS: `~/Library/Logs/gogrepoc-desktop/`
- Linux: `~/.config/gogrepoc-desktop/logs/`

### DevTools not opening

Ensure you're running in development mode:
```bash
NODE_ENV=development npm start
```

Or use:
```bash
npm run dev:electron
```

### Build fails

1. Ensure all dependencies are installed: `npm install`
2. Ensure Python backend is built: `npm run build:backend`
3. Check that icons exist in `build/` directory
4. Check electron-builder logs for specific errors

## Next Steps

This is the initial project structure (Task 1). Subsequent tasks will:

1. Implement Python backend bundling with PyInstaller (Task 2)
2. Implement backend subprocess management (Task 4)
3. Implement IPC handlers (Task 8)
4. Integrate React frontend (Task 14)
5. Complete build and packaging (Task 15-16)

## Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [Electron Builder Documentation](https://www.electron.build/)
- [Electron Security Best Practices](https://www.electronjs.org/docs/tutorial/security)
