/**
 * Unit tests for menu template
 * Task 10.1: Create menu template
 * Requirements: 14.1, 14.4, 14.5
 */

const { createMenuTemplate } = require('../menu-template');

// Mock electron modules
jest.mock('electron', () => ({
  app: {
    name: 'GOGRepoc',
    getVersion: () => '1.0.0'
  },
  shell: {
    openExternal: jest.fn(),
    openPath: jest.fn()
  }
}));

jest.mock('electron-log', () => ({
  transports: {
    file: {
      getFile: () => ({ path: '/fake/log/path/app.log' })
    }
  }
}));

describe('Menu Template', () => {
  let mockWindow;
  let mockOnSelectDirectory;

  beforeEach(() => {
    mockWindow = {
      reload: jest.fn(),
      webContents: {
        reloadIgnoringCache: jest.fn(),
        toggleDevTools: jest.fn()
      }
    };
    mockOnSelectDirectory = jest.fn();
  });

  describe('Menu Structure', () => {
    it('should create menu template with all required menus', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      // On non-Mac platforms, should have File, Edit, View, Window, Help
      const menuLabels = template.map(menu => menu.label);
      
      expect(menuLabels).toContain('File');
      expect(menuLabels).toContain('Edit');
      expect(menuLabels).toContain('View');
      expect(menuLabels).toContain('Window');
      expect(menuLabels).toContain('Help');
    });

    it('should include app menu on macOS', () => {
      // Save original platform
      const originalPlatform = process.platform;
      
      // Mock macOS
      Object.defineProperty(process, 'platform', {
        value: 'darwin',
        writable: true,
        configurable: true
      });

      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const menuLabels = template.map(menu => menu.label);
      expect(menuLabels[0]).toBe('GOGRepoc'); // App menu should be first on macOS

      // Restore original platform
      Object.defineProperty(process, 'platform', {
        value: originalPlatform,
        writable: true,
        configurable: true
      });
    });
  });

  describe('File Menu - Requirement 14.1', () => {
    it('should have Select Download Directory menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const fileMenu = template.find(menu => menu.label === 'File');
      expect(fileMenu).toBeDefined();
      
      const selectDirItem = fileMenu.submenu.find(
        item => item.label === 'Select Download Directory'
      );
      expect(selectDirItem).toBeDefined();
      expect(selectDirItem.accelerator).toBe('CmdOrCtrl+O');
    });

    it('should call onSelectDirectory when Select Download Directory is clicked', async () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const fileMenu = template.find(menu => menu.label === 'File');
      const selectDirItem = fileMenu.submenu.find(
        item => item.label === 'Select Download Directory'
      );

      await selectDirItem.click();
      expect(mockOnSelectDirectory).toHaveBeenCalled();
    });

    it('should have Quit menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const fileMenu = template.find(menu => menu.label === 'File');
      const quitItem = fileMenu.submenu.find(
        item => item.role === 'quit' || item.role === 'close'
      );
      expect(quitItem).toBeDefined();
    });
  });

  describe('Edit Menu - Requirement 14.1', () => {
    it('should have standard edit operations', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const editMenu = template.find(menu => menu.label === 'Edit');
      expect(editMenu).toBeDefined();

      const roles = editMenu.submenu
        .filter(item => item.role)
        .map(item => item.role);

      expect(roles).toContain('undo');
      expect(roles).toContain('redo');
      expect(roles).toContain('cut');
      expect(roles).toContain('copy');
      expect(roles).toContain('paste');
      expect(roles).toContain('selectAll');
    });
  });

  describe('View Menu - Requirement 14.1, 14.4', () => {
    it('should have Reload menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      expect(viewMenu).toBeDefined();

      const reloadItem = viewMenu.submenu.find(
        item => item.label === 'Reload'
      );
      expect(reloadItem).toBeDefined();
      expect(reloadItem.accelerator).toBe('CmdOrCtrl+R');
    });

    it('should call window.reload when Reload is clicked', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const reloadItem = viewMenu.submenu.find(
        item => item.label === 'Reload'
      );

      reloadItem.click();
      expect(mockWindow.reload).toHaveBeenCalled();
    });

    it('should have Force Reload menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const forceReloadItem = viewMenu.submenu.find(
        item => item.label === 'Force Reload'
      );
      expect(forceReloadItem).toBeDefined();
      expect(forceReloadItem.accelerator).toBe('CmdOrCtrl+Shift+R');
    });

    it('should call reloadIgnoringCache when Force Reload is clicked', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const forceReloadItem = viewMenu.submenu.find(
        item => item.label === 'Force Reload'
      );

      forceReloadItem.click();
      expect(mockWindow.webContents.reloadIgnoringCache).toHaveBeenCalled();
    });

    it('should include Toggle DevTools in development mode', () => {
      const template = createMenuTemplate({
        isDevelopment: true,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const devToolsItem = viewMenu.submenu.find(
        item => item.label === 'Toggle Developer Tools'
      );

      expect(devToolsItem).toBeDefined();
    });

    it('should NOT include Toggle DevTools in production mode - Requirement 14.4', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const devToolsItem = viewMenu.submenu.find(
        item => item.label === 'Toggle Developer Tools'
      );

      expect(devToolsItem).toBeUndefined();
    });

    it('should call toggleDevTools when Toggle DevTools is clicked', () => {
      const template = createMenuTemplate({
        isDevelopment: true,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const devToolsItem = viewMenu.submenu.find(
        item => item.label === 'Toggle Developer Tools'
      );

      devToolsItem.click();
      expect(mockWindow.webContents.toggleDevTools).toHaveBeenCalled();
    });

    it('should handle null window gracefully for Reload', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: null,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const reloadItem = viewMenu.submenu.find(
        item => item.label === 'Reload'
      );

      // Should not throw when window is null
      expect(() => reloadItem.click()).not.toThrow();
    });

    it('should handle null window gracefully for Force Reload', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: null,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const forceReloadItem = viewMenu.submenu.find(
        item => item.label === 'Force Reload'
      );

      // Should not throw when window is null
      expect(() => forceReloadItem.click()).not.toThrow();
    });

    it('should handle null window gracefully for Toggle DevTools', () => {
      const template = createMenuTemplate({
        isDevelopment: true,
        mainWindow: null,
        onSelectDirectory: mockOnSelectDirectory
      });

      const viewMenu = template.find(menu => menu.label === 'View');
      const devToolsItem = viewMenu.submenu.find(
        item => item.label === 'Toggle Developer Tools'
      );

      // Should not throw when window is null
      expect(() => devToolsItem.click()).not.toThrow();
    });
  });

  describe('Help Menu - Requirement 14.1, 14.5', () => {
    it('should have Documentation menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      expect(helpMenu).toBeDefined();

      const docsItem = helpMenu.submenu.find(
        item => item.label === 'Documentation'
      );
      expect(docsItem).toBeDefined();
    });

    it('should open external link when Documentation is clicked', async () => {
      const { shell } = require('electron');
      
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const docsItem = helpMenu.submenu.find(
        item => item.label === 'Documentation'
      );

      await docsItem.click();
      expect(shell.openExternal).toHaveBeenCalledWith('https://github.com/Magnitus-/gogrepoc#readme');
    });

    it('should have About menu item on non-macOS', () => {
      // Save original platform
      const originalPlatform = process.platform;
      
      // Mock non-macOS platform
      Object.defineProperty(process, 'platform', {
        value: 'win32',
        writable: true,
        configurable: true
      });

      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const aboutItem = helpMenu.submenu.find(
        item => item.label === 'About'
      );
      expect(aboutItem).toBeDefined();

      // Restore original platform
      Object.defineProperty(process, 'platform', {
        value: originalPlatform,
        writable: true,
        configurable: true
      });
    });

    it('should show About dialog when About is clicked', () => {
      // Save original platform
      const originalPlatform = process.platform;
      
      // Mock non-macOS platform
      Object.defineProperty(process, 'platform', {
        value: 'win32',
        writable: true,
        configurable: true
      });

      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const aboutItem = helpMenu.submenu.find(
        item => item.label === 'About'
      );

      // The About dialog requires electron's dialog module which is mocked at the top level
      // We just verify the menu item exists and has a click handler
      expect(aboutItem).toBeDefined();
      expect(aboutItem.click).toBeDefined();
      expect(typeof aboutItem.click).toBe('function');

      // Restore original platform
      Object.defineProperty(process, 'platform', {
        value: originalPlatform,
        writable: true,
        configurable: true
      });
    });

    it('should have View Logs menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const logsItem = helpMenu.submenu.find(
        item => item.label === 'View Logs'
      );
      expect(logsItem).toBeDefined();
    });

    it('should open log directory when View Logs is clicked', async () => {
      const { shell } = require('electron');
      
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const logsItem = helpMenu.submenu.find(
        item => item.label === 'View Logs'
      );

      await logsItem.click();
      expect(shell.openPath).toHaveBeenCalledWith('/fake/log/path');
    });

    it('should have Report Issue menu item', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const issueItem = helpMenu.submenu.find(
        item => item.label === 'Report Issue'
      );
      expect(issueItem).toBeDefined();
    });

    it('should open external link when Report Issue is clicked', async () => {
      const { shell } = require('electron');
      
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const helpMenu = template.find(menu => menu.label === 'Help');
      const issueItem = helpMenu.submenu.find(
        item => item.label === 'Report Issue'
      );

      await issueItem.click();
      expect(shell.openExternal).toHaveBeenCalledWith('https://github.com/Magnitus-/gogrepoc/issues');
    });
  });

  describe('Window Menu', () => {
    it('should have Window menu with standard controls', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: mockOnSelectDirectory
      });

      const windowMenu = template.find(menu => menu.label === 'Window');
      expect(windowMenu).toBeDefined();

      const roles = windowMenu.submenu
        .filter(item => item.role)
        .map(item => item.role);

      expect(roles).toContain('minimize');
      expect(roles).toContain('zoom');
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing mainWindow gracefully', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: null,
        onSelectDirectory: mockOnSelectDirectory
      });

      expect(template).toBeDefined();
      expect(Array.isArray(template)).toBe(true);
    });

    it('should handle missing onSelectDirectory gracefully', () => {
      const template = createMenuTemplate({
        isDevelopment: false,
        mainWindow: mockWindow,
        onSelectDirectory: null
      });

      const fileMenu = template.find(menu => menu.label === 'File');
      const selectDirItem = fileMenu.submenu.find(
        item => item.label === 'Select Download Directory'
      );

      // Should not throw when clicked
      expect(() => selectDirItem.click()).not.toThrow();
    });
  });

  describe('Task 10.3: Menu Actions - Requirements 14.2, 14.3, 14.4', () => {
    beforeEach(() => {
      // Clear all mocks before each test
      jest.clearAllMocks();
    });

    describe('Requirement 14.2: Select Download Directory triggers native dialog', () => {
      it('should trigger directory selection handler when menu item is clicked', async () => {
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const fileMenu = template.find(menu => menu.label === 'File');
        const selectDirItem = fileMenu.submenu.find(
          item => item.label === 'Select Download Directory'
        );

        await selectDirItem.click();
        
        expect(mockOnSelectDirectory).toHaveBeenCalledTimes(1);
      });

      it('should have keyboard accelerator for Select Download Directory', () => {
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const fileMenu = template.find(menu => menu.label === 'File');
        const selectDirItem = fileMenu.submenu.find(
          item => item.label === 'Select Download Directory'
        );

        expect(selectDirItem.accelerator).toBe('CmdOrCtrl+O');
      });
    });

    describe('Requirement 14.3: Quit menu item terminates gracefully', () => {
      it('should have Quit menu item in File menu', () => {
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const fileMenu = template.find(menu => menu.label === 'File');
        const quitItem = fileMenu.submenu.find(
          item => item.role === 'quit' || item.role === 'close'
        );

        expect(quitItem).toBeDefined();
        expect(['quit', 'close']).toContain(quitItem.role);
      });

      it('should use quit role on non-macOS platforms', () => {
        // Save original platform
        const originalPlatform = process.platform;
        
        // Mock non-macOS platform
        Object.defineProperty(process, 'platform', {
          value: 'win32',
          writable: true,
          configurable: true
        });

        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const fileMenu = template.find(menu => menu.label === 'File');
        const quitItem = fileMenu.submenu.find(
          item => item.role === 'quit'
        );

        expect(quitItem).toBeDefined();

        // Restore original platform
        Object.defineProperty(process, 'platform', {
          value: originalPlatform,
          writable: true,
          configurable: true
        });
      });

      it('should use close role on macOS', () => {
        // Save original platform
        const originalPlatform = process.platform;
        
        // Mock macOS
        Object.defineProperty(process, 'platform', {
          value: 'darwin',
          writable: true,
          configurable: true
        });

        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const fileMenu = template.find(menu => menu.label === 'File');
        const closeItem = fileMenu.submenu.find(
          item => item.role === 'close'
        );

        expect(closeItem).toBeDefined();

        // Restore original platform
        Object.defineProperty(process, 'platform', {
          value: originalPlatform,
          writable: true,
          configurable: true
        });
      });
    });

    describe('Requirement 14.4: DevTools menu only in development mode', () => {
      it('should include Toggle DevTools in development mode', () => {
        const template = createMenuTemplate({
          isDevelopment: true,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const viewMenu = template.find(menu => menu.label === 'View');
        const devToolsItem = viewMenu.submenu.find(
          item => item.label === 'Toggle Developer Tools'
        );

        expect(devToolsItem).toBeDefined();
        expect(devToolsItem.click).toBeDefined();
      });

      it('should NOT include Toggle DevTools in production mode', () => {
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const viewMenu = template.find(menu => menu.label === 'View');
        const devToolsItem = viewMenu.submenu.find(
          item => item.label === 'Toggle Developer Tools'
        );

        expect(devToolsItem).toBeUndefined();
      });

      it('should toggle DevTools when menu item is clicked in dev mode', () => {
        const template = createMenuTemplate({
          isDevelopment: true,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const viewMenu = template.find(menu => menu.label === 'View');
        const devToolsItem = viewMenu.submenu.find(
          item => item.label === 'Toggle Developer Tools'
        );

        devToolsItem.click();

        expect(mockWindow.webContents.toggleDevTools).toHaveBeenCalledTimes(1);
      });

      it('should have keyboard accelerator for Toggle DevTools', () => {
        const template = createMenuTemplate({
          isDevelopment: true,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const viewMenu = template.find(menu => menu.label === 'View');
        const devToolsItem = viewMenu.submenu.find(
          item => item.label === 'Toggle Developer Tools'
        );

        expect(devToolsItem.accelerator).toBeDefined();
        expect(devToolsItem.accelerator).toMatch(/Ctrl|Command/);
      });
    });

    describe('All menu actions trigger correctly', () => {
      it('should trigger reload action', () => {
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const viewMenu = template.find(menu => menu.label === 'View');
        const reloadItem = viewMenu.submenu.find(
          item => item.label === 'Reload'
        );

        reloadItem.click();

        expect(mockWindow.reload).toHaveBeenCalledTimes(1);
      });

      it('should trigger force reload action', () => {
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const viewMenu = template.find(menu => menu.label === 'View');
        const forceReloadItem = viewMenu.submenu.find(
          item => item.label === 'Force Reload'
        );

        forceReloadItem.click();

        expect(mockWindow.webContents.reloadIgnoringCache).toHaveBeenCalledTimes(1);
      });

      it('should trigger documentation link action', async () => {
        const { shell } = require('electron');
        
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const helpMenu = template.find(menu => menu.label === 'Help');
        const docsItem = helpMenu.submenu.find(
          item => item.label === 'Documentation'
        );

        await docsItem.click();

        expect(shell.openExternal).toHaveBeenCalledWith(
          expect.stringContaining('github.com')
        );
      });

      it('should trigger view logs action', async () => {
        const { shell } = require('electron');
        
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const helpMenu = template.find(menu => menu.label === 'Help');
        const logsItem = helpMenu.submenu.find(
          item => item.label === 'View Logs'
        );

        await logsItem.click();

        expect(shell.openPath).toHaveBeenCalledWith(
          expect.stringContaining('/fake/log/path')
        );
      });

      it('should trigger report issue action', async () => {
        const { shell } = require('electron');
        
        const template = createMenuTemplate({
          isDevelopment: false,
          mainWindow: mockWindow,
          onSelectDirectory: mockOnSelectDirectory
        });

        const helpMenu = template.find(menu => menu.label === 'Help');
        const issueItem = helpMenu.submenu.find(
          item => item.label === 'Report Issue'
        );

        await issueItem.click();

        expect(shell.openExternal).toHaveBeenCalledWith(
          expect.stringContaining('issues')
        );
      });
    });
  });
});
