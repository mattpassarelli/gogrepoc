# Task 11.2 Implementation: Backend Crash Detection and Recovery

## Overview

Implemented comprehensive backend crash detection and recovery system with automatic restart capabilities, exponential backoff, and user-friendly error dialogs.

## Requirements Satisfied

- **Requirement 3.5**: Detect backend subprocess crashes and notify the user
- **Requirement 3.6**: Log errors and provide restart options when backend terminates unexpectedly

## Implementation Details

### 1. Crash Detection

The system listens for the subprocess 'exit' event in the `startBackend()` function:

```javascript
backendProcess.on('exit', (code, signal) => {
  log.info(`Backend process exited with code ${code}, signal ${signal}`);
  
  if (!isShuttingDown && code !== 0) {
    log.error('Backend crashed unexpectedly');
    handleBackendCrash(code, signal).catch(err => {
      log.error('Error in crash recovery handler:', err);
    });
  }
  
  backendProcess = null;
});
```

**Key Features:**
- Only triggers recovery for non-zero exit codes (crashes)
- Ignores exits during intentional shutdown (`isShuttingDown` flag)
- Passes exit code and signal to recovery handler
- Logs all exit events for diagnostics

### 2. Automatic Restart with Exponential Backoff

The `handleBackendCrash()` function implements automatic restart with exponential backoff:

**Backoff Schedule:**
- Attempt 1: 1 second delay (2^0 = 1s)
- Attempt 2: 2 second delay (2^1 = 2s)
- Attempt 3: 4 second delay (2^2 = 4s)

**Formula:** `delay = 1000 * Math.pow(2, attempt - 1)`

```javascript
if (backendRestartCount < MAX_AUTO_RESTARTS) {
  backendRestartCount++;
  
  // Calculate exponential backoff delay
  const delay = 1000 * Math.pow(2, backendRestartCount - 1);
  
  log.info(`Attempting automatic restart ${backendRestartCount}/${MAX_AUTO_RESTARTS} after ${delay}ms delay`);
  
  // Wait for delay
  await new Promise(resolve => setTimeout(resolve, delay));
  
  // Attempt restart
  const newPort = await startBackend();
  await waitForBackend(newPort);
  
  // Success! Reset counter
  backendRestartCount = 0;
  global.backendUrl = `http://localhost:${newPort}`;
}
```

### 3. Restart Limit

The system limits automatic restarts to **3 attempts** (`MAX_AUTO_RESTARTS = 3`):

- Attempts 1-3: Automatic restart with exponential backoff
- After 3 failed attempts: Display error dialog requiring manual intervention

### 4. Error Dialog After Max Restarts

When automatic restarts are exhausted, the system displays a comprehensive error dialog:

**Dialog Configuration:**
- **Type:** Error
- **Title:** "Backend Repeatedly Crashing"
- **Message:** "The GOGRepoc backend has crashed multiple times."
- **Buttons:** 
  - View Logs (response 0)
  - Restart Backend (response 1) - Default
  - Exit (response 2) - Cancel

**Diagnostic Information:**
```
The backend has crashed multiple times and automatic restart has failed.
Exit code: <code>
Signal: <signal> (if present)
Restart attempts: <count>
Log file: <path>

Please check the logs for more information.
```

### 5. User Actions

**View Logs (Response 0):**
- Opens the log file in the system's default application
- Shows the error dialog again after viewing logs
- Handles errors if log file cannot be opened

**Restart Backend (Response 1):**
- Resets restart counter to 0
- Kills any existing backend process
- Attempts to start backend with new port
- Updates global backend URL on success
- Notifies renderer of successful restart
- Falls back to startup error handler on failure

**Exit (Response 2):**
- Logs exit message
- Calls `app.quit()` to terminate application

### 6. Renderer Notifications

The system sends IPC events to the renderer process to keep the UI informed:

**backend-restarting event:**
```javascript
mainWindow.webContents.send('backend-restarting', {
  attempt: backendRestartCount,
  maxAttempts: MAX_AUTO_RESTARTS,
  delay
});
```

**backend-restarted event:**
```javascript
mainWindow.webContents.send('backend-restarted', {
  url: global.backendUrl
});
```

### 7. Successful Restart Handling

When automatic restart succeeds:
1. Reset restart counter to 0
2. Update `global.backendUrl` with new port
3. Send `backend-restarted` event to renderer
4. Log success message

This allows the application to recover from transient crashes without user intervention.

## State Management

### Global Variables

```javascript
let backendRestartCount = 0;
const MAX_AUTO_RESTARTS = 3;
```

### Exported Functions for Testing

```javascript
module.exports = {
  handleBackendCrash,
  MAX_AUTO_RESTARTS,
  getBackendRestartCount: () => backendRestartCount,
  setBackendRestartCount: (count) => { backendRestartCount = count; },
  resetBackendRestartCount: () => { backendRestartCount = 0; }
};
```

## Error Logging

All crash events are comprehensively logged:

```javascript
log.error('Backend crashed during runtime', { 
  exitCode, 
  signal, 
  restartCount: backendRestartCount,
  maxRestarts: MAX_AUTO_RESTARTS
});
```

Additional logging includes:
- Each restart attempt with delay
- Successful restarts
- Failed restart attempts
- Max restarts exceeded
- User actions (view logs, manual restart, exit)

## Testing

### Unit Tests

Created comprehensive unit test suite in `__tests__/backend-crash-recovery.test.js`:

**Test Coverage:**
- Function existence and signature
- Restart counter management
- Exponential backoff calculation
- Automatic restart logic
- Subprocess exit event handling
- Error dialog configuration
- Diagnostic information building
- User action handling
- Successful restart handling
- Renderer notifications
- Error logging
- Requirements validation
- Edge cases
- Integration with startBackend

**Test Results:** 74 tests, all passing ✓

### Test Categories

1. **Function Tests:** Verify function exists, has correct signature, is async
2. **Constant Tests:** Verify MAX_AUTO_RESTARTS = 3
3. **Counter Tests:** Verify restart counter tracking and management
4. **Backoff Tests:** Verify exponential backoff formula (1s, 2s, 4s)
5. **Logic Tests:** Verify restart decision logic
6. **Event Tests:** Verify exit event handling
7. **Dialog Tests:** Verify error dialog configuration
8. **Action Tests:** Verify user action handling
9. **Notification Tests:** Verify renderer IPC events
10. **Logging Tests:** Verify comprehensive error logging
11. **Requirements Tests:** Verify all requirements satisfied
12. **Edge Case Tests:** Verify handling of edge cases

## Integration with Existing Code

### Modified Files

1. **electron/main.js**
   - Added `backendRestartCount` and `MAX_AUTO_RESTARTS` global variables
   - Implemented `handleBackendCrash()` function
   - Updated subprocess exit event handler to call `handleBackendCrash()`
   - Exported new functions and constants for testing

### New Files

1. **electron/__tests__/backend-crash-recovery.test.js**
   - Comprehensive unit test suite (74 tests)
   - Tests all aspects of crash detection and recovery

2. **electron/TASK_11.2_IMPLEMENTATION.md**
   - This documentation file

## Usage Example

### Scenario 1: Single Crash with Successful Recovery

```
1. Backend crashes (exit code 1)
2. System detects crash (exit event)
3. Restart attempt 1 after 1 second delay
4. Backend starts successfully
5. Restart counter reset to 0
6. Renderer notified of new backend URL
7. Application continues normally
```

### Scenario 2: Multiple Crashes Leading to Manual Intervention

```
1. Backend crashes (exit code 1)
2. Restart attempt 1 after 1 second delay → fails
3. Backend crashes again
4. Restart attempt 2 after 2 second delay → fails
5. Backend crashes again
6. Restart attempt 3 after 4 second delay → fails
7. Backend crashes again
8. Max restarts exceeded (3 attempts)
9. Error dialog displayed to user
10. User chooses "Restart Backend"
11. Restart counter reset to 0
12. Backend starts successfully
13. Application continues normally
```

### Scenario 3: Graceful Shutdown (No Recovery)

```
1. User closes application
2. isShuttingDown flag set to true
3. Backend receives SIGTERM
4. Backend exits with code 0
5. Exit event fired
6. Recovery NOT triggered (code === 0 and isShuttingDown === true)
7. Application exits normally
```

## Benefits

1. **Automatic Recovery:** Transient crashes are handled automatically without user intervention
2. **Exponential Backoff:** Prevents rapid restart loops that could consume resources
3. **Restart Limit:** Prevents infinite restart loops for persistent failures
4. **User Control:** After max restarts, user can view logs, manually restart, or exit
5. **Comprehensive Logging:** All crash events and recovery attempts are logged for diagnostics
6. **Renderer Awareness:** UI can display appropriate messages during restart attempts
7. **Graceful Degradation:** System distinguishes between crashes and intentional shutdowns

## Future Enhancements

Potential improvements for future iterations:

1. **Configurable Restart Limit:** Allow users to configure max restart attempts
2. **Crash Analytics:** Track crash patterns and report to developers
3. **Automatic Bug Reports:** Offer to send crash logs to developers
4. **Backend Health Monitoring:** Proactively detect backend issues before crashes
5. **Restart Cooldown:** Implement cooldown period after successful restart
6. **Crash History:** Track crash history across sessions
7. **Smart Restart:** Adjust restart strategy based on crash patterns

## Conclusion

Task 11.2 has been successfully implemented with comprehensive crash detection and recovery capabilities. The system provides automatic recovery for transient failures while requiring manual intervention for persistent issues. All requirements are satisfied, and the implementation is fully tested with 74 passing unit tests.
