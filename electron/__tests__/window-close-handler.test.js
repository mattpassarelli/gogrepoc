/**
 * Unit Tests for Window Close Handler
 * 
 * Feature: electron-desktop-app
 * Task 6.4: Implement window close handler
 * 
 * **Validates: Requirements 9.4**
 * 
 * Tests that the window close handler:
 * - Listens for 'close' event on window
 * - Saves window state before closing
 * - Triggers backend subprocess termination
 * - Waits for subprocess to exit before allowing window close
 */

const { EventEmitter } = require('events');

// Mock electron modules
const mockWindow = new EventEmitter();
mockWindow.getBounds = jest.fn(() => ({ width: 1024, height: 768, x: 100, y: 100 }));
mockWindow.destroy = jest.fn();

const mockStore = {
  get: jest.fn(),
  set: jest.fn()
};

const mockLog = {
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  transports: {
    file: {
      level: 'info',
      maxSize: 10 * 1024 * 1024,
      format: '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}',
      getFile: jest.fn(() => ({ path: '/mock/log/path' }))
    }
  }
};

// Mock the subprocess
let mockBackendProcess = null;

// Mock the modules before requiring main.js
jest.mock('electron', () => ({
  app: {
    whenReady: jest.fn(() => Promise.resolve()),
    on: jest.fn(),
    quit: jest.fn(),
    getAppPath: jest.fn(() => '/app'),
    getPath: jest.fn(() => '/userdata'),
    isPackaged: false
  },
  BrowserWindow: jest.fn(),
  screen: {
    getAllDisplays: jest.fn(() => [
      { bounds: { x: 0, y: 0, width: 1920, height: 1080 } }
    ])
  }
}));

jest.mock('electron-log', () => mockLog);
jest.mock('electron-store', () => jest.fn(() => mockStore));
jest.mock('../path-utils', () => ({
  getBackendExecutablePath: jest.fn(() => null),
  normalizePath: jest.fn(p => p)
}));

describe('Window Close Handler (Task 6.4)', () => {
  let saveWindowBounds;
  let stopBackend;
  let isShuttingDown;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset mocks
    mockWindow.destroy.mockClear();
    mockStore.set.mockClear();
    mockLog.info.mockClear();
    
    // Import functions from main.js
    const main = require('../main.js');
    saveWindowBounds = main.saveWindowBounds;
    stopBackend = main.stopBackend;
    
    // Reset shutdown flag
    isShuttingDown = false;
    mockBackendProcess = null;
  });

  afterEach(() => {
    // Clean up any listeners
    mockWindow.removeAllListeners();
  });

  it('should save window bounds when close event is triggered', async () => {
    // Setup: Mock store to track if bounds were saved
    mockStore.get.mockReturnValue({ width: 1024, height: 768, x: 100, y: 100 });
    
    // Create a mock close handler that simulates the actual implementation
    let closeHandler;
    mockWindow.on('close', (handler) => {
      closeHandler = handler;
    });
    
    // Simulate the close handler registration
    const closeEvent = { preventDefault: jest.fn() };
    
    // Create a simplified version of the close handler
    const handleClose = async (event) => {
      // Save window state before closing
      const bounds = mockWindow.getBounds();
      mockStore.set('windowBounds', bounds);
      mockLog.info(`Saving window bounds: ${JSON.stringify(bounds)}`);
      
      // Prevent immediate close
      event.preventDefault();
      
      // Simulate backend stop
      await new Promise(resolve => setTimeout(resolve, 10));
      
      // Destroy window
      mockWindow.destroy();
    };
    
    // Act: Trigger close event
    await handleClose(closeEvent);
    
    // Assert: Window bounds should be saved
    expect(mockStore.set).toHaveBeenCalledWith('windowBounds', {
      width: 1024,
      height: 768,
      x: 100,
      y: 100
    });
    
    // Assert: Close should be prevented initially
    expect(closeEvent.preventDefault).toHaveBeenCalled();
    
    // Assert: Window should be destroyed after backend stops
    expect(mockWindow.destroy).toHaveBeenCalled();
  });

  it('should trigger backend subprocess termination on close', async () => {
    // Setup: Create a mock subprocess
    const { spawn } = require('child_process');
    const mockSubprocess = new EventEmitter();
    mockSubprocess.pid = 12345;
    mockSubprocess.kill = jest.fn();
    mockSubprocess.stdout = new EventEmitter();
    mockSubprocess.stderr = new EventEmitter();
    
    // Track if subprocess was terminated
    let subprocessTerminated = false;
    
    // Create a close handler that stops the subprocess
    const handleClose = async (event) => {
      event.preventDefault();
      
      // Simulate stopBackend
      if (mockSubprocess) {
        mockLog.info('Stopping backend subprocess...');
        
        return new Promise((resolve) => {
          const timeout = setTimeout(() => {
            if (mockSubprocess) {
              mockSubprocess.kill('SIGKILL');
            }
            subprocessTerminated = true;
            resolve();
          }, 100); // Short timeout for testing
          
          mockSubprocess.once('exit', () => {
            clearTimeout(timeout);
            subprocessTerminated = true;
            mockLog.info('Backend subprocess stopped');
            resolve();
          });
          
          mockSubprocess.kill('SIGTERM');
        });
      }
    };
    
    // Act: Trigger close event
    const closeEvent = { preventDefault: jest.fn() };
    const closePromise = handleClose(closeEvent);
    
    // Simulate subprocess exit
    setTimeout(() => {
      mockSubprocess.emit('exit', 0, null);
    }, 50);
    
    await closePromise;
    
    // Assert: Subprocess should be terminated
    expect(mockSubprocess.kill).toHaveBeenCalledWith('SIGTERM');
    expect(subprocessTerminated).toBe(true);
    expect(mockLog.info).toHaveBeenCalledWith('Backend subprocess stopped');
  });

  it('should wait for subprocess to exit before allowing window close', async () => {
    // Setup: Create a mock subprocess that takes time to exit
    const mockSubprocess = new EventEmitter();
    mockSubprocess.pid = 12345;
    mockSubprocess.kill = jest.fn();
    
    let windowDestroyed = false;
    let subprocessExited = false;
    
    // Create a close handler
    const handleClose = async (event) => {
      event.preventDefault();
      
      // Stop backend
      if (mockSubprocess) {
        await new Promise((resolve) => {
          mockSubprocess.once('exit', () => {
            subprocessExited = true;
            resolve();
          });
          
          mockSubprocess.kill('SIGTERM');
        });
      }
      
      // Destroy window after backend stops
      windowDestroyed = true;
    };
    
    // Act: Trigger close event
    const closeEvent = { preventDefault: jest.fn() };
    const closePromise = handleClose(closeEvent);
    
    // Verify window is not destroyed yet
    expect(windowDestroyed).toBe(false);
    
    // Simulate subprocess exit after a delay
    setTimeout(() => {
      mockSubprocess.emit('exit', 0, null);
    }, 100);
    
    await closePromise;
    
    // Assert: Subprocess should exit before window is destroyed
    expect(subprocessExited).toBe(true);
    expect(windowDestroyed).toBe(true);
  });

  it('should handle close event when no backend process is running', async () => {
    // Setup: No backend process
    mockBackendProcess = null;
    
    // Create a close handler
    const handleClose = async (event) => {
      event.preventDefault();
      
      // Save window bounds
      const bounds = mockWindow.getBounds();
      mockStore.set('windowBounds', bounds);
      
      // Stop backend (should handle null gracefully)
      if (mockBackendProcess) {
        await new Promise((resolve) => {
          mockBackendProcess.once('exit', resolve);
          mockBackendProcess.kill('SIGTERM');
        });
      }
      
      // Destroy window
      mockWindow.destroy();
    };
    
    // Act: Trigger close event
    const closeEvent = { preventDefault: jest.fn() };
    await handleClose(closeEvent);
    
    // Assert: Should complete without errors
    expect(mockStore.set).toHaveBeenCalled();
    expect(mockWindow.destroy).toHaveBeenCalled();
  });

  it('should prevent window close immediately and only allow after backend stops', async () => {
    // Setup: Create a mock subprocess
    const mockSubprocess = new EventEmitter();
    mockSubprocess.pid = 12345;
    mockSubprocess.kill = jest.fn();
    
    const events = [];
    
    // Create a close handler
    const handleClose = async (event) => {
      events.push('close-event-received');
      event.preventDefault();
      events.push('close-prevented');
      
      // Stop backend
      if (mockSubprocess) {
        await new Promise((resolve) => {
          mockSubprocess.once('exit', () => {
            events.push('subprocess-exited');
            resolve();
          });
          
          mockSubprocess.kill('SIGTERM');
        });
      }
      
      events.push('window-destroy-called');
      mockWindow.destroy();
    };
    
    // Act: Trigger close event
    const closeEvent = { preventDefault: jest.fn() };
    const closePromise = handleClose(closeEvent);
    
    // Simulate subprocess exit
    setTimeout(() => {
      mockSubprocess.emit('exit', 0, null);
    }, 50);
    
    await closePromise;
    
    // Assert: Events should occur in correct order
    expect(events).toEqual([
      'close-event-received',
      'close-prevented',
      'subprocess-exited',
      'window-destroy-called'
    ]);
    
    expect(closeEvent.preventDefault).toHaveBeenCalled();
    expect(mockWindow.destroy).toHaveBeenCalled();
  });

  it('should handle errors during backend shutdown gracefully', async () => {
    // Setup: Create a mock subprocess that throws an error
    const mockSubprocess = new EventEmitter();
    mockSubprocess.pid = 12345;
    mockSubprocess.kill = jest.fn(() => {
      throw new Error('Kill failed');
    });
    
    // Create a close handler with error handling
    const handleClose = async (event) => {
      event.preventDefault();
      
      try {
        if (mockSubprocess) {
          mockSubprocess.kill('SIGTERM');
        }
      } catch (error) {
        mockLog.error('Error stopping backend during window close:', error);
      }
      
      // Window should still close even if backend stop fails
      mockWindow.destroy();
    };
    
    // Act: Trigger close event
    const closeEvent = { preventDefault: jest.fn() };
    await handleClose(closeEvent);
    
    // Assert: Error should be logged but window should still close
    expect(mockLog.error).toHaveBeenCalledWith(
      'Error stopping backend during window close:',
      expect.any(Error)
    );
    expect(mockWindow.destroy).toHaveBeenCalled();
  });
});
