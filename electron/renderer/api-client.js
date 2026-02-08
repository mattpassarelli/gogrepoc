/**
 * API Client for GOGRepoc Backend
 * 
 * Provides methods to communicate with the FastAPI backend running in the
 * Electron main process. Includes error handling with retry logic for
 * transient failures.
 * 
 * Requirements: 7.1, 7.4, 7.5
 */

/**
 * Custom error classes for API client
 */
class APIError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.details = details;
  }
}

class NetworkError extends Error {
  constructor(message, originalError = null) {
    super(message);
    this.name = 'NetworkError';
    this.originalError = originalError;
  }
}

/**
 * APIClient class for communicating with the GOGRepoc backend
 */
class APIClient {
  /**
   * Create an API client instance
   * @param {string} baseUrl - Base URL of the backend (e.g., http://localhost:8000)
   * @param {Object} options - Configuration options
   * @param {number} options.maxRetries - Maximum number of retry attempts (default: 3)
   * @param {number} options.retryDelay - Initial retry delay in ms (default: 1000)
   * @param {number} options.timeout - Request timeout in ms (default: 30000)
   */
  constructor(baseUrl, options = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.maxRetries = options.maxRetries || 3;
    this.retryDelay = options.retryDelay || 1000;
    this.timeout = options.timeout || 30000;
  }

  /**
   * Make an HTTP request with retry logic
   * @private
   * @param {string} endpoint - API endpoint path
   * @param {Object} options - Fetch options
   * @param {number} retries - Number of retries remaining
   * @returns {Promise<any>} Response data
   */
  async _request(endpoint, options = {}, retries = this.maxRetries) {
    const url = `${this.baseUrl}${endpoint}`;
    
    // Add timeout to request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      // Handle non-OK responses
      if (!response.ok) {
        let errorData = {};
        let errorMessage = `HTTP ${response.status}`;
        
        try {
          errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (jsonError) {
          // If JSON parsing fails, use default error message
        }
        
        // Don't retry client errors (4xx)
        if (response.status >= 400 && response.status < 500) {
          throw new APIError(errorMessage, response.status, errorData);
        }
        
        // Retry server errors (5xx) if retries remain
        if (retries > 0) {
          const delay = this.retryDelay * Math.pow(2, this.maxRetries - retries);
          await this._sleep(delay);
          return this._request(endpoint, options, retries - 1);
        }
        
        throw new APIError(errorMessage, response.status, errorData);
      }

      // Parse JSON response
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      // Don't retry APIErrors (they're already handled above)
      if (error instanceof APIError) {
        throw error;
      }

      // Retry network errors if retries remain
      if (retries > 0) {
        const delay = this.retryDelay * Math.pow(2, this.maxRetries - retries);
        await this._sleep(delay);
        return this._request(endpoint, options, retries - 1);
      }

      // Wrap network errors
      throw new NetworkError(
        `Network request failed: ${error.message}`,
        error
      );
    }
  }

  /**
   * Sleep for a specified duration
   * @private
   * @param {number} ms - Milliseconds to sleep
   * @returns {Promise<void>}
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Health check endpoint
   * @returns {Promise<Object>} Health status
   */
  async healthCheck() {
    return this._request('/health');
  }

  /**
   * Login to GOG account
   * @param {string} username - GOG username
   * @param {string} password - GOG password
   * @param {string} twoFactorCode - Two-factor authentication code (optional)
   * @returns {Promise<Object>} Login response with success status
   */
  async login(username, password, twoFactorCode = null) {
    const body = {
      username,
      password,
    };
    
    if (twoFactorCode) {
      body.two_factor_code = twoFactorCode;
    }

    return this._request('/api/login', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  /**
   * Check authentication status
   * @returns {Promise<Object>} Authentication status
   */
  async checkAuth() {
    return this._request('/api/check-auth');
  }

  /**
   * Get game manifest with optional filters
   * @param {Object} filters - Filter options
   * @param {string[]} filters.osTypes - OS types to filter (e.g., ['windows', 'linux'])
   * @param {string[]} filters.languages - Languages to filter
   * @param {boolean} filters.updatesOnly - Show only games with updates
   * @param {string} filters.search - Search query
   * @returns {Promise<Object>} Manifest response with games list
   */
  async getManifest(filters = {}) {
    const params = new URLSearchParams();
    
    if (filters.osTypes && filters.osTypes.length > 0) {
      filters.osTypes.forEach(os => params.append('os_types', os));
    }
    
    if (filters.languages && filters.languages.length > 0) {
      filters.languages.forEach(lang => params.append('languages', lang));
    }
    
    if (filters.updatesOnly) {
      params.append('updates_only', 'true');
    }
    
    if (filters.search) {
      params.append('search', filters.search);
    }

    const queryString = params.toString();
    const endpoint = queryString ? `/api/manifest?${queryString}` : '/api/manifest';
    
    return this._request(endpoint);
  }

  /**
   * Update manifest from GOG
   * @param {Object} options - Update options
   * @param {string[]} options.osTypes - OS types to update
   * @param {string[]} options.languages - Languages to update
   * @param {boolean} options.skipKnownGames - Skip games already in manifest
   * @returns {Promise<Object>} Update response with statistics
   */
  async updateManifest(options = {}) {
    return this._request('/api/update', {
      method: 'POST',
      body: JSON.stringify({
        os_types: options.osTypes || [],
        languages: options.languages || [],
        skip_known_games: options.skipKnownGames || false,
      }),
    });
  }

  /**
   * Start download of selected games
   * @param {Object} request - Download request
   * @param {string[]} request.gameIds - Game IDs to download
   * @param {string} request.saveDir - Directory to save downloads
   * @param {string[]} request.osTypes - OS types to download
   * @param {string[]} request.languages - Languages to download
   * @param {boolean} request.skipExtras - Skip downloading extras
   * @param {boolean} request.skipGalaxy - Skip Galaxy installers
   * @param {boolean} request.skipStandalone - Skip standalone installers
   * @param {number} request.threads - Number of download threads
   * @returns {Promise<Object>} Download response with task ID
   */
  async startDownload(request) {
    return this._request('/api/download', {
      method: 'POST',
      body: JSON.stringify({
        game_ids: request.gameIds,
        save_dir: request.saveDir,
        os_types: request.osTypes || [],
        languages: request.languages || [],
        skip_extras: request.skipExtras || false,
        skip_galaxy: request.skipGalaxy || false,
        skip_standalone: request.skipStandalone || false,
        threads: request.threads || 4,
      }),
    });
  }

  /**
   * Get download progress via Server-Sent Events
   * @param {string} taskId - Download task ID
   * @returns {EventSource} EventSource for progress updates
   */
  getDownloadProgress(taskId) {
    const url = `${this.baseUrl}/api/download-progress/${taskId}`;
    return new EventSource(url);
  }

  /**
   * Add games to manifest without downloading
   * @param {Object} request - Add without download request
   * @param {string[]} request.gameIds - Game IDs to add
   * @param {string} request.saveDir - Directory where games would be saved
   * @returns {Promise<Object>} Response with added games count
   */
  async addWithoutDownload(request) {
    return this._request('/api/add_without_download', {
      method: 'POST',
      body: JSON.stringify({
        game_ids: request.gameIds,
        save_dir: request.saveDir,
      }),
    });
  }

  /**
   * Update the backend URL (useful if backend restarts on different port)
   * @param {string} newBaseUrl - New backend URL
   */
  updateBaseUrl(newBaseUrl) {
    this.baseUrl = newBaseUrl.replace(/\/$/, '');
  }
}

// Export for use in browser/renderer context
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { APIClient, APIError, NetworkError };
}
