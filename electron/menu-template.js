/**
 * Application Menu Template
 * Task 10.1: Create menu template
 * Requirements: 14.1, 14.4, 14.5
 */

const { app, shell } = require('electron');

/**
 * Create the application menu template
 * @param {Object} options - Menu configuration options
 * @param {boolean} options.isDevelopment - Whether running in development mode
 * @param {BrowserWindow} options.mainWindow - Main application window
 * @param {Function} options.onSelectDirectory - Handler for directory selection
 * @returns {Array} Menu template array
 */
function createMenuTemplate({ isDevelopment, mainWindow, onSelectDirectory }) {
  const isMac = process.platform === 'darwin';

  const template = [
    // App menu (macOS only)
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }] : []),

    // File menu
    // Requirement 14.1: File menu with Select Download Directory and Quit
    // Requirement 14.2: "Select Download Directory" displays native dialog
    {
      label: 'File',
      submenu: [
        {
          label: 'Select Download Directory',
          accelerator: 'CmdOrCtrl+O',
          click: async () => {
            if (onSelectDirectory) {
              await onSelectDirectory();
            }
          }
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' }
      ]
    },

    // Edit menu
    // Requirement 14.1: Edit menu with standard edit operations
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        ...(isMac ? [
          { role: 'pasteAndMatchStyle' },
          { role: 'delete' },
          { role: 'selectAll' },
          { type: 'separator' },
          {
            label: 'Speech',
            submenu: [
              { role: 'startSpeaking' },
              { role: 'stopSpeaking' }
            ]
          }
        ] : [
          { role: 'delete' },
          { type: 'separator' },
          { role: 'selectAll' }
        ])
      ]
    },

    // View menu
    // Requirement 14.1: View menu with Reload and Toggle DevTools (dev mode only)
    // Requirement 14.4: DevTools toggle only in development mode
    {
      label: 'View',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => {
            if (mainWindow) {
              mainWindow.reload();
            }
          }
        },
        {
          label: 'Force Reload',
          accelerator: 'CmdOrCtrl+Shift+R',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.reloadIgnoringCache();
            }
          }
        },
        ...(isDevelopment ? [
          { type: 'separator' },
          {
            label: 'Toggle Developer Tools',
            accelerator: isMac ? 'Alt+Command+I' : 'Ctrl+Shift+I',
            click: () => {
              if (mainWindow) {
                mainWindow.webContents.toggleDevTools();
              }
            }
          }
        ] : []),
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },

    // Window menu
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front' },
          { type: 'separator' },
          { role: 'window' }
        ] : [
          { role: 'close' }
        ])
      ]
    },

    // Help menu
    // Requirement 14.1: Help menu with Documentation and About
    // Requirement 14.5: Help menu includes links to documentation and About dialog
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation',
          click: async () => {
            await shell.openExternal('https://github.com/Magnitus-/gogrepoc#readme');
          }
        },
        {
          label: 'View Logs',
          click: async () => {
            const log = require('electron-log');
            const logPath = log.transports.file.getFile().path;
            const logDir = require('path').dirname(logPath);
            await shell.openPath(logDir);
          }
        },
        { type: 'separator' },
        {
          label: 'Report Issue',
          click: async () => {
            await shell.openExternal('https://github.com/Magnitus-/gogrepoc/issues');
          }
        },
        ...(!isMac ? [
          { type: 'separator' },
          {
            label: 'About',
            click: () => {
              const { dialog } = require('electron');
              dialog.showMessageBox(mainWindow, {
                type: 'info',
                title: 'About GOGRepoc',
                message: 'GOGRepoc',
                detail: `Version: ${app.getVersion()}\n\nA tool for managing your GOG game library.\n\nCopyright © 2025`,
                buttons: ['OK']
              });
            }
          }
        ] : [])
      ]
    }
  ];

  return template;
}

module.exports = {
  createMenuTemplate
};
