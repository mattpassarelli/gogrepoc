/**
 * Unit tests for IPC handlers
 * Task 8.4: Write unit tests for IPC handlers
 * Requirements: 6.3
 * 
 * Tests the IPC handlers in main.js:
 * - Directory selection with valid selection
 * - Directory selection with cancellation
 * - Backend URL retrieval
 * - Settings get/set operations
 */

// Create mock handlers storage before any imports
const mockHandlers = {};

// Mock electron modules
jest.mock('electron', () => ({
  ipcMain: {
    handle: jest.fn((channel, handler) => {
      mockHandlers[channel] = handler;
    })
  },
  dialog: {
    showOpenDialog: jest.fn()
  },
  app: {
    getVersion: jest.fn(() => '1.0.0'),
    getAppPath: jest.fn(() => '/mock/app/path'),
    getPath: jest.fn(() => '/mock/user/data'),
    whenReady: jest.fn(() => Promise.resolve()),
    on: jest.fn(),
    quit: jest.fn(),
    isPackaged: false
  },
  BrowserWindow: jest.fn(),
  screen: {
    getAllDisplays: jest.fn(() => [
      { bounds: { x: 0, y: 0, width: 1920, height: 1080 } }
    ])
  }
}));

// Mock electron-log
jest.mock('electron-log', () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  transports: {
    file: {
      level: 'info',
      maxSize: 10 * 1024 * 1024,
      format: '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}',
      getFile: () => ({ path: '/mock/log/path' })
    }
  }
}));

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
  getBackendExecutablePath: jest.fn(() => null),
  normalizePath: jest.fn((p) => p)
}));

const { ipcMain, dialog } = require('electron');

describe('IPC Handlers', () => {
  let handlers;
  let mockMainWindow;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Clear handlers
    Object.keys(mockHandlers).forEach(key => delete mockHandlers[key]);
    
    // Create mock main window
    mockMainWindow = {
      getBounds: jest.fn(() => ({ width: 1024, height: 768, x: 100, y: 100 })),
      loadFile: jest.fn(),
      on: jest.fn(),
      webContents: {
        openDevTools: jest.fn()
      }
    };
    
    // Set up global state
    global.backendUrl = 'http://localhost:8000';
    
    // Require main.js to register handlers
    const main = require('../main');
    
    // Set the mock main window
    main.setMainWindow(mockMainWindow);
    
    // Call registerIpcHandlers to set up handlers
    main.registerIpcHandlers();
    
    // Copy handlers for easier access in tests
    handlers = mockHandlers;
  });

  afterEach(() => {
    // Clean up global state
    delete global.backendUrl;
    
    // Clean up main window
    const main = require('../main');
    main.setMainWindow(null);
  });

  describe('select-directory handler', () => {
    it('should return selected directory path on valid selection', async () => {
      // Mock dialog to return a selected path
      const selectedPath = '/home/user/downloads';
      dialog.showOpenDialog.mockResolvedValue({
        canceled: false,
        filePaths: [selectedPath]
      });
      
      // Mock store.get to return a last directory
      mockStore.get.mockReturnValue('/home/user/documents');
      
      // Call the handler
      const handler = handlers['select-directory'];
      expect(handler).toBeDefined();
      
      const result = await handler();
      
      // Verify dialog was called with correct options
      expect(dialog.showOpenDialog).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          properties: ['openDirectory'],
          defaultPath: '/home/user/documents'
        })
      );
      
      // Verify result
      expect(result).toEqual({
        success: true,
        path: selectedPath
      });
      
      // Verify path was saved to settings
      expect(mockStore.set).toHaveBeenCalledWith('lastDirectory', selectedPath);
    });

    it('should handle directory selection cancellation gracefully', async () => {
      // Mock dialog to return cancelled
      dialog.showOpenDialog.mockResolvedValue({
        canceled: true,
        filePaths: []
      });
      
      // Call the handler
      const handler = handlers['select-directory'];
      const result = await handler();
      
      // Verify result indicates cancellation
      expect(result).toEqual({
        success: false,
        error: 'User cancelled'
      });
      
      // Verify path was NOT saved to settings
      expect(mockStore.set).not.toHaveBeenCalled();
    });

    it('should use null as defaultPath when no last directory is saved', async () => {
      // Mock store.get to return null
      mockStore.get.mockReturnValue(null);
      
      // Mock dialog to return a selected path
      dialog.showOpenDialog.mockResolvedValue({
        canceled: false,
        filePaths: ['/home/user/downloads']
      });
      
      // Call the handler
      const handler = handlers['select-directory'];
      await handler();
      
      // Verify dialog was called with undefined defaultPath
      expect(dialog.showOpenDialog).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          properties: ['openDirectory'],
          defaultPath: undefined
        })
      );
    });

    it('should handle dialog errors gracefully', async () => {
      // Mock dialog to throw an error
      const errorMessage = 'Dialog failed to open';
      dialog.showOpenDialog.mockRejectedValue(new Error(errorMessage));
      
      // Call the handler
      const handler = handlers['select-directory'];
      const result = await handler();
      
      // Verify result contains error
      expect(result).toEqual({
        success: false,
        error: errorMessage
      });
    });

    it('should handle unexpected dialog result (not cancelled but no paths)', async () => {
      // Mock dialog to return an unexpected result
      dialog.showOpenDialog.mockResolvedValue({
        canceled: false,
        filePaths: []
      });
      
      // Call the handler
      const handler = handlers['select-directory'];
      const result = await handler();
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'No directory selected'
      });
    });

    it('should remember last selected directory for subsequent selections', async () => {
      // First selection
      const firstPath = '/home/user/downloads';
      dialog.showOpenDialog.mockResolvedValue({
        canceled: false,
        filePaths: [firstPath]
      });
      
      mockStore.get.mockReturnValue(null);
      
      const handler = handlers['select-directory'];
      await handler();
      
      // Verify first path was saved
      expect(mockStore.set).toHaveBeenCalledWith('lastDirectory', firstPath);
      
      // Second selection - mock store to return first path
      const secondPath = '/home/user/documents';
      mockStore.get.mockReturnValue(firstPath);
      dialog.showOpenDialog.mockResolvedValue({
        canceled: false,
        filePaths: [secondPath]
      });
      
      await handler();
      
      // Verify dialog used first path as default
      expect(dialog.showOpenDialog).toHaveBeenLastCalledWith(
        expect.anything(),
        expect.objectContaining({
          defaultPath: firstPath
        })
      );
      
      // Verify second path was saved
      expect(mockStore.set).toHaveBeenLastCalledWith('lastDirectory', secondPath);
    });
  });

  describe('get-backend-url handler', () => {
    it('should return backend URL when available', async () => {
      // Set global backend URL
      global.backendUrl = 'http://localhost:8123';
      
      // Call the handler
      const handler = handlers['get-backend-url'];
      expect(handler).toBeDefined();
      
      const result = await handler();
      
      // Verify result
      expect(result).toEqual({
        success: true,
        url: 'http://localhost:8123'
      });
    });

    it('should return error when backend URL is not available', async () => {
      // Clear global backend URL
      global.backendUrl = null;
      
      // Call the handler
      const handler = handlers['get-backend-url'];
      const result = await handler();
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'Backend URL not available'
      });
    });

    it('should return error when backend URL is undefined', async () => {
      // Delete global backend URL
      delete global.backendUrl;
      
      // Call the handler
      const handler = handlers['get-backend-url'];
      const result = await handler();
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'Backend URL not available'
      });
    });

    it('should handle different port numbers correctly', async () => {
      // Test with various port numbers
      const ports = [8000, 8080, 9000, 3000];
      
      for (const port of ports) {
        global.backendUrl = `http://localhost:${port}`;
        
        const handler = handlers['get-backend-url'];
        const result = await handler();
        
        expect(result).toEqual({
          success: true,
          url: `http://localhost:${port}`
        });
      }
    });
  });

  describe('get-setting handler', () => {
    it('should retrieve setting value by key', async () => {
      // Mock store to return a value
      const settingKey = 'lastDirectory';
      const settingValue = '/home/user/downloads';
      mockStore.get.mockReturnValue(settingValue);
      
      // Call the handler
      const handler = handlers['get-setting'];
      expect(handler).toBeDefined();
      
      const result = await handler(null, settingKey);
      
      // Verify store.get was called with correct key
      expect(mockStore.get).toHaveBeenCalledWith(settingKey);
      
      // Verify result
      expect(result).toEqual({
        success: true,
        value: settingValue
      });
    });

    it('should return null for non-existent setting', async () => {
      // Mock store to return null
      mockStore.get.mockReturnValue(null);
      
      // Call the handler
      const handler = handlers['get-setting'];
      const result = await handler(null, 'nonExistentKey');
      
      // Verify result
      expect(result).toEqual({
        success: true,
        value: null
      });
    });

    it('should handle invalid setting key (null)', async () => {
      // Call the handler with null key
      const handler = handlers['get-setting'];
      const result = await handler(null, null);
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'Invalid setting key'
      });
      
      // Verify store.get was not called
      expect(mockStore.get).not.toHaveBeenCalled();
    });

    it('should handle invalid setting key (non-string)', async () => {
      // Call the handler with non-string key
      const handler = handlers['get-setting'];
      const result = await handler(null, 123);
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'Invalid setting key'
      });
      
      // Verify store.get was not called
      expect(mockStore.get).not.toHaveBeenCalled();
    });

    it('should retrieve different types of setting values', async () => {
      const handler = handlers['get-setting'];
      
      // Test string value
      mockStore.get.mockReturnValue('string value');
      let result = await handler(null, 'stringKey');
      expect(result.value).toBe('string value');
      
      // Test number value
      mockStore.get.mockReturnValue(42);
      result = await handler(null, 'numberKey');
      expect(result.value).toBe(42);
      
      // Test boolean value
      mockStore.get.mockReturnValue(true);
      result = await handler(null, 'booleanKey');
      expect(result.value).toBe(true);
      
      // Test object value
      const objectValue = { width: 1024, height: 768 };
      mockStore.get.mockReturnValue(objectValue);
      result = await handler(null, 'objectKey');
      expect(result.value).toEqual(objectValue);
      
      // Test array value
      const arrayValue = [1, 2, 3];
      mockStore.get.mockReturnValue(arrayValue);
      result = await handler(null, 'arrayKey');
      expect(result.value).toEqual(arrayValue);
    });

    it('should handle store errors gracefully', async () => {
      // Mock store.get to throw an error
      const errorMessage = 'Store read failed';
      mockStore.get.mockImplementation(() => {
        throw new Error(errorMessage);
      });
      
      // Call the handler
      const handler = handlers['get-setting'];
      const result = await handler(null, 'testKey');
      
      // Verify result contains error
      expect(result).toEqual({
        success: false,
        error: errorMessage
      });
    });
  });

  describe('set-setting handler', () => {
    it('should save setting value by key', async () => {
      // Call the handler
      const handler = handlers['set-setting'];
      expect(handler).toBeDefined();
      
      const settingKey = 'lastDirectory';
      const settingValue = '/home/user/downloads';
      
      const result = await handler(null, settingKey, settingValue);
      
      // Verify store.set was called with correct key and value
      expect(mockStore.set).toHaveBeenCalledWith(settingKey, settingValue);
      
      // Verify result
      expect(result).toEqual({
        success: true
      });
    });

    it('should handle invalid setting key (null)', async () => {
      // Call the handler with null key
      const handler = handlers['set-setting'];
      const result = await handler(null, null, 'value');
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'Invalid setting key'
      });
      
      // Verify store.set was not called
      expect(mockStore.set).not.toHaveBeenCalled();
    });

    it('should handle invalid setting key (non-string)', async () => {
      // Call the handler with non-string key
      const handler = handlers['set-setting'];
      const result = await handler(null, 123, 'value');
      
      // Verify result indicates error
      expect(result).toEqual({
        success: false,
        error: 'Invalid setting key'
      });
      
      // Verify store.set was not called
      expect(mockStore.set).not.toHaveBeenCalled();
    });

    it('should save different types of setting values', async () => {
      const handler = handlers['set-setting'];
      
      // Test string value
      await handler(null, 'stringKey', 'string value');
      expect(mockStore.set).toHaveBeenCalledWith('stringKey', 'string value');
      
      // Test number value
      await handler(null, 'numberKey', 42);
      expect(mockStore.set).toHaveBeenCalledWith('numberKey', 42);
      
      // Test boolean value
      await handler(null, 'booleanKey', true);
      expect(mockStore.set).toHaveBeenCalledWith('booleanKey', true);
      
      // Test object value
      const objectValue = { width: 1024, height: 768 };
      await handler(null, 'objectKey', objectValue);
      expect(mockStore.set).toHaveBeenCalledWith('objectKey', objectValue);
      
      // Test array value
      const arrayValue = [1, 2, 3];
      await handler(null, 'arrayKey', arrayValue);
      expect(mockStore.set).toHaveBeenCalledWith('arrayKey', arrayValue);
      
      // Test null value
      await handler(null, 'nullKey', null);
      expect(mockStore.set).toHaveBeenCalledWith('nullKey', null);
    });

    it('should handle store errors gracefully', async () => {
      // Mock store.set to throw an error
      const errorMessage = 'Store write failed';
      mockStore.set.mockImplementation(() => {
        throw new Error(errorMessage);
      });
      
      // Call the handler
      const handler = handlers['set-setting'];
      const result = await handler(null, 'testKey', 'testValue');
      
      // Verify result contains error
      expect(result).toEqual({
        success: false,
        error: errorMessage
      });
    });

    it('should overwrite existing setting value', async () => {
      const handler = handlers['set-setting'];
      const settingKey = 'testKey';
      
      // Set initial value
      await handler(null, settingKey, 'initial value');
      expect(mockStore.set).toHaveBeenCalledWith(settingKey, 'initial value');
      
      // Overwrite with new value
      await handler(null, settingKey, 'new value');
      expect(mockStore.set).toHaveBeenCalledWith(settingKey, 'new value');
      
      // Verify set was called twice
      expect(mockStore.set).toHaveBeenCalledTimes(2);
    });
  });

  describe('get-version handler', () => {
    it('should return application version', async () => {
      // Mock app.getVersion
      const { app } = require('electron');
      app.getVersion.mockReturnValue('2.0.1');
      
      // Call the handler
      const handler = handlers['get-version'];
      expect(handler).toBeDefined();
      
      const result = await handler();
      
      // Verify result
      expect(result).toEqual({
        success: true,
        version: '2.0.1'
      });
    });

    it('should handle different version formats', async () => {
      const { app } = require('electron');
      const handler = handlers['get-version'];
      
      // Test various version formats
      const versions = ['1.0.0', '2.1.3', '0.0.1', '10.20.30', '1.0.0-beta.1'];
      
      for (const version of versions) {
        app.getVersion.mockReturnValue(version);
        const result = await handler();
        
        expect(result).toEqual({
          success: true,
          version: version
        });
      }
    });

    it('should handle errors when getting version', async () => {
      // Mock app.getVersion to throw an error
      const { app } = require('electron');
      const errorMessage = 'Failed to get version';
      app.getVersion.mockImplementation(() => {
        throw new Error(errorMessage);
      });
      
      // Call the handler
      const handler = handlers['get-version'];
      const result = await handler();
      
      // Verify result contains error
      expect(result).toEqual({
        success: false,
        error: errorMessage
      });
    });
  });

  describe('IPC handler registration', () => {
    it('should register all required IPC handlers', () => {
      // Verify all handlers are registered
      expect(handlers).toHaveProperty('select-directory');
      expect(handlers).toHaveProperty('get-backend-url');
      expect(handlers).toHaveProperty('get-setting');
      expect(handlers).toHaveProperty('set-setting');
      expect(handlers).toHaveProperty('get-version');
    });

    it('should register handlers as functions', () => {
      // Verify all handlers are functions
      expect(typeof handlers['select-directory']).toBe('function');
      expect(typeof handlers['get-backend-url']).toBe('function');
      expect(typeof handlers['get-setting']).toBe('function');
      expect(typeof handlers['set-setting']).toBe('function');
      expect(typeof handlers['get-version']).toBe('function');
    });

    it('should use ipcMain.handle for all handlers', () => {
      // Verify ipcMain.handle was called for each handler
      expect(ipcMain.handle).toHaveBeenCalledWith('select-directory', expect.any(Function));
      expect(ipcMain.handle).toHaveBeenCalledWith('get-backend-url', expect.any(Function));
      expect(ipcMain.handle).toHaveBeenCalledWith('get-setting', expect.any(Function));
      expect(ipcMain.handle).toHaveBeenCalledWith('set-setting', expect.any(Function));
      expect(ipcMain.handle).toHaveBeenCalledWith('get-version', expect.any(Function));
    });
  });

  describe('Error handling consistency', () => {
    it('should return consistent error format across all handlers', async () => {
      // Test that all handlers return { success: false, error: string } on error
      
      // select-directory error
      dialog.showOpenDialog.mockRejectedValue(new Error('Dialog error'));
      const selectDirResult = await handlers['select-directory']();
      expect(selectDirResult).toMatchObject({
        success: false,
        error: expect.any(String)
      });
      
      // get-backend-url error
      delete global.backendUrl;
      const backendUrlResult = await handlers['get-backend-url']();
      expect(backendUrlResult).toMatchObject({
        success: false,
        error: expect.any(String)
      });
      
      // get-setting error
      const getSettingResult = await handlers['get-setting'](null, null);
      expect(getSettingResult).toMatchObject({
        success: false,
        error: expect.any(String)
      });
      
      // set-setting error
      const setSettingResult = await handlers['set-setting'](null, null, 'value');
      expect(setSettingResult).toMatchObject({
        success: false,
        error: expect.any(String)
      });
    });

    it('should return consistent success format across all handlers', async () => {
      // Test that all handlers return { success: true, ... } on success
      
      // select-directory success
      // Clear any previous mock calls and set up fresh mock
      dialog.showOpenDialog.mockClear();
      dialog.showOpenDialog.mockResolvedValue({
        canceled: false,
        filePaths: ['/test/path']
      });
      mockStore.get.mockReturnValue(null);
      // Reset mockStore.set to not throw errors
      mockStore.set.mockClear();
      mockStore.set.mockImplementation(() => {});
      
      const selectDirResult = await handlers['select-directory']();
      expect(selectDirResult).toMatchObject({
        success: true
      });
      
      // get-backend-url success
      global.backendUrl = 'http://localhost:8000';
      const backendUrlResult = await handlers['get-backend-url']();
      expect(backendUrlResult).toMatchObject({
        success: true
      });
      
      // get-setting success
      mockStore.get.mockReturnValue('test value');
      const getSettingResult = await handlers['get-setting'](null, 'testKey');
      expect(getSettingResult).toMatchObject({
        success: true
      });
      
      // set-setting success
      mockStore.set.mockImplementation(() => {});
      const setSettingResult = await handlers['set-setting'](null, 'testKey', 'value');
      expect(setSettingResult).toMatchObject({
        success: true
      });
      
      // get-version success
      const { app } = require('electron');
      app.getVersion.mockReturnValue('1.0.0');
      const versionResult = await handlers['get-version']();
      expect(versionResult).toMatchObject({
        success: true
      });
    });
  });
});
