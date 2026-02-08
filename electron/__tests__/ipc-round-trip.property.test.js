/**
 * Property-Based Test for IPC Round-Trip Communication
 * 
 * Feature: electron-desktop-app
 * Property 2: IPC Round-Trip Communication
 * 
 * **Validates: Requirements 2.3, 6.3**
 * 
 * For any valid IPC message type (directory selection, backend URL request,
 * settings access), sending a request from the renderer process should result
 * in a response from the main process without errors.
 */

const fc = require('fast-check');

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
      showOpenDialog: jest.fn(() => Promise.resolve({
        canceled: false,
        filePaths: ['/mock/selected/path']
      }))
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
const { ipcMain } = require('electron');
const Store = require('electron-store');

describe('Property 2: IPC Round-Trip Communication', () => {
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
    mockStore.set('windowBounds', { width: 1024, height: 768, x: 100, y: 100 });
    
    // Set global backend URL
    global.backendUrl = 'http://localhost:8000';
    
    // Load main module (don't reset modules, just reload)
    delete require.cache[require.resolve('../main.js')];
    mainModule = require('../main.js');
    
    // Register IPC handlers
    mainModule.registerIpcHandlers();
  });

  afterEach(() => {
    // Clean up global state
    delete global.backendUrl;
  });

  /**
   * Property: For any valid IPC channel (select-directory, get-backend-url,
   * get-setting, set-setting, get-version), invoking the channel should
   * return a response without throwing an error.
   */
  it('should complete round-trip for any valid IPC channel without errors', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary IPC channel names from valid set
        fc.constantFrom(
          'select-directory',
          'get-backend-url',
          'get-setting',
          'set-setting',
          'get-version'
        ),
        async (channel) => {
          // Prepare arguments based on channel type
          let args = [];
          if (channel === 'get-setting') {
            args = ['testKey'];
          } else if (channel === 'set-setting') {
            args = ['testKey', 'testValue'];
          }
          
          // Act: Simulate IPC invoke from renderer
          let response;
          let error = null;
          
          try {
            response = await ipcMain._simulateInvoke(channel, ...args);
          } catch (err) {
            error = err;
          }
          
          // Assert: Should not throw an error
          expect(error).toBeNull();
          
          // Assert: Should return a response
          expect(response).toBeDefined();
          
          // Assert: Response should be an object (our handlers return objects)
          expect(typeof response).toBe('object');
          
          // Assert: Response should have a success field
          expect(response).toHaveProperty('success');
          expect(typeof response.success).toBe('boolean');
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any setting key-value pair, a set-setting followed by
   * get-setting should return the same value (round-trip consistency).
   */
  it('should maintain consistency for settings round-trip (set then get)', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary setting keys and values
        fc.record({
          key: fc.string({ minLength: 1, maxLength: 50 }),
          value: fc.oneof(
            fc.string(),
            fc.integer(),
            fc.boolean(),
            fc.constant(null),
            fc.array(fc.string()),
            fc.record({
              nested: fc.string(),
              number: fc.integer()
            })
          )
        }),
        async ({ key, value }) => {
          // Act: Set the setting
          const setResponse = await ipcMain._simulateInvoke('set-setting', key, value);
          
          // Assert: Set should succeed
          expect(setResponse.success).toBe(true);
          
          // Act: Get the setting
          const getResponse = await ipcMain._simulateInvoke('get-setting', key);
          
          // Assert: Get should succeed
          expect(getResponse.success).toBe(true);
          
          // Assert: Retrieved value should match the set value
          expect(getResponse.value).toEqual(value);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any sequence of IPC calls, each call should complete
   * independently without affecting other calls (no side effects).
   */
  it('should handle multiple concurrent IPC calls independently', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create a sequence of IPC operations
        fc.array(
          fc.record({
            channel: fc.constantFrom(
              'get-backend-url',
              'get-setting',
              'get-version'
            ),
            key: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: null })
          }),
          { minLength: 1, maxLength: 10 }
        ),
        async (operations) => {
          // Act: Execute all operations concurrently
          const promises = operations.map(op => {
            const args = op.channel === 'get-setting' && op.key ? [op.key] : [];
            return ipcMain._simulateInvoke(op.channel, ...args);
          });
          
          const responses = await Promise.all(promises);
          
          // Assert: All operations should complete successfully
          expect(responses).toHaveLength(operations.length);
          
          // Assert: Each response should be valid
          for (let i = 0; i < responses.length; i++) {
            const response = responses[i];
            const operation = operations[i];
            
            expect(response).toBeDefined();
            expect(typeof response).toBe('object');
            expect(response).toHaveProperty('success');
            
            // Verify response matches the operation type
            if (operation.channel === 'get-backend-url') {
              if (response.success) {
                expect(response).toHaveProperty('url');
              }
            } else if (operation.channel === 'get-version') {
              if (response.success) {
                expect(response).toHaveProperty('version');
              }
            } else if (operation.channel === 'get-setting') {
              // Only check for value if the request was successful
              if (response.success) {
                expect(response).toHaveProperty('value');
              }
            }
          }
        }
      ),
      {
        numRuns: 50, // Fewer runs for concurrent operations
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any invalid setting key (empty, non-string), the IPC
   * handler should return an error response without crashing.
   */
  it('should handle invalid setting keys gracefully', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create invalid setting keys
        fc.oneof(
          fc.constant(''),           // Empty string
          fc.constant(null),         // Null
          fc.constant(undefined),    // Undefined
          fc.constant(123),          // Number
          fc.constant(true),         // Boolean
          fc.constant({}),           // Object
          fc.constant([])            // Array
        ),
        async (invalidKey) => {
          // Act: Try to get setting with invalid key
          let response;
          let error = null;
          
          try {
            response = await ipcMain._simulateInvoke('get-setting', invalidKey);
          } catch (err) {
            error = err;
          }
          
          // Assert: Should not crash (no error thrown)
          expect(error).toBeNull();
          
          // Assert: Should return a response
          expect(response).toBeDefined();
          
          // Assert: Response should indicate failure for invalid keys
          if (invalidKey === '' || typeof invalidKey !== 'string') {
            expect(response.success).toBe(false);
            expect(response).toHaveProperty('error');
          }
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any IPC channel, the response should always have a
   * consistent structure (success field and appropriate data/error fields).
   */
  it('should return consistent response structure for all IPC channels', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create test cases for each IPC channel
        fc.record({
          channel: fc.constantFrom(
            'select-directory',
            'get-backend-url',
            'get-setting',
            'set-setting',
            'get-version'
          ),
          settingKey: fc.string({ minLength: 1, maxLength: 20 }),
          settingValue: fc.string()
        }),
        async ({ channel, settingKey, settingValue }) => {
          // Prepare arguments based on channel
          let args = [];
          if (channel === 'get-setting') {
            args = [settingKey];
          } else if (channel === 'set-setting') {
            args = [settingKey, settingValue];
          }
          
          // Act: Invoke the channel
          const response = await ipcMain._simulateInvoke(channel, ...args);
          
          // Assert: Response should be an object
          expect(typeof response).toBe('object');
          expect(response).not.toBeNull();
          
          // Assert: Response should have success field
          expect(response).toHaveProperty('success');
          expect(typeof response.success).toBe('boolean');
          
          // Assert: If success is true, should have appropriate data field
          if (response.success) {
            switch (channel) {
              case 'select-directory':
                expect(response).toHaveProperty('path');
                break;
              case 'get-backend-url':
                expect(response).toHaveProperty('url');
                expect(typeof response.url).toBe('string');
                break;
              case 'get-setting':
                expect(response).toHaveProperty('value');
                break;
              case 'get-version':
                expect(response).toHaveProperty('version');
                expect(typeof response.version).toBe('string');
                break;
              // set-setting doesn't need additional fields
            }
          } else {
            // Assert: If success is false, should have error field
            expect(response).toHaveProperty('error');
            expect(typeof response.error).toBe('string');
          }
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any backend URL set in global state, get-backend-url
   * should return that exact URL.
   */
  it('should return the exact backend URL from global state', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary backend URLs
        fc.record({
          protocol: fc.constantFrom('http', 'https'),
          host: fc.constantFrom('localhost', '127.0.0.1'),
          port: fc.integer({ min: 8000, max: 9000 })
        }),
        async ({ protocol, host, port }) => {
          // Setup: Set global backend URL
          const expectedUrl = `${protocol}://${host}:${port}`;
          global.backendUrl = expectedUrl;
          
          // Act: Get backend URL via IPC
          const response = await ipcMain._simulateInvoke('get-backend-url');
          
          // Assert: Should succeed
          expect(response.success).toBe(true);
          
          // Assert: Should return the exact URL
          expect(response.url).toBe(expectedUrl);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any setting key, multiple get-setting calls should
   * return the same value (idempotent reads).
   */
  it('should return consistent values for repeated get-setting calls', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create setting key and number of reads
        fc.record({
          key: fc.string({ minLength: 1, maxLength: 20 }),
          value: fc.string(),
          numReads: fc.integer({ min: 2, max: 10 })
        }),
        async ({ key, value, numReads }) => {
          // Setup: Set a value
          mockStore.set(key, value);
          
          // Act: Read the value multiple times
          const responses = await Promise.all(
            Array(numReads).fill(null).map(() => 
              ipcMain._simulateInvoke('get-setting', key)
            )
          );
          
          // Assert: All reads should succeed
          expect(responses).toHaveLength(numReads);
          responses.forEach(response => {
            expect(response.success).toBe(true);
          });
          
          // Assert: All reads should return the same value
          const values = responses.map(r => r.value);
          const firstValue = values[0];
          values.forEach(v => {
            expect(v).toEqual(firstValue);
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
   * Property: For any sequence of set-setting operations on the same key,
   * get-setting should return the value from the most recent set operation.
   */
  it('should return the most recent value after multiple set operations', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create a key and sequence of values
        fc.record({
          key: fc.string({ minLength: 1, maxLength: 20 }),
          values: fc.array(
            fc.oneof(fc.string(), fc.integer(), fc.boolean()),
            { minLength: 1, maxLength: 10 }
          )
        }),
        async ({ key, values }) => {
          // Act: Set the value multiple times
          for (const value of values) {
            const setResponse = await ipcMain._simulateInvoke('set-setting', key, value);
            expect(setResponse.success).toBe(true);
          }
          
          // Act: Get the final value
          const getResponse = await ipcMain._simulateInvoke('get-setting', key);
          
          // Assert: Should return the last value set
          const lastValue = values[values.length - 1];
          expect(getResponse.success).toBe(true);
          expect(getResponse.value).toEqual(lastValue);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });
});
