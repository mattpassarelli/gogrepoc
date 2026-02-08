/**
 * Path resolution utilities for Electron application
 * Handles development vs production mode path resolution,
 * platform-specific path separators, and resource verification.
 */

const path = require('path');
const fs = require('fs');
const log = require('electron-log');

/**
 * Determine if running in development mode
 * @returns {boolean} True if in development mode
 */
function isDevelopmentMode() {
  // Check multiple indicators for development mode
  return process.env.NODE_ENV === 'development' || 
         process.argv.includes('--dev') || 
         (typeof process.resourcesPath === 'undefined');
}

/**
 * Normalize path to use platform-specific separators
 * @param {string} filePath - Path to normalize
 * @returns {string} Normalized path with correct separators
 */
function normalizePath(filePath) {
  if (!filePath) {
    return filePath;
  }

  // Use path.normalize to handle platform-specific separators
  // This converts all separators to the platform's native separator
  return path.normalize(filePath);
}

/**
 * Get the path to the backend executable
 * @returns {string|null} Path to backend executable, or null in development mode
 * @throws {Error} If backend executable is missing in production mode
 */
function getBackendExecutablePath() {
  const isDev = isDevelopmentMode();
  
  if (isDev) {
    // In development mode, expect backend to be run separately
    log.info('Development mode: backend should be run separately');
    return null;
  }

  // In production, backend is bundled in resources
  const platform = process.platform;
  const exeName = platform === 'win32' ? 'gogrepoc-backend.exe' : 'gogrepoc-backend';
  
  // Check if we're in Electron context
  if (typeof process.resourcesPath === 'undefined') {
    const error = new Error('Not in Electron context, cannot determine backend path');
    log.error(error.message);
    throw error;
  }
  
  const backendPath = path.join(process.resourcesPath, 'backend', exeName);
  const normalizedPath = normalizePath(backendPath);
  
  // Verify the backend executable exists
  if (!fs.existsSync(normalizedPath)) {
    const error = new Error(
      `Backend executable not found at: ${normalizedPath}\n` +
      `Platform: ${platform}\n` +
      `Expected file: ${exeName}\n` +
      `Resources path: ${process.resourcesPath}\n` +
      `Please reinstall the application.`
    );
    log.error(error.message);
    throw error;
  }

  // Verify the file is executable (on Unix-like systems)
  if (platform !== 'win32') {
    try {
      fs.accessSync(normalizedPath, fs.constants.X_OK);
    } catch (err) {
      const error = new Error(
        `Backend executable found but is not executable: ${normalizedPath}\n` +
        `Please check file permissions.`
      );
      log.error(error.message);
      throw error;
    }
  }
  
  log.info(`Backend executable path: ${normalizedPath}`);
  return normalizedPath;
}

/**
 * Get the path to a resource file
 * @param {string} relativePath - Relative path to the resource (e.g., 'icons/app.png')
 * @param {Object} options - Options for resource resolution
 * @param {boolean} options.required - If true, throw error if resource doesn't exist (default: true)
 * @param {string} options.devBasePath - Base path for development mode (default: __dirname)
 * @returns {string} Absolute path to the resource
 * @throws {Error} If resource is required but not found
 */
function getResourcePath(relativePath, options = {}) {
  const { required = true, devBasePath = __dirname } = options;
  const isDev = isDevelopmentMode();
  
  let resourcePath;
  
  if (isDev) {
    // In development mode, resources are relative to the project directory
    resourcePath = path.join(devBasePath, relativePath);
  } else {
    // In production, resources are in the app.asar or resources directory
    if (typeof process.resourcesPath === 'undefined') {
      const error = new Error('Not in Electron context, cannot determine resource path');
      log.error(error.message);
      throw error;
    }
    
    resourcePath = path.join(process.resourcesPath, relativePath);
  }
  
  const normalizedPath = normalizePath(resourcePath);
  
  // Verify the resource exists if required
  if (required && !fs.existsSync(normalizedPath)) {
    const error = new Error(
      `Required resource not found: ${relativePath}\n` +
      `Expected location: ${normalizedPath}\n` +
      `Mode: ${isDev ? 'development' : 'production'}\n` +
      `Please ensure the resource is included in the build.`
    );
    log.error(error.message);
    throw error;
  }
  
  log.info(`Resource path resolved: ${relativePath} -> ${normalizedPath}`);
  return normalizedPath;
}

/**
 * Verify that a path exists and is accessible
 * @param {string} filePath - Path to verify
 * @param {string} description - Description of the resource for error messages
 * @throws {Error} If path doesn't exist or is not accessible
 */
function verifyPathExists(filePath, description = 'Resource') {
  const normalizedPath = normalizePath(filePath);
  
  if (!fs.existsSync(normalizedPath)) {
    const error = new Error(
      `${description} not found: ${normalizedPath}\n` +
      `Please ensure the file exists.`
    );
    log.error(error.message);
    throw error;
  }
  
  // Try to access the file to ensure we have permissions
  try {
    fs.accessSync(normalizedPath, fs.constants.R_OK);
  } catch (err) {
    const error = new Error(
      `${description} exists but is not readable: ${normalizedPath}\n` +
      `Please check file permissions.\n` +
      `Original error: ${err.message}`
    );
    log.error(error.message);
    throw error;
  }
  
  log.info(`Path verified: ${normalizedPath}`);
  return normalizedPath;
}

/**
 * Get the base path for the application
 * @returns {string} Base path (app directory in dev, resources path in production)
 */
function getBasePath() {
  const isDev = isDevelopmentMode();
  
  if (isDev) {
    // In development, use the current directory
    return __dirname;
  } else {
    // In production, use the resources path
    if (typeof process.resourcesPath === 'undefined') {
      const error = new Error('Not in Electron context, cannot determine base path');
      log.error(error.message);
      throw error;
    }
    return process.resourcesPath;
  }
}

module.exports = {
  isDevelopmentMode,
  normalizePath,
  getBackendExecutablePath,
  getResourcePath,
  verifyPathExists,
  getBasePath
};
