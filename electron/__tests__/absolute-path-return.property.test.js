/**
 * Property-Based Test for Absolute Path Return from Dialog
 * 
 * Feature: electron-desktop-app
 * Property 4: Absolute Path Return from Dialog
 * 
 * **Validates: Requirements 5.3**
 * 
 * For any directory selected through the native dialog, the path returned
 * to the renderer process should be an absolute path (not relative).
 */

const fc = require('fast-check');
const path = require('path');

// Mock electron-store before requiring anything else
jest.mock('electron-store');

// Mock electron modules
jest.mock('electron', () => {
  const handlers = new Map();
  
  return {
    app: {
      whenReady: jest.fn(() => Promise.resolve()),
      on: jest.fn(),
      quit: jest.fn(),
      getAppPath: jest.fn(() => '/mock/app/path'),
      getPath: jest.fn(() => '/mock/user/data'),
      getVersion: jest.fn(() => '1.0.0'),
      isPackaged: false
    },
    BrowserWindow: jest.fn(function(options) {
      this.bounds = {
        x: options.x !== undefined ? options.x : 100,
        y: options.y !== undefined ? options.y : 100,
        width: options.width || 1024,
        height: options.height || 768
      };
      this.getBounds = jest.fn(() => this.bounds);
      this.setBounds = jest.fn((newBounds) => {
        this.bounds = { ...this.bounds, ...newBounds };
      });
      this.on = jest.fn();
      this.loadFile = jest.fn(() => Promise.resolve());
      this.webContents = {
        on: jest.fn()
      };
    }),
    ipcMain: {
      handle: jest.fn((channel, handler) => {
        handlers.set(channel, handler);
      }),
      removeHandler: jest.fn((channel) => {
        handlers.delete(channel);
      }),
      // Helper to simulate IPC invoke from renderer
      _simulateInvoke: async (channel, ...args) => {
        const handler = handlers.get(channel);
        if (!handler) {
          throw new Error(`No handler registered for channel: ${channel}`);
        }
        // Simulate event object (first parameter to handler)
        const mockEvent = {};
        return handler(mockEvent, ...args);
      },
      _getHandlers: () => handlers
    },
    dialog: {
      showOpenDialog: jest.fn()
    },
    screen: {
      getAllDisplays: jest.fn(() => [
        {
          bounds: { x: 0, y: 0, width: 1920, height: 1080 }
        }
      ])
    }
  };
});

jest.mock('electron-log', () => ({
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
}));

// Mock path-utils module
jest.mock('../path-utils', () => ({
  getBackendExecutablePath: jest.fn(() => null),
  normalizePath: jest.fn((p) => p)
}));

// Import after mocks are set up
const { ipcMain, dialog } = require('electron');
const Store = require('electron-store');

describe('Property 4: Absolute Path Return from Dialog', () => {
  let mockStore;
  let mainModule;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset ipcMain handlers
    const handlers = ipcMain._getHandlers();
    handlers.clear();
    
    // Create a fresh mock store for each test
    mockStore = new Map();
    
    // Mock electron-store implementation
    Store.mockImplementation(() => ({
      get: jest.fn((key) => mockStore.get(key)),
      set: jest.fn((key, value) => {
        mockStore.set(key, value);
        return value;
      }),
      has: jest.fn((key) => mockStore.has(key)),
      delete: jest.fn((key) => mockStore.delete(key)),
      clear: jest.fn(() => mockStore.clear())
    }));
    
    // Set up default store values
    mockStore.set('lastDirectory', '/default/path');
    
    // Load main module
    delete require.cache[require.resolve('../main.js')];
    mainModule = require('../main.js');
    
    // Create a mock main window
    const mockMainWindow = {
      getBounds: jest.fn(() => ({ width: 1024, height: 768, x: 100, y: 100 })),
      loadFile: jest.fn(),
      on: jest.fn(),
      webContents: {
        on: jest.fn()
      }
    };
    
    // Set the mock main window
    mainModule.setMainWindow(mockMainWindow);
    
    // Register IPC handlers
    mainModule.registerIpcHandlers();
  });

  afterEach(() => {
    // Clean up
    const mainModule = require('../main.js');
    mainModule.setMainWindow(null);
  });

  /**
   * Property: For any directory path returned by the native dialog,
   * the path should be absolute (not relative).
   * 
   * This ensures that the renderer process always receives absolute paths
   * that can be used reliably regardless of the current working directory.
   * 
   * Note: We test with platform-appropriate paths since path.isAbsolute()
   * is platform-specific (Unix paths on Unix, Windows paths on Windows).
   */
  it('should return absolute paths for any directory selected through dialog', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary absolute directory paths
        // Use platform-appropriate paths for the current OS
        fc.oneof(
          // Unix-style absolute paths (for Unix/macOS/Linux)
          fc.record({
            segments: fc.array(
              fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
              { minLength: 1, maxLength: 5 }
            )
          }).map(({ segments }) => '/' + segments.join('/')),
          
          // Common Unix directory paths
          fc.constantFrom(
            '/home/user/documents',
            '/home/user/downloads',
            '/var/data',
            '/opt/apps',
            '/Users/user/Desktop',
            '/Applications',
            '/tmp/test',
            '/usr/local/bin'
          )
        ),
        async (selectedPath) => {
          // Setup: Mock dialog to return the selected path
          dialog.showOpenDialog.mockResolvedValue({
            canceled: false,
            filePaths: [selectedPath]
          });
          
          // Act: Invoke select-directory handler
          const response = await ipcMain._simulateInvoke('select-directory');
          
          // Assert: Response should be successful
          expect(response.success).toBe(true);
          expect(response).toHaveProperty('path');
          
          // Property: The returned path should be absolute
          const returnedPath = response.path;
          expect(path.isAbsolute(returnedPath)).toBe(true);
          
          // Property: The returned path should match the selected path
          expect(returnedPath).toBe(selectedPath);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any absolute path returned by the dialog, the path
   * should remain absolute after being saved and retrieved from settings.
   * 
   * This ensures that path absoluteness is preserved through the
   * settings persistence layer.
   */
  it('should preserve absolute path property when saving to settings', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary absolute paths (platform-appropriate)
        fc.array(
          fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
          { minLength: 1, maxLength: 4 }
        ).map(segments => '/' + segments.join('/')),
        async (selectedPath) => {
          // Setup: Mock dialog to return the selected path
          dialog.showOpenDialog.mockResolvedValue({
            canceled: false,
            filePaths: [selectedPath]
          });
          
          // Act: Select directory (which saves to settings)
          const response = await ipcMain._simulateInvoke('select-directory');
          
          // Assert: Selection succeeded
          expect(response.success).toBe(true);
          
          // Property: Path should be absolute
          expect(path.isAbsolute(response.path)).toBe(true);
          
          // Act: Retrieve the saved path from settings
          const savedPath = mockStore.get('lastDirectory');
          
          // Property: Saved path should also be absolute
          expect(path.isAbsolute(savedPath)).toBe(true);
          
          // Property: Saved path should match the returned path
          expect(savedPath).toBe(response.path);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any sequence of directory selections, all returned
   * paths should be absolute.
   * 
   * This ensures consistency across multiple dialog invocations.
   */
  it('should return absolute paths for multiple consecutive selections', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create a sequence of directory paths (platform-appropriate)
        fc.array(
          fc.array(
            fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
            { minLength: 1, maxLength: 3 }
          ).map(segments => '/' + segments.join('/')),
          { minLength: 1, maxLength: 5 }
        ),
        async (pathSequence) => {
          const responses = [];
          
          // Act: Select each directory in sequence
          for (const selectedPath of pathSequence) {
            dialog.showOpenDialog.mockResolvedValue({
              canceled: false,
              filePaths: [selectedPath]
            });
            
            const response = await ipcMain._simulateInvoke('select-directory');
            responses.push(response);
          }
          
          // Assert: All selections should succeed
          expect(responses).toHaveLength(pathSequence.length);
          responses.forEach(response => {
            expect(response.success).toBe(true);
          });
          
          // Property: All returned paths should be absolute
          responses.forEach(response => {
            expect(path.isAbsolute(response.path)).toBe(true);
          });
          
          // Property: Each returned path should match the corresponding input
          responses.forEach((response, index) => {
            expect(response.path).toBe(pathSequence[index]);
          });
        }
      ),
      {
        numRuns: 50,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: The dialog should never return a relative path, even if
   * the defaultPath is relative (which shouldn't happen in practice).
   * 
   * This tests the robustness of the implementation.
   */
  it('should return absolute paths regardless of defaultPath format', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create various defaultPath formats and selected paths
        fc.record({
          defaultPath: fc.oneof(
            fc.constant(null),
            fc.constant(undefined),
            // Relative paths (shouldn't be used but testing robustness)
            fc.constantFrom('./relative', '../parent', 'relative/path'),
            // Absolute paths (normal case)
            fc.constantFrom('/absolute/path', '/home/user/test')
          ),
          selectedPath: fc.array(
            fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
            { minLength: 1, maxLength: 3 }
          ).map(segments => '/' + segments.join('/'))
        }),
        async ({ defaultPath, selectedPath }) => {
          // Setup: Set defaultPath in store
          if (defaultPath !== null && defaultPath !== undefined) {
            mockStore.set('lastDirectory', defaultPath);
          } else {
            mockStore.delete('lastDirectory');
          }
          
          // Setup: Mock dialog to return absolute path
          dialog.showOpenDialog.mockResolvedValue({
            canceled: false,
            filePaths: [selectedPath]
          });
          
          // Act: Select directory
          const response = await ipcMain._simulateInvoke('select-directory');
          
          // Assert: Selection succeeded
          expect(response.success).toBe(true);
          
          // Property: Returned path must be absolute
          expect(path.isAbsolute(response.path)).toBe(true);
          
          // Property: Returned path should match the selected path
          expect(response.path).toBe(selectedPath);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any platform-appropriate absolute path,
   * the returned path should be recognized as absolute by path.isAbsolute().
   * 
   * This verifies that the dialog returns paths in the correct format
   * for the current platform.
   */
  it('should return platform-appropriate absolute paths', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create platform-appropriate absolute paths
        fc.array(
          fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
          { minLength: 1, maxLength: 4 }
        ).map(segments => '/' + segments.join('/')),
        async (selectedPath) => {
          // Setup: Mock dialog to return the path
          dialog.showOpenDialog.mockResolvedValue({
            canceled: false,
            filePaths: [selectedPath]
          });
          
          // Act: Select directory
          const response = await ipcMain._simulateInvoke('select-directory');
          
          // Assert: Selection succeeded
          expect(response.success).toBe(true);
          
          // Property: Path should be absolute
          expect(path.isAbsolute(response.path)).toBe(true);
          
          // Property: Path should start with / on Unix systems
          expect(response.path).toMatch(/^\//);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: When dialog is cancelled, no path should be returned,
   * but this should not affect the absolute path property of future selections.
   */
  it('should maintain absolute path property after cancellation', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create a path to select after cancellation
        fc.array(
          fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
          { minLength: 1, maxLength: 3 }
        ).map(segments => '/' + segments.join('/')),
        async (selectedPath) => {
          // Act: First selection - cancelled
          dialog.showOpenDialog.mockResolvedValue({
            canceled: true,
            filePaths: []
          });
          
          const cancelResponse = await ipcMain._simulateInvoke('select-directory');
          
          // Assert: Cancellation handled correctly
          expect(cancelResponse.success).toBe(false);
          expect(cancelResponse.error).toBe('User cancelled');
          
          // Act: Second selection - successful
          dialog.showOpenDialog.mockResolvedValue({
            canceled: false,
            filePaths: [selectedPath]
          });
          
          const successResponse = await ipcMain._simulateInvoke('select-directory');
          
          // Assert: Selection succeeded
          expect(successResponse.success).toBe(true);
          
          // Property: Returned path should be absolute
          expect(path.isAbsolute(successResponse.path)).toBe(true);
          
          // Property: Returned path should match selected path
          expect(successResponse.path).toBe(selectedPath);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });
});
