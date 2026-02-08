# Task 6.4 Implementation: Window Close Handler

## Overview

Implemented a comprehensive window close handler that ensures proper cleanup of the backend subprocess before the application window closes. This implementation satisfies Requirement 9.4: "When the user closes the window, THE Electron_App SHALL terminate the Backend_Subprocess before exiting."

## Implementation Details

### Window Close Event Handler

The window close handler in `electron/main.js` implements the following sequence:

1. **Prevent Immediate Close**: Uses `event.preventDefault()` to stop the window from closing immediately
2. **Save Window State**: Calls `saveWindowBounds()` to persist the current window size and position
3. **Set Shutdown Flag**: Sets `isShuttingDown = true` to prevent duplicate shutdown attempts
4. **Stop Backend**: Calls `await stopBackend()` to gracefully terminate the backend subprocess
5. **Destroy Window**: After backend stops, calls `mainWindow.destroy()` to close the window

### Code Changes

**File: `electron/main.js`**

```javascript
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
```

### Backend Shutdown Process

The `stopBackend()` function (already implemented in Task 4.2) handles graceful subprocess termination:

1. Sends `SIGTERM` signal for graceful shutdown
2. Waits up to 5 seconds for the process to exit
3. If process doesn't exit, sends `SIGKILL` to force termination
4. Cleans up process references

### Integration with App Lifecycle

The implementation also updated the `before-quit` handler to avoid duplicate shutdown attempts:

```javascript
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
```

## Testing

### Unit Tests

Created comprehensive unit tests in `electron/__tests__/window-close-handler.test.js`:

1. **Save Window Bounds**: Verifies window bounds are saved when close event is triggered
2. **Trigger Backend Termination**: Verifies backend subprocess is terminated on close
3. **Wait for Subprocess Exit**: Verifies window doesn't close until subprocess exits
4. **Handle No Backend Process**: Verifies graceful handling when no backend is running
5. **Prevent Immediate Close**: Verifies correct event sequence (prevent → stop backend → destroy)
6. **Error Handling**: Verifies graceful error handling during backend shutdown

### Test Results

All tests pass successfully:

```
PASS  __tests__/window-close-handler.test.js
  Window Close Handler (Task 6.4)
    ✓ should save window bounds when close event is triggered
    ✓ should trigger backend subprocess termination on close
    ✓ should wait for subprocess to exit before allowing window close
    ✓ should handle close event when no backend process is running
    ✓ should prevent window close immediately and only allow after backend stops
    ✓ should handle errors during backend shutdown gracefully

Test Suites: 1 passed, 1 total
Tests:       6 passed, 6 total
```

### Integration with Existing Tests

All existing tests continue to pass, including:
- Port assignment tests
- Subprocess cleanup tests
- Subprocess output capture tests
- Window bounds persistence tests
- Window state persistence tests
- Path utils tests
- Missing resource errors tests

**Total Test Results**: 101 tests passed across 8 test suites

## Requirements Validation

### Requirement 9.4

✅ **WHEN the user closes the window, THE Electron_App SHALL terminate the Backend_Subprocess before exiting**

The implementation:
- Listens for the 'close' event on the window
- Prevents immediate window closure
- Calls `stopBackend()` to terminate the subprocess
- Waits for the subprocess to exit (up to 5 seconds)
- Only destroys the window after the backend has stopped

### Additional Requirements Satisfied

- **Requirement 3.4**: Backend subprocess is terminated gracefully when app closes
- **Requirement 15.5**: Window state is saved before closing

## Edge Cases Handled

1. **No Backend Process**: If no backend process is running, the close handler completes without errors
2. **Backend Already Stopping**: The `isShuttingDown` flag prevents duplicate shutdown attempts
3. **Backend Doesn't Respond**: The `stopBackend()` function has a 5-second timeout and will force kill if needed
4. **Errors During Shutdown**: Errors are logged but don't prevent the window from closing
5. **Multiple Close Attempts**: The `isShuttingDown` flag ensures only one shutdown sequence runs

## Logging

The implementation includes comprehensive logging:
- Window close request logged
- Backend shutdown progress logged
- Errors during shutdown logged
- Window destruction logged

## Future Enhancements

Potential improvements for future tasks:
1. Add user confirmation dialog for unsaved work (if applicable)
2. Add progress indicator during shutdown for long-running backend operations
3. Add configurable timeout for backend shutdown
4. Add metrics for shutdown duration

## Related Tasks

- **Task 4.2**: Implemented `stopBackend()` function used by this handler
- **Task 6.2**: Implemented `saveWindowBounds()` function used by this handler
- **Task 6.3**: Property test for window bounds persistence validates this functionality

## Conclusion

Task 6.4 is complete. The window close handler properly:
- Listens for the 'close' event ✅
- Saves window state before closing ✅
- Triggers backend subprocess termination ✅
- Waits for subprocess to exit before allowing window close ✅

All requirements are satisfied, all tests pass, and the implementation is production-ready.
