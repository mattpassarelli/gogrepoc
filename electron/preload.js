// Preload script for GOGRepoc Electron application
// Exposes safe APIs to the renderer process via contextBridge
// Task 8.1: Create preload script with contextBridge
// Requirements: 6.2 (preload scripts for secure IPC), 6.4 (contextBridge to expose only necessary APIs)

const { contextBridge, ipcRenderer } = require('electron');

/**
 * Expose electronAPI to renderer process
 * Uses contextBridge to securely expose IPC functionality
 * Requirement 6.4: Use contextBridge to expose only necessary APIs to the renderer
 * Requirement 6.2: Renderer process uses preload scripts to access IPC functionality securely
 */
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Open native directory selection dialog
   * @returns {Promise<string|null>} Selected directory path or null if cancelled
   */
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  /**
   * Get the backend URL (with dynamically assigned port)
   * @returns {Promise<string>} Backend URL (e.g., 'http://localhost:8000')
   */
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  
  /**
   * Get a setting value from persistent storage
   * @param {string} key - Setting key
   * @returns {Promise<any>} Setting value
   */
  getSetting: (key) => ipcRenderer.invoke('get-setting', key),
  
  /**
   * Set a setting value in persistent storage
   * @param {string} key - Setting key
   * @param {any} value - Setting value
   * @returns {Promise<void>}
   */
  setSetting: (key, value) => ipcRenderer.invoke('set-setting', key, value),
  
  /**
   * Get the application version
   * @returns {Promise<string>} Application version
   */
  getVersion: () => ipcRenderer.invoke('get-version'),
  
  /**
   * Get the current platform
   * @returns {string} Platform identifier ('win32', 'darwin', 'linux', etc.)
   */
  getPlatform: () => process.platform
});

console.log('Preload script loaded - electronAPI exposed to renderer');
