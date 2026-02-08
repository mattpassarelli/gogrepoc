/**
 * Tests for preload script
 * Task 8.1: Create preload script with contextBridge
 * Requirements: 6.2, 6.4
 */

describe('Preload Script', () => {
  let mockContextBridge;
  let mockIpcRenderer;
  let exposedAPI;

  beforeEach(() => {
    // Mock contextBridge
    mockContextBridge = {
      exposeInMainWorld: jest.fn((apiKey, api) => {
        exposedAPI = api;
      })
    };

    // Mock ipcRenderer
    mockIpcRenderer = {
      invoke: jest.fn()
    };

    // Mock require to return our mocks
    jest.resetModules();
    jest.mock('electron', () => ({
      contextBridge: mockContextBridge,
      ipcRenderer: mockIpcRenderer
    }));

    // Load the preload script
    require('../preload');
  });

  afterEach(() => {
    jest.unmock('electron');
  });

  describe('contextBridge.exposeInMainWorld', () => {
    it('should expose electronAPI to main world', () => {
      expect(mockContextBridge.exposeInMainWorld).toHaveBeenCalledWith(
        'electronAPI',
        expect.any(Object)
      );
    });

    it('should expose all required methods', () => {
      expect(exposedAPI).toHaveProperty('selectDirectory');
      expect(exposedAPI).toHaveProperty('getBackendUrl');
      expect(exposedAPI).toHaveProperty('getSetting');
      expect(exposedAPI).toHaveProperty('setSetting');
      expect(exposedAPI).toHaveProperty('getVersion');
      expect(exposedAPI).toHaveProperty('getPlatform');
    });

    it('should expose methods as functions', () => {
      expect(typeof exposedAPI.selectDirectory).toBe('function');
      expect(typeof exposedAPI.getBackendUrl).toBe('function');
      expect(typeof exposedAPI.getSetting).toBe('function');
      expect(typeof exposedAPI.setSetting).toBe('function');
      expect(typeof exposedAPI.getVersion).toBe('function');
      expect(typeof exposedAPI.getPlatform).toBe('function');
    });
  });

  describe('selectDirectory', () => {
    it('should invoke select-directory IPC channel', () => {
      exposedAPI.selectDirectory();
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('select-directory');
    });
  });

  describe('getBackendUrl', () => {
    it('should invoke get-backend-url IPC channel', () => {
      exposedAPI.getBackendUrl();
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('get-backend-url');
    });
  });

  describe('getSetting', () => {
    it('should invoke get-setting IPC channel with key', () => {
      exposedAPI.getSetting('testKey');
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('get-setting', 'testKey');
    });
  });

  describe('setSetting', () => {
    it('should invoke set-setting IPC channel with key and value', () => {
      exposedAPI.setSetting('testKey', 'testValue');
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('set-setting', 'testKey', 'testValue');
    });
  });

  describe('getVersion', () => {
    it('should invoke get-version IPC channel', () => {
      exposedAPI.getVersion();
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('get-version');
    });
  });

  describe('getPlatform', () => {
    it('should return process.platform', () => {
      const platform = exposedAPI.getPlatform();
      expect(platform).toBe(process.platform);
    });

    it('should not use IPC for platform', () => {
      exposedAPI.getPlatform();
      expect(mockIpcRenderer.invoke).not.toHaveBeenCalled();
    });
  });
});
