# Development Mode Guide

This guide explains how to use the development mode scripts for the GOGRepoc Electron application.

## Overview

The development mode allows you to work on the Electron application with hot reload capabilities for both the frontend and backend, making development faster and more efficient.

**Task 16.1: Create development mode scripts**
- Requirements: 11.1 (enable DevTools and hot reload), 11.3 (connect to separately running backend), 11.5 (detailed console logging)

## Quick Start

### Running in Development Mode

To start the application in development mode with both backend and frontend:

```bash
cd electron
npm run dev
```

This command uses `concurrently` to run both the backend and Electron simultaneously.

### Running Backend Separately

If you want to run just the Python backend:

```bash
cd electron
npm run dev:backend
```

This starts the FastAPI backend on `http://localhost:8000` with hot reload enabled.

### Running Electron Separately

If you want to run just the Electron app (assuming backend is already running):

```bash
cd electron
npm run dev:electron
```

This starts Electron in development mode, connecting to the backend at `http://localhost:8000`.

## Development Mode Features

### 1. Hot Reload

- **Backend**: The Python backend uses `uvicorn --reload` to automatically restart when Python files change
- **Frontend**: Electron can be restarted manually (Ctrl+R or Cmd+R) to reload changes

### 2. DevTools

In development mode, the Chrome DevTools are automatically opened, allowing you to:
- Inspect the DOM
- Debug JavaScript
- Monitor network requests
- View console logs

### 3. Detailed Logging

Development mode enables verbose logging to help with debugging:
- All backend subprocess output is captured and logged
- IPC communication is logged
- Health check attempts are logged
- Window state changes are logged

### 4. No Backend Bundling

In development mode, the Electron app expects the backend to be running separately on port 8000. This means:
- No need to rebuild the PyInstaller bundle for backend changes
- Faster iteration cycle
- Easier debugging of backend issues

## Environment Detection

The application detects development mode through multiple indicators:

1. **NODE_ENV environment variable**: Set to `'development'`
2. **--dev command line flag**: Passed to Electron
3. **Packaged state**: If `app.isPackaged` is false

Any of these conditions will trigger development mode.

## Scripts Breakdown

### `npm run dev`

```json
"dev": "concurrently \"npm run dev:backend\" \"npm run dev:electron\""
```

Uses `concurrently` to run both backend and Electron processes simultaneously. This is the recommended way to start development.

### `npm run dev:backend`

```json
"dev:backend": "cd .. && python -m uvicorn gogrepoc.api.main:app --reload --port 8000"
```

Starts the Python backend with:
- `--reload`: Enables hot reload for Python files
- `--port 8000`: Fixed port for development (Electron expects this)
- Working directory: Project root (one level up from electron/)

### `npm run dev:electron`

```json
"dev:electron": "NODE_ENV=development electron . --dev"
```

Starts Electron with:
- `NODE_ENV=development`: Sets environment variable for development mode
- `--dev`: Additional flag for development mode detection
- Opens DevTools automatically
- Connects to backend at `http://localhost:8000`

## Backend Connection

### Development Mode

In development mode:
- Backend runs on fixed port `8000`
- Electron connects to `http://localhost:8000`
- No backend subprocess is spawned by Electron
- Backend must be started separately (via `npm run dev:backend` or manually)

### Production Mode

In production mode:
- Backend is bundled as a PyInstaller executable
- Electron spawns the backend subprocess
- Port is dynamically assigned (8000-9000 range)
- Backend URL is `http://localhost:{dynamic_port}`

## Troubleshooting

### Backend Not Starting

If the backend fails to start:

1. Check that Python dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Verify the backend can run standalone:
   ```bash
   cd /path/to/project
   python -m uvicorn gogrepoc.api.main:app --reload --port 8000
   ```

3. Check for port conflicts:
   ```bash
   lsof -i :8000  # On Unix-like systems
   netstat -ano | findstr :8000  # On Windows
   ```

### Electron Not Connecting to Backend

If Electron starts but can't connect to the backend:

1. Verify the backend is running on port 8000
2. Check the Electron console for connection errors
3. Verify the backend health endpoint responds:
   ```bash
   curl http://localhost:8000/health
   ```

### DevTools Not Opening

If DevTools don't open automatically:

1. Verify you're in development mode (check console logs)
2. Manually open DevTools: View menu → Toggle Developer Tools
3. Or use keyboard shortcut: Ctrl+Shift+I (Windows/Linux) or Cmd+Option+I (macOS)

### Hot Reload Not Working

For backend hot reload:
- Ensure `--reload` flag is present in the `dev:backend` script
- Check that uvicorn is watching the correct directories
- Some changes (like environment variables) require a full restart

For Electron:
- Electron doesn't have automatic hot reload
- Use Ctrl+R (Windows/Linux) or Cmd+R (macOS) to reload
- Or close and restart the Electron app

## Best Practices

### 1. Use `npm run dev` for Most Development

The combined script is the easiest way to start development:
```bash
npm run dev
```

This ensures both backend and frontend are running.

### 2. Run Backend Separately for Backend-Only Work

If you're only working on the backend:
```bash
npm run dev:backend
```

Then test with curl or a REST client instead of running Electron.

### 3. Check Logs for Issues

Development mode provides detailed logging. Check:
- Electron console (DevTools)
- Terminal output from `npm run dev`
- Log files in `~/Library/Logs/gogrepoc-desktop/` (macOS) or equivalent

### 4. Restart When Needed

Some changes require a full restart:
- Changes to main.js (Electron main process)
- Changes to preload.js
- Changes to package.json
- Environment variable changes

### 5. Test Production Build Periodically

Development mode behaves differently from production. Periodically test the production build:
```bash
npm run build
```

## Cross-Platform Considerations

### Unix-like Systems (Linux, macOS)

The `dev:electron` script uses Unix-style environment variable setting:
```bash
NODE_ENV=development electron . --dev
```

This works natively on Linux and macOS.

### Windows

The `--dev` flag ensures development mode works on Windows without needing to set environment variables differently:
```bash
electron . --dev
```

The `NODE_ENV=development` part may not work on Windows CMD, but the `--dev` flag ensures development mode is detected.

For better Windows compatibility, you could use `cross-env`:
```bash
npm install --save-dev cross-env
```

Then update the script:
```json
"dev:electron": "cross-env NODE_ENV=development electron . --dev"
```

## Testing Development Mode

Run the development mode tests:
```bash
npm test -- dev-mode-scripts.test.js
```

This verifies:
- Development mode detection works correctly
- Backend connection configuration is correct
- Scripts are properly configured
- Cross-platform compatibility

## Related Documentation

- [Main README](README.md) - General project documentation
- [Build Guide](build/WINDOWS_BUILD.md) - Production build instructions
- [Architecture Overview](../docs/architecture.md) - System architecture

## Requirements Validation

This development mode implementation validates:

- **Requirement 11.1**: DevTools are enabled and opened automatically in development mode
- **Requirement 11.3**: Electron connects to separately running backend (localhost:8000) in development mode
- **Requirement 11.5**: Detailed console logging is provided in development mode

All requirements are tested in `__tests__/dev-mode-scripts.test.js`.
