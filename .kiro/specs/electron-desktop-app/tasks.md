# Implementation Plan: Electron Desktop Application for GOGRepoc

## Overview

This implementation plan breaks down the Electron desktop application packaging into discrete, incremental tasks. The approach follows a bottom-up strategy: first setting up the project structure, then implementing core functionality (backend management, IPC), followed by UI integration, and finally packaging and distribution.

## Tasks

- [x] 1. Set up Electron project structure and dependencies
  - Create `electron/` directory in project root
  - Initialize npm project with `package.json`
  - Install Electron, electron-builder, electron-store, electron-log
  - Create basic directory structure (main.js, preload.js, renderer/)
  - Configure package.json scripts for development and production
  - Add build configuration for electron-builder (Windows, macOS, Linux targets)
  - _Requirements: 2.1, 2.4, 2.5, 8.1, 8.2, 8.3_

- [ ] 2. Implement Python backend bundling with PyInstaller
  - [x] 2.1 Create backend entry point script
    - Create `backend/main.py` with CLI argument parsing (--port, --host)
    - Add uvicorn server startup with configurable host and port
    - Ensure proper logging configuration for Electron integration
    - _Requirements: 1.2_
  
  - [x] 2.2 Create PyInstaller spec file
    - Create `backend/gogrepoc.spec` with Analysis configuration
    - Configure hidden imports for uvicorn and FastAPI
    - Include data files (gogrepoc package, templates, static assets)
    - Set console=False to prevent console window on Windows
    - Configure platform-specific executable names
    - _Requirements: 1.1, 1.3, 1.4, 1.5_
  
  - [x] 2.3 Write unit tests for backend entry point
    - Test CLI argument parsing
    - Test server startup with different port configurations
    - Test graceful shutdown handling
    - _Requirements: 1.2_
  
  - [x] 2.4 Create build script for PyInstaller
    - Create `backend/build.sh` (Unix) and `backend/build.bat` (Windows)
    - Add platform detection and appropriate PyInstaller invocation
    - Verify output executable exists and is executable
    - _Requirements: 1.3_

- [-] 3. Checkpoint - Verify backend builds and runs standalone
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Electron main process core functionality
  - [x] 4.1 Create main process entry point
    - Create `electron/main.js` with app lifecycle handlers
    - Implement environment detection (development vs production)
    - Set up electron-log for file logging
    - Initialize electron-store for settings persistence
    - _Requirements: 2.1, 10.1, 11.4, 15.2, 15.3_
  
  - [x] 4.2 Implement backend subprocess management
    - Create `startBackend()` function to spawn Python subprocess
    - Implement port finding logic (scan 8000-9000 range)
    - Capture stdout/stderr from subprocess and pipe to logs
    - Handle subprocess exit events and track exit codes
    - Implement graceful shutdown with SIGTERM/SIGKILL fallback
    - _Requirements: 3.1, 3.2, 3.4, 10.2, 10.3_
  
  - [x] 4.3 Write property test for port assignment
    - **Property 1: Backend Port Assignment**
    - **Validates: Requirements 3.2**
  
  - [x] 4.4 Write property test for subprocess cleanup
    - **Property 3: Subprocess Cleanup on Exit**
    - **Validates: Requirements 3.4, 9.4**
  
  - [x] 4.5 Write property test for subprocess output capture
    - **Property 8: Subprocess Output Capture**
    - **Validates: Requirements 10.2, 10.3**
  
  - [x] 4.6 Implement backend health checking
    - Create `waitForBackend()` function with exponential backoff
    - Poll /health endpoint with configurable max attempts (default 10)
    - Implement retry delays: 1s, 2s, 4s, 8s, 10s (capped)
    - Return success when health check passes, throw error on timeout
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [ ] 5. Implement resource path resolution
  - [x] 5.1 Create path resolution utilities
    - Implement `getBackendExecutablePath()` for dev and production modes
    - Implement `getResourcePath()` for general resource location
    - Handle platform-specific path separators
    - Verify resources exist and throw descriptive errors if missing
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [x] 5.2 Write property test for path normalization
    - **Property 11: Path Normalization**
    - **Validates: Requirements 12.4**
  
  - [x] 5.3 Write property test for environment-specific path resolution
    - **Property 10: Environment-Specific Path Resolution**
    - **Validates: Requirements 12.1**
  
  - [x] 5.4 Write unit tests for missing resource errors
    - Test error message when backend executable missing
    - Test error message when other resources missing
    - _Requirements: 12.5_

- [ ] 6. Implement window management
  - [x] 6.1 Create main application window
    - Implement `createWindow()` function
    - Set minimum size (1024x768), enable resizing
    - Configure webPreferences (nodeIntegration: false, contextIsolation: true)
    - Set window title to "GOGRepoc"
    - Load index.html from build directory
    - _Requirements: 9.1, 9.3, 9.5_
  
  - [x] 6.2 Implement window state persistence
    - Load saved window bounds from electron-store on startup
    - Save window bounds to electron-store on close
    - Handle edge cases (window off-screen, invalid bounds)
    - _Requirements: 9.2, 15.5_
  
  - [x] 6.3 Write property test for window bounds persistence
    - **Property 6: Window Bounds Persistence**
    - **Validates: Requirements 9.2, 15.5**
  
  - [x] 6.4 Implement window close handler
    - Listen for 'close' event on window
    - Save window state before closing
    - Trigger backend subprocess termination
    - Wait for subprocess to exit before allowing window close
    - _Requirements: 9.4_

- [ ] 7. Checkpoint - Verify main process can start backend and create window
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement preload script and IPC handlers
  - [x] 8.1 Create preload script with contextBridge
    - Create `electron/preload.js`
    - Use contextBridge to expose electronAPI to renderer
    - Expose: selectDirectory, getBackendUrl, getSetting, setSetting, getVersion, getPlatform
    - _Requirements: 6.2, 6.4_
  
  - [x] 8.2 Implement IPC handlers in main process
    - Register 'select-directory' handler with native dialog
    - Register 'get-backend-url' handler to return backend URL
    - Register 'get-setting' and 'set-setting' handlers for settings access
    - Register 'get-version' handler to return app version
    - Wrap all handlers in try-catch and return error objects on failure
    - _Requirements: 6.1, 6.3, 6.5_
  
  - [x] 8.3 Write property test for IPC round-trip communication
    - **Property 2: IPC Round-Trip Communication**
    - **Validates: Requirements 2.3, 6.3**
  
  - [x] 8.4 Write unit tests for IPC handlers
    - Test directory selection with valid selection
    - Test directory selection with cancellation
    - Test backend URL retrieval
    - Test settings get/set operations
    - _Requirements: 6.3_

- [ ] 9. Implement native file system integration
  - [x] 9.1 Implement directory selection dialog
    - Configure dialog.showOpenDialog with 'openDirectory' property
    - Set defaultPath from last selected directory in settings
    - Save selected directory to settings on successful selection
    - Handle cancellation gracefully (return null)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 9.2 Write property test for absolute path return
    - **Property 4: Absolute Path Return from Dialog**
    - **Validates: Requirements 5.3**
  
  - [x] 9.3 Write unit tests for dialog edge cases
    - Test cancellation handling
    - Test remembering last directory
    - _Requirements: 5.4, 5.5_

- [ ] 10. Implement application menu
  - [x] 10.1 Create menu template
    - Define File menu (Select Download Directory, Quit)
    - Define Edit menu (standard edit operations)
    - Define View menu (Reload, Toggle DevTools - dev mode only)
    - Define Help menu (Documentation, About)
    - _Requirements: 14.1, 14.4, 14.5_
  
  - [x] 10.2 Implement menu actions
    - Wire "Select Download Directory" to IPC directory selection
    - Wire "Quit" to graceful app shutdown
    - Wire "Reload" to window.reload()
    - Wire "Toggle DevTools" to window.toggleDevTools()
    - Create "About" dialog with app version and info
    - _Requirements: 14.2, 14.3_
  
  - [x] 10.3 Write unit tests for menu actions
    - Test each menu item triggers correct action
    - Test DevTools menu only appears in dev mode
    - _Requirements: 14.2, 14.3, 14.4_

- [ ] 11. Implement error handling and recovery
  - [x] 11.1 Implement backend startup error handling
    - Create `handleBackendStartupError()` function
    - Display error dialog with diagnostic info (port, path, error)
    - Offer options: Retry, View Logs, Exit
    - Implement retry logic with new port selection
    - _Requirements: 3.5, 10.4, 10.5_
  
  - [x] 11.2 Implement backend crash detection and recovery
    - Listen for subprocess 'exit' event
    - Implement automatic restart with exponential backoff
    - Limit automatic restarts to 3 attempts
    - Display error dialog after max restarts exceeded
    - _Requirements: 3.5, 3.6_
  
  - [x] 11.3 Write unit tests for error handling
    - Test backend startup failure dialog
    - Test backend crash detection
    - Test automatic restart logic
    - Test max restart limit
    - _Requirements: 3.5, 3.6_

- [ ] 12. Implement settings persistence
  - [x] 12.1 Create settings schema and defaults
    - Define settings interface (lastDirectory, windowBounds, theme, etc.)
    - Implement default values for all settings
    - Handle corrupted settings by falling back to defaults
    - _Requirements: 15.3, 15.4_
  
  - [x] 12.2 Implement settings load and save
    - Load settings on app startup using electron-store
    - Save settings on changes (directory selection, window resize, etc.)
    - Verify settings are stored in platform-appropriate location
    - _Requirements: 15.1, 15.2, 15.3_
  
  - [x] 12.3 Write property test for settings persistence
    - **Property 12: Settings Persistence**
    - **Validates: Requirements 15.1**
  
  - [x] 12.4 Write unit tests for settings edge cases
    - Test corrupted settings fallback to defaults
    - Test missing settings file
    - _Requirements: 15.4_

- [ ] 13. Checkpoint - Verify complete Electron app functionality
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Integrate React frontend with Electron
  - [x] 14.1 Create API client for renderer process
    - Create `electron/renderer/api-client.js`
    - Implement APIClient class with backend URL from IPC
    - Add methods for all backend endpoints (login, manifest, download, etc.)
    - Implement error handling with retry logic for transient failures
    - _Requirements: 7.1, 7.4, 7.5_
  
  - [x] 14.2 Write property test for API request routing
    - **Property 5: API Request Routing**
    - **Validates: Requirements 7.1**
  
  - [x] 14.3 Modify React app initialization
    - Update `ui/src/index.js` to detect Electron environment
    - Get backend URL from window.electronAPI.getBackendUrl()
    - Initialize API client with dynamic backend URL
    - Handle backend unavailable state with loading/error UI
    - _Requirements: 7.2, 7.3, 7.5_
  
  - [x] 14.4 Replace manual path input with native dialog
    - Update download directory selection UI component
    - Replace text input with button that calls window.electronAPI.selectDirectory()
    - Display selected path in read-only field
    - _Requirements: 5.1_
  
  - [x] 14.5 Write unit tests for React-Electron integration
    - Test API client initialization
    - Test backend URL retrieval
    - Test directory selection integration
    - _Requirements: 7.2, 7.3_

- [ ] 15. Configure build system for cross-platform packaging
  - [x] 15.1 Configure electron-builder for Windows
    - Set up NSIS installer configuration
    - Configure portable executable build
    - Add application icon (icon.ico)
    - Configure file associations if needed
    - _Requirements: 8.1, 8.4_
  
  - [x] 15.2 Configure electron-builder for macOS
    - Set up DMG configuration
    - Configure .app bundle
    - Add application icon (icon.icns)
    - Set application category
    - Configure code signing (if certificates available)
    - _Requirements: 8.2, 8.4_
  
  - [x] 15.3 Configure electron-builder for Linux
    - Set up AppImage configuration
    - Configure deb package
    - Configure rpm package
    - Add application icon (icon.png)
    - Set desktop entry category
    - _Requirements: 8.3, 8.4_
  
  - [x] 15.4 Configure extraResources for backend bundle
    - Add backend/dist/ to extraResources in electron-builder config
    - Ensure platform-specific backend executables are included
    - Verify resource paths resolve correctly in packaged app
    - _Requirements: 8.4, 12.2_

- [ ] 16. Create build and development scripts
  - [x] 16.1 Create development mode scripts
    - Add `npm run dev` script to run Electron in dev mode
    - Add `npm run dev:backend` to run Python backend separately
    - Use concurrently to run both processes
    - Configure Electron to connect to localhost:8000 in dev mode
    - _Requirements: 11.1, 11.3, 11.5_
  
  - [x] 16.2 Create production build scripts
    - Add `npm run build:backend` to run PyInstaller
    - Add `npm run build:frontend` to build React app
    - Add `npm run build:electron` to run electron-builder
    - Add `npm run build` to run all build steps in sequence
    - Add platform-specific scripts (build:win, build:mac, build:linux)
    - _Requirements: 11.2_
  
  - [x] 16.3 Create build verification script
    - Verify backend executable exists after PyInstaller build
    - Verify React build output exists
    - Verify electron-builder output exists
    - Check file sizes and warn if unexpectedly large
    - _Requirements: 1.1, 8.4_

- [ ] 18. Implement logging and diagnostics
  - [x] 18.1 Configure electron-log
    - Set log file location in user's app data directory
    - Configure log levels (info, warn, error)
    - Add timestamps to all log entries
    - Implement log rotation (max 5 files, 10MB each)
    - _Requirements: 10.1_
  
  - [x] 18.2 Add logging throughout application
    - Log app startup and shutdown
    - Log backend subprocess lifecycle events
    - Log IPC calls and responses
    - Log errors with full stack traces
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 18.3 Write property test for error logging
    - **Property 7: Error Logging**
    - **Validates: Requirements 10.1**
  
  - [x] 18.4 Add "View Logs" menu item
    - Add menu item to Help menu
    - Open log file directory in system file manager
    - _Requirements: 10.4_

- [ ] 19. Checkpoint - Verify complete build and packaging
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Write documentation
  - [x] 20.1 Create README for Electron app
    - Document development setup
    - Document build process
    - Document troubleshooting steps
    - _Requirements: 14.5_
  
  - [x] 20.2 Create user documentation
    - Document installation process for each platform
    - Document basic usage
    - Document common issues and solutions
    - _Requirements: 14.5_
  
  - [x] 20.3 Create developer documentation
    - Document architecture and design decisions
    - Document IPC API
    - Document build and release process
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 21. Create GitHub Actions build pipeline
  - [ ] 21.1 Create workflow file for automated builds
    - Create `.github/workflows/electron-build.yml`
    - Configure workflow to trigger on tags (e.g., v*.*.*)
    - Set up matrix build for Windows, macOS, and Linux
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ] 21.2 Configure Python backend build step
    - Install Python and dependencies in workflow
    - Run PyInstaller to build backend executable for each platform
    - Cache Python dependencies for faster builds
    - Verify backend executable was created successfully
    - _Requirements: 1.1, 1.3_
  
  - [ ] 21.3 Configure Electron build step
    - Install Node.js and npm dependencies
    - Build React frontend (if applicable)
    - Run electron-builder for target platform
    - Cache node_modules for faster builds
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ] 21.4 Configure artifact upload and release
    - Upload built executables as workflow artifacts
    - Create GitHub release with built packages
    - Attach installers (.exe, .dmg, .AppImage, .deb, .rpm) to release
    - Generate checksums for all release artifacts
    - _Requirements: 8.1, 8.2, 8.3, 8.5_
  
  - [ ] 21.5 Add build status badge and documentation
    - Add build status badge to README
    - Document release process and versioning
    - Document how to trigger builds (git tag workflow)
    - _Requirements: 14.5_

- [ ] 22. Final integration testing
  - [x] 22.1 Write integration tests for complete startup flow
    - Test: Launch app → backend starts → health check → window shows → UI loads
    - Test: Select directory → start download → monitor progress → completion
    - Test: Backend crash → automatic restart → UI reconnection
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 9.1_
  
  - [x] 22.2 Write integration tests for settings persistence
    - Test: Change settings → close app → reopen → verify settings restored
    - Test: Resize window → close → reopen → verify window bounds restored
    - _Requirements: 15.1, 15.2, 15.5_
  
  - [x] 22.3 Write integration tests for error recovery
    - Test: Backend fails to start → error dialog → retry → success
    - Test: Backend crashes → automatic restart → success
    - Test: Health check timeout → error dialog
    - _Requirements: 3.5, 3.6, 4.3_

- [ ] 23. Final checkpoint - Complete application ready for release
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test-related sub-tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and error conditions
- Integration tests validate end-to-end flows and component interactions
- The implementation follows a bottom-up approach: infrastructure first, then core functionality, then UI integration, finally packaging
- Development mode allows rapid iteration without rebuilding the backend
- Production mode creates fully self-contained distributable packages
