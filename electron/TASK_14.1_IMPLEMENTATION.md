# Task 14.1 Implementation: API Client for Renderer Process

## Overview

Created a comprehensive API client for the Electron renderer process to communicate with the FastAPI backend. The client includes all backend endpoints with robust error handling and retry logic for transient failures.

## Requirements Addressed

- **Requirement 7.1**: Frontend-Backend Communication - API requests sent to backend on dynamically assigned port
- **Requirement 7.4**: Backend connection errors handled gracefully with user-friendly messages
- **Requirement 7.5**: Backend unavailability handled with appropriate error states

## Implementation Details

### Files Created

1. **`electron/renderer/api-client.js`** - Main API client implementation
2. **`electron/__tests__/api-client.test.js`** - Comprehensive unit tests

### API Client Features

#### Core Functionality

1. **Dynamic Base URL**: Accepts backend URL from IPC (supports port changes)
2. **Request Timeout**: Configurable timeout with abort controller (default: 30s)
3. **Retry Logic**: Exponential backoff for transient failures (default: 3 retries)
4. **Error Handling**: Distinguishes between client errors (4xx) and server errors (5xx)

#### Implemented Endpoints

1. **Health Check**: `healthCheck()` - Verify backend availability
2. **Authentication**:
   - `login(username, password, twoFactorCode)` - Login to GOG account
   - `checkAuth()` - Check authentication status
3. **Manifest Management**:
   - `getManifest(filters)` - Get game manifest with optional filters
   - `updateManifest(options)` - Update manifest from GOG
4. **Downloads**:
   - `startDownload(request)` - Start downloading selected games
   - `getDownloadProgress(taskId)` - Get progress via Server-Sent Events
   - `addWithoutDownload(request)` - Add games to manifest without downloading

#### Error Handling Strategy

1. **APIError**: For HTTP errors (4xx, 5xx)
   - Includes status code and error details
   - Client errors (4xx) are NOT retried
   - Server errors (5xx) are retried with exponential backoff

2. **NetworkError**: For network/connection failures
   - Includes original error for debugging
   - Automatically retried with exponential backoff

3. **Retry Logic**:
   - Initial delay: 1 second
   - Exponential backoff: 2x multiplier
   - Maximum retries: 3 (configurable)
   - Delays: 1s, 2s, 4s

4. **Timeout Handling**:
   - Uses AbortController to cancel long-running requests
   - Default timeout: 30 seconds (configurable)
   - Timeout errors are retried as network errors

### Test Coverage

Created 31 unit tests covering:

1. **Constructor**: URL handling, default options, custom options
2. **All Endpoints**: Request formatting, parameter handling
3. **Error Handling**:
   - 4xx client errors (no retry)
   - 5xx server errors (with retry)
   - Network errors (with retry)
   - Malformed responses
   - Timeout handling
4. **Retry Logic**: Exponential backoff verification
5. **URL Management**: Base URL updates

### Usage Example

```javascript
// Initialize client with backend URL from IPC
const backendUrl = await window.electronAPI.getBackendUrl();
const client = new APIClient(backendUrl);

// Login
try {
  const result = await client.login('user@example.com', 'password');
  console.log('Login successful:', result);
} catch (error) {
  if (error instanceof APIError) {
    console.error('API error:', error.message, error.status);
  } else if (error instanceof NetworkError) {
    console.error('Network error:', error.message);
  }
}

// Get manifest with filters
const manifest = await client.getManifest({
  osTypes: ['windows', 'linux'],
  languages: ['en'],
  updatesOnly: true,
  search: 'witcher'
});

// Start download
const downloadResult = await client.startDownload({
  gameIds: ['game1', 'game2'],
  saveDir: '/downloads',
  osTypes: ['windows'],
  languages: ['en'],
  threads: 8
});

// Monitor progress
const eventSource = client.getDownloadProgress(downloadResult.task_id);
eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log('Progress:', progress);
};
```

## Design Decisions

1. **Separate Error Classes**: APIError vs NetworkError allows callers to handle different error types appropriately
2. **Exponential Backoff**: Prevents overwhelming the backend during temporary issues
3. **No Retry for 4xx**: Client errors indicate invalid requests that won't succeed on retry
4. **Configurable Options**: Allows tuning for different environments (dev vs production)
5. **EventSource for Progress**: Uses Server-Sent Events for real-time download progress updates
6. **URL Update Method**: Supports backend restarts on different ports without recreating client

## Testing Results

All 31 tests pass successfully:
- ✓ Constructor and configuration
- ✓ All endpoint methods
- ✓ Error handling and retry logic
- ✓ Timeout handling
- ✓ URL management

## Next Steps

The API client is ready for integration with the React frontend (Task 14.3). The next tasks will:
1. Write property test for API request routing (Task 14.2)
2. Modify React app to use the API client (Task 14.3)
3. Replace manual path input with native dialog (Task 14.4)
4. Write integration tests (Task 14.5)
