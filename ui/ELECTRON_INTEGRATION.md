# Electron Integration for React App

This document describes the changes made to integrate the React app with Electron.

## Overview

The React app has been modified to work seamlessly in both standalone web mode and Electron desktop mode. The key changes enable:

1. **Dynamic Backend URL Configuration**: The app detects whether it's running in Electron and gets the backend URL from the main process
2. **Backend Health Checking**: The app verifies the backend is available before attempting to use it
3. **Graceful Error Handling**: The app displays appropriate UI when the backend is unavailable

## Changes Made

### 1. Modified `ui/src/index.js`

The entry point now includes an async initialization function that:

- Detects if running in Electron by checking for `window.electronAPI`
- Gets the backend URL from the main process via `window.electronAPI.getBackendUrl()`
- Falls back to `REACT_APP_API_URL` environment variable or `http://localhost:8000` in web mode
- Performs a health check to verify backend availability
- Passes configuration props to the App component
- Displays an error state if initialization fails

**Key Functions:**
- `initializeApp()`: Main initialization function that sets up the app

**Props Passed to App:**
- `backendUrl`: The backend API URL
- `isElectron`: Boolean indicating if running in Electron
- `backendAvailable`: Boolean indicating if backend health check passed
- `backendError`: Error message if backend is unavailable

### 2. Modified `ui/src/App.js`

The App component now accepts configuration props and:

- Configures axios with the dynamic backend URL
- Displays a warning banner when backend is unavailable
- Disables login form and other UI when backend is down
- Shows different messages for Electron vs web mode
- Provides a "Retry Connection" button

**New Props:**
```javascript
{
  backendUrl: string,        // Backend API URL
  isElectron: boolean,       // Whether running in Electron
  backendAvailable: boolean, // Whether backend is available
  backendError: string       // Error message if unavailable
}
```

**Backend Unavailable UI:**
- Warning alert with appropriate message for Electron/web mode
- Error details displayed
- Retry button to reload the page
- Login form and other features disabled

### 3. Added Tests

Created comprehensive tests for the integration:

- `ui/src/App.backend.test.js`: Tests for App component backend configuration
- `ui/src/index.test.js`: Tests for initialization logic (comprehensive)
- `ui/src/App.integration.test.js`: Integration tests (comprehensive)

**Test Coverage:**
- Electron environment detection
- Backend URL retrieval from electronAPI
- Backend health checking
- Error handling for various failure scenarios
- Backend unavailable state UI
- Axios configuration with dynamic URL

## Usage

### In Electron Mode

The app automatically detects Electron and gets the backend URL:

```javascript
// Electron main process provides the backend URL
window.electronAPI.getBackendUrl() // Returns 'http://localhost:8123' (or dynamic port)
```

### In Web Mode

The app uses environment variables or defaults:

```bash
# Set backend URL via environment variable
REACT_APP_API_URL=http://localhost:8000 npm start

# Or it defaults to http://localhost:8000
```

## Requirements Validated

This implementation validates the following requirements:

- **7.2**: The Main Process SHALL provide the backend URL to the Renderer Process via IPC
- **7.3**: WHEN the backend port changes, THE Renderer Process SHALL update its API client configuration
- **7.5**: WHEN the Python_Backend is not available, THE Renderer_Process SHALL display a loading or error state

## Testing

Run the tests:

```bash
cd ui
npm test -- App.backend.test.js --watchAll=false
```

All tests should pass, verifying:
- ✓ Axios configuration with backend URL
- ✓ Backend unavailable warning display
- ✓ Different messages for Electron vs web mode
- ✓ Retry button presence
- ✓ Login form disabled when backend unavailable
- ✓ No warning when backend is available

## Future Enhancements

Potential improvements:
1. Add automatic retry with exponential backoff
2. Show backend startup progress in Electron mode
3. Add backend reconnection detection
4. Display backend version information
