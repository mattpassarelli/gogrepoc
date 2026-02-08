/**
 * Integration tests for menu creation in main process
 * Task 10.1: Create menu template
 * Requirements: 14.1, 14.4, 14.5
 */

const { Menu } = require('electron');
const { createApplicationMenu, handleMenuSelectDirectory } = require('../main');

// Mock electron modules
jest.mock('electron', () => {
  const mockMenu = {
    buildFromTemplate: jest.fn((template) => template),
    setApplicationMenu: jest.fn()
  };

  return {
    app: {
      name: 'GOGRepoc',
      getVersion: () => '1.0.0',
      getAppPath: () => '/fake/app/path',
      getPath: () => '/fake/user/data',
      whenReady: () => Promise.resolve(),
      on: jest.fn(),
      quit: jest.fn(),
      isPackaged: false
    },
    BrowserWindow: jest.fn(),
    ipcMain: {
      handle: jest.fn()
    },
    dialog: {
      showOpenDialog: jest.fn(),
      showMessageBox: jest.fn()
    },
    Menu: mockMenu,
    shell: {
      openExternal: jest.fn(),
      openPath: jest.fn()
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
      getFile: () => ({ path: '/fake/log/path/app.log' })
    }
  }
}));

jest.mock('electron-store');

describe('Menu Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createApplicationMenu', () => {
    it('should build and set application menu', () => {
      createApplicationMenu();

      expect(Menu.buildFromTemplate).toHaveBeenCalled();
      expect(Menu.setApplicationMenu).toHaveBeenCalled();
    });

    it('should create menu with correct structure', () => {
      createApplicationMenu();

      const template = Menu.buildFromTemplate.mock.calls[0][0];
      expect(Array.isArray(template)).toBe(true);
      expect(template.length).toBeGreaterThan(0);

      // Verify main menu labels exist
      const menuLabels = template.map(menu => menu.label);
      expect(menuLabels).toContain('File');
      expect(menuLabels).toContain('Edit');
      expect(menuLabels).toContain('View');
      expect(menuLabels).toContain('Help');
    });
  });

  describe('handleMenuSelectDirectory', () => {
    it('should be a function', () => {
      expect(typeof handleMenuSelectDirectory).toBe('function');
    });

    it('should handle missing mainWindow gracefully', async () => {
      // Should not throw when mainWindow is null
      await expect(handleMenuSelectDirectory()).resolves.not.toThrow();
    });
  });
});
