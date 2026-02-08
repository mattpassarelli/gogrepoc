// Preload script for GOGRepoc Electron application
// Exposes safe APIs to the renderer process via contextBridge
// This file will be expanded in Task 8

const { contextBridge, ipcRenderer } = require('electron');

// Expose electronAPI to renderer process
// This is a placeholder that will be expanded with actual IPC methods in Task 8
contextBridge.exposeInMainWorld('electronAPI', {
  // Placeholder methods - will be implemented in Task 8
  // selectDirectory: () => ipcRenderer.invoke('select-directory'),
  // getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  // getSetting: (key) => ipcRenderer.invoke('get-setting', key),
  // setSetting: (key, value) => ipcRenderer.invoke('set-setting', key, value),
  // getVersion: () => ipcRenderer.invoke('get-version'),
  getPlatform: () => process.platform
});

console.log('Preload script loaded');
