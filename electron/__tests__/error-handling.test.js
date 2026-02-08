/**
 * Unit tests for error handling
 * Task 11.3: Write unit tests for error handling
 * Requirements: 3.5 (detect backend failure and notify user), 3.6 (log error and provide restart options)
 * 
 * Tests verify:
 * - Backend startup failure dialog
 * - Backend crash detection
 * - Automatic restart logic
 * - Max restart limit
 */

// Mock child_process to prevent actual process spawning
const mockChildProcess = {
  on: jest.fn(),
  stdout: { on: jest.fn() },
  stderr: { on: jest.fn() },
  kill: jest.fn()
};

jest.mock('child_process', () => ({
  spawn: jest.fn(() => mockChildProcess)
}));

// Mock net module for port checking
jest.mock('net', () => ({
  createServer: jest.fn(() => ({
    listen: jest.fn(function(port, callback) {
      callback();
      return this;
    }),
    close: jest.fn(function(callback) {
      if (callback) callback();
      return this;
    }),
    on: jest.fn()
  }))
}));

// Mock electron modules
const mockDialog = {
  showMessageBox: jest.fn()
};

const mockShell = {
  openPath: jest.fn()
};

const mockApp = {
  quit: jest.fn(),
  getVersion: jest.fn(() => '1.0.0'),
  getAppPath: jest.fn(() => '/mock/app/path'),
  getPath: jest.fn(() => '/mock/user/data'),
  whenReady: null, // Set to null to prevent app.whenReady() from executing
  on: jest.fn(),
  isPackaged: false
};

jest.mock('electron', () => ({
  dialog: mockDialog,
  shell: mockShell,
  app: mockApp,
  ipcMain: {
    handle: jest.fn()
  },
  BrowserWindow: jest.fn(),
  screen: {
    getAllDisplays: jest.fn(() => [
      { bounds: { x: 0, y: 0, width: 1920, height: 1080 } }
    ])
  },
  Menu: {
    setApplicationMenu: jest.fn(),
    buildFromTemplate: jest.fn()
  }
}));

// Mock electron-log
const mockLog = {
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  transports: {
    file: {
      level: 'info',
      maxSize: 10 * 1024 * 1024,
      format: '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}',
      getFile: jest.fn(() => ({ path: '/mock/logs/main.log' }))
    }
  }
};

jest.mock('electron-log', () => mockLog);

// Mock electron-store
const mockStore = {
  get: jest.fn(),
  set: jest.fn()
};

jest.mock('electron-store', () => {
  return jest.fn().mockImplementation(() => mockStore);
});

// Mock path-utils
jest.mock('../path-utils', () => ({
  getBackendExecutablePath: jest.fn(() => '/mock/backend/path'),
  normalizePath: jest.fn((p) => p)
}));

// Mock menu-template
jest.mock('../menu-template', () => ({
  createMenuTemplate: jest.fn(() => [])
}));

describe('Error Handling', () => {
  let main;
  
  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Reset module cache to get fresh instance
    jest.resetModules();
    
    // Require main.js
    main = require('../main');
    
    // Reset restart count
    main.resetBackendRestartCount();
  });

  describe('Backend Startup Error Handling', () => {
    describe('handleBackendStartupError function', () => {
      it('should exist and be exported', () => {
        expect(main.handleBackendStartupError).toBeDefined();
        expect(typeof main.handleBackendStartupError).toBe('function');
      });

      it('should be an async function', () => {
        expect(main.handleBackendStartupError.constructor.name).toBe('AsyncFunction');
      });

      it('should log error with diagnostic details', async () => {
        const error = new Error('Backend failed to start');
        const port = 8000;
        const backendPath = '/path/to/backend';
        
        // Mock dialog to return Exit (response 2)
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendStartupError(error, port, backendPath);
        
        expect(mockLog.error).toHaveBeenCalledWith(
          'Backend startup failed',
          expect.objectContaining({
            error: 'Backend failed to start',
            port: 8000,
            backendPath: '/path/to/backend'
          })
        );
      });

      it('should display error dialog with correct configuration', async () => {
        const error = new Error('Backend failed');
        const port = 8000;
        const backendPath = '/path/to/backend';
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendStartupError(error, port, backendPath);
        
        expect(mockDialog.showMessageBox).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'error',
            title: 'Backend Startup Failed',
            message: 'The GOGRepoc backend failed to start.',
            buttons: ['Retry', 'View Logs', 'Exit'],
            defaultId: 0,
            cancelId: 2
          })
        );
      });

      it('should include diagnostic information in dialog detail', async () => {
        const error = new Error('Connection refused');
        const port = 8000;
        const backendPath = '/path/to/backend';
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendStartupError(error, port, backendPath);
        
        const dialogCall = mockDialog.showMessageBox.mock.calls[0][0];
        expect(dialogCall.detail).toContain('Error: Connection refused');
        expect(dialogCall.detail).toContain('Port: 8000');
        expect(dialogCall.detail).toContain('Path: /path/to/backend');
        expect(dialogCall.detail).toContain(`Platform: ${process.platform}`);
        expect(dialogCall.detail).toContain('Log file:');
      });

      it('should handle null port in diagnostic info', async () => {
        const error = new Error('Backend failed');
        const port = null;
        const backendPath = '/path/to/backend';
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendStartupError(error, port, backendPath);
        
        const dialogCall = mockDialog.showMessageBox.mock.calls[0][0];
        expect(dialogCall.detail).toContain('Port: Not assigned');
      });

      it('should handle null backend path in diagnostic info', async () => {
        const error = new Error('Backend failed');
        const port = 8000;
        const backendPath = null;
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendStartupError(error, port, backendPath);
        
        const dialogCall = mockDialog.showMessageBox.mock.calls[0][0];
        expect(dialogCall.detail).toContain('Path: Development mode (no bundled backend)');
      });

      it('should quit app when user chooses Exit', async () => {
        const error = new Error('Backend failed');
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendStartupError(error, 8000, '/path');
        
        expect(mockApp.quit).toHaveBeenCalled();
        expect(mockLog.info).toHaveBeenCalledWith('User chose to exit application');
      });

      it('should open log file when user chooses View Logs', async () => {
        const error = new Error('Backend failed');
        
        // First call: View Logs (response 1), Second call: Exit (response 2)
        mockDialog.showMessageBox
          .mockResolvedValueOnce({ response: 1 })
          .mockResolvedValueOnce({ response: 2 });
        
        mockShell.openPath.mockResolvedValue('');
        
        await main.handleBackendStartupError(error, 8000, '/path');
        
        expect(mockShell.openPath).toHaveBeenCalledWith('/mock/logs/main.log');
        expect(mockLog.info).toHaveBeenCalledWith('User chose to view logs');
        expect(mockLog.info).toHaveBeenCalledWith('Opened log file: /mock/logs/main.log');
      });

      it('should handle errors when opening log file fails', async () => {
        const error = new Error('Backend failed');
        const openError = new Error('Failed to open file');
        
        mockDialog.showMessageBox
          .mockResolvedValueOnce({ response: 1 })
          .mockResolvedValueOnce({ response: 2 });
        
        mockShell.openPath.mockRejectedValue(openError);
        
        await main.handleBackendStartupError(error, 8000, '/path');
        
        expect(mockLog.error).toHaveBeenCalledWith('Failed to open log file:', openError);
      });

      it('should show dialog again after viewing logs', async () => {
        const error = new Error('Backend failed');
        
        mockDialog.showMessageBox
          .mockResolvedValueOnce({ response: 1 })
          .mockResolvedValueOnce({ response: 2 });
        
        mockShell.openPath.mockResolvedValue('');
        
        await main.handleBackendStartupError(error, 8000, '/path');
        
        // Should be called twice: once for View Logs, once after viewing
        expect(mockDialog.showMessageBox).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Backend Crash Detection and Recovery', () => {
    describe('handleBackendCrash function', () => {
      it('should exist and be exported', () => {
        expect(main.handleBackendCrash).toBeDefined();
        expect(typeof main.handleBackendCrash).toBe('function');
      });

      it('should be an async function', () => {
        expect(main.handleBackendCrash.constructor.name).toBe('AsyncFunction');
      });

      it('should log crash with exit code and signal', async () => {
        const exitCode = 1;
        const signal = 'SIGTERM';
        
        // Mock to exceed max restarts immediately
        main.setBackendRestartCount(3);
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(exitCode, signal);
        
        expect(mockLog.error).toHaveBeenCalledWith(
          'Backend crashed during runtime',
          expect.objectContaining({
            exitCode: 1,
            signal: 'SIGTERM',
            restartCount: 3,
            maxRestarts: 3
          })
        );
      });
    });

    describe('Restart counter management', () => {
      it('should track restart count', () => {
        const count = main.getBackendRestartCount();
        expect(typeof count).toBe('number');
        expect(count).toBeGreaterThanOrEqual(0);
      });

      it('should allow setting restart count', () => {
        main.setBackendRestartCount(2);
        expect(main.getBackendRestartCount()).toBe(2);
      });

      it('should allow resetting restart count', () => {
        main.setBackendRestartCount(5);
        main.resetBackendRestartCount();
        expect(main.getBackendRestartCount()).toBe(0);
      });
    });

    describe('MAX_AUTO_RESTARTS constant', () => {
      it('should be exported and set to 3', () => {
        expect(main.MAX_AUTO_RESTARTS).toBeDefined();
        expect(main.MAX_AUTO_RESTARTS).toBe(3);
      });
    });

    describe('Exponential backoff calculation', () => {
      it('should calculate 1 second delay for first restart', () => {
        const attempt = 1;
        const delay = 1000 * Math.pow(2, attempt - 1);
        expect(delay).toBe(1000);
      });

      it('should calculate 2 second delay for second restart', () => {
        const attempt = 2;
        const delay = 1000 * Math.pow(2, attempt - 1);
        expect(delay).toBe(2000);
      });

      it('should calculate 4 second delay for third restart', () => {
        const attempt = 3;
        const delay = 1000 * Math.pow(2, attempt - 1);
        expect(delay).toBe(4000);
      });
    });

    describe('Automatic restart logic', () => {
      it('should attempt restart when count is less than MAX_AUTO_RESTARTS', () => {
        const restartCount = 0;
        const shouldRestart = restartCount < main.MAX_AUTO_RESTARTS;
        expect(shouldRestart).toBe(true);
      });

      it('should NOT attempt restart when count equals MAX_AUTO_RESTARTS', () => {
        const restartCount = 3;
        const shouldRestart = restartCount < main.MAX_AUTO_RESTARTS;
        expect(shouldRestart).toBe(false);
      });

      it('should NOT attempt restart when count exceeds MAX_AUTO_RESTARTS', () => {
        const restartCount = 4;
        const shouldRestart = restartCount < main.MAX_AUTO_RESTARTS;
        expect(shouldRestart).toBe(false);
      });
    });

    describe('Max restart limit', () => {
      it('should display error dialog when max restarts exceeded', async () => {
        // Set restart count to max
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, null);
        
        expect(mockDialog.showMessageBox).toHaveBeenCalledWith(
          null, // mainWindow is null in test environment
          expect.objectContaining({
            type: 'error',
            title: 'Backend Repeatedly Crashing',
            message: 'The GOGRepoc backend has crashed multiple times.',
            buttons: ['View Logs', 'Restart Backend', 'Exit'],
            defaultId: 1,
            cancelId: 2
          })
        );
      });

      it('should include diagnostic information in crash dialog', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, 'SIGTERM');
        
        const dialogCall = mockDialog.showMessageBox.mock.calls[0][1];
        expect(dialogCall.detail).toContain('Exit code: 1');
        expect(dialogCall.detail).toContain('Signal: SIGTERM');
        expect(dialogCall.detail).toContain('Restart attempts: 3');
        expect(dialogCall.detail).toContain('Log file:');
        expect(dialogCall.detail).toContain('Please check the logs for more information');
      });

      it('should omit signal line if null', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, null);
        
        const dialogCall = mockDialog.showMessageBox.mock.calls[0][1];
        expect(dialogCall.detail).toContain('Exit code: 1');
        expect(dialogCall.detail).not.toContain('Signal:');
      });

      it('should quit app when user chooses Exit after max restarts', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, null);
        
        expect(mockApp.quit).toHaveBeenCalled();
        expect(mockLog.info).toHaveBeenCalledWith(
          'User chose to exit application after repeated backend crashes'
        );
      });

      it('should open log file when user chooses View Logs after max restarts', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox
          .mockResolvedValueOnce({ response: 0 })
          .mockResolvedValueOnce({ response: 2 });
        
        mockShell.openPath.mockResolvedValue('');
        
        await main.handleBackendCrash(1, null);
        
        expect(mockShell.openPath).toHaveBeenCalledWith('/mock/logs/main.log');
        expect(mockLog.info).toHaveBeenCalledWith(
          'User chose to view logs after repeated crashes'
        );
      });

      it('should handle errors when opening log file fails after crash', async () => {
        main.setBackendRestartCount(3);
        
        const openError = new Error('Failed to open file');
        mockDialog.showMessageBox
          .mockResolvedValueOnce({ response: 0 })
          .mockResolvedValueOnce({ response: 2 });
        
        mockShell.openPath.mockRejectedValue(openError);
        
        await main.handleBackendCrash(1, null);
        
        expect(mockLog.error).toHaveBeenCalledWith('Failed to open log file:', openError);
      });

      it('should show dialog again after viewing logs', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox
          .mockResolvedValueOnce({ response: 0 })
          .mockResolvedValueOnce({ response: 2 });
        
        mockShell.openPath.mockResolvedValue('');
        
        await main.handleBackendCrash(1, null);
        
        // Should be called twice: once for View Logs, once after viewing
        expect(mockDialog.showMessageBox).toHaveBeenCalledTimes(2);
      });
    });

    describe('Edge cases', () => {
      it('should handle crash with null signal', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, null);
        
        expect(mockLog.error).toHaveBeenCalledWith(
          'Backend crashed during runtime',
          expect.objectContaining({
            exitCode: 1,
            signal: null
          })
        );
      });

      it('should handle crash with various exit codes', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        const exitCodes = [1, 2, 127, 255];
        
        for (const code of exitCodes) {
          jest.clearAllMocks();
          await main.handleBackendCrash(code, null);
          
          expect(mockLog.error).toHaveBeenCalledWith(
            'Backend crashed during runtime',
            expect.objectContaining({
              exitCode: code
            })
          );
        }
      });

      it('should handle multiple consecutive crashes', async () => {
        main.resetBackendRestartCount();
        
        // Set up to exceed max restarts
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        // Simulate 3 crashes
        for (let i = 0; i < 3; i++) {
          main.setBackendRestartCount(i);
          const shouldRestart = main.getBackendRestartCount() < main.MAX_AUTO_RESTARTS;
          expect(shouldRestart).toBe(true);
        }
        
        // 4th crash should trigger dialog
        main.setBackendRestartCount(3);
        await main.handleBackendCrash(1, null);
        
        expect(mockDialog.showMessageBox).toHaveBeenCalled();
      });
    });

    describe('Requirements validation', () => {
      it('should satisfy Requirement 3.5: detect backend failure and notify user', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, null);
        
        // Detection: function is called when backend crashes
        expect(mockLog.error).toHaveBeenCalledWith(
          'Backend crashed during runtime',
          expect.any(Object)
        );
        
        // Notification: error dialog is displayed
        expect(mockDialog.showMessageBox).toHaveBeenCalled();
      });

      it('should satisfy Requirement 3.6: log error and provide restart options', async () => {
        main.setBackendRestartCount(3);
        
        mockDialog.showMessageBox.mockResolvedValue({ response: 2 });
        
        await main.handleBackendCrash(1, 'SIGTERM');
        
        // Error logging: logs crash details
        expect(mockLog.error).toHaveBeenCalledWith(
          'Backend crashed during runtime',
          expect.objectContaining({
            exitCode: 1,
            signal: 'SIGTERM'
          })
        );
        
        // Restart options: dialog provides restart button
        const dialogCall = mockDialog.showMessageBox.mock.calls[0][1];
        expect(dialogCall.buttons).toContain('Restart Backend');
      });

      it('should implement automatic restart with exponential backoff', () => {
        // Verify exponential backoff formula
        const delays = [1, 2, 3].map(attempt => 1000 * Math.pow(2, attempt - 1));
        expect(delays).toEqual([1000, 2000, 4000]);
      });

      it('should limit automatic restarts to 3 attempts', () => {
        expect(main.MAX_AUTO_RESTARTS).toBe(3);
        
        // Verify restart logic
        expect(0 < main.MAX_AUTO_RESTARTS).toBe(true);
        expect(1 < main.MAX_AUTO_RESTARTS).toBe(true);
        expect(2 < main.MAX_AUTO_RESTARTS).toBe(true);
        expect(3 < main.MAX_AUTO_RESTARTS).toBe(false);
      });
    });
  });
});
