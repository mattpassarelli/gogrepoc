/**
 * Unit tests for API Client
 * 
 * Tests the APIClient class including:
 * - Request handling
 * - Error handling
 * - Retry logic for transient failures
 * - All backend endpoint methods
 * 
 * Requirements: 7.1, 7.4, 7.5
 */

const { APIClient, APIError, NetworkError } = require('../renderer/api-client');

// Mock fetch globally
global.fetch = jest.fn();
global.EventSource = jest.fn();

describe('APIClient', () => {
  let client;
  const baseUrl = 'http://localhost:8000';

  beforeEach(() => {
    client = new APIClient(baseUrl, {
      maxRetries: 3,
      retryDelay: 100, // Shorter delay for tests
      timeout: 5000,
    });
    jest.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create client with base URL', () => {
      expect(client.baseUrl).toBe(baseUrl);
    });

    it('should remove trailing slash from base URL', () => {
      const clientWithSlash = new APIClient('http://localhost:8000/');
      expect(clientWithSlash.baseUrl).toBe(baseUrl);
    });

    it('should use default options when not provided', () => {
      const defaultClient = new APIClient(baseUrl);
      expect(defaultClient.maxRetries).toBe(3);
      expect(defaultClient.retryDelay).toBe(1000);
      expect(defaultClient.timeout).toBe(30000);
    });

    it('should accept custom options', () => {
      const customClient = new APIClient(baseUrl, {
        maxRetries: 5,
        retryDelay: 2000,
        timeout: 60000,
      });
      expect(customClient.maxRetries).toBe(5);
      expect(customClient.retryDelay).toBe(2000);
      expect(customClient.timeout).toBe(60000);
    });
  });

  describe('healthCheck', () => {
    it('should call health endpoint', async () => {
      const mockResponse = { status: 'ok' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.healthCheck();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/health',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('login', () => {
    it('should send login request with credentials', async () => {
      const mockResponse = { success: true, message: 'Logged in' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.login('user@example.com', 'password123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            username: 'user@example.com',
            password: 'password123',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should include two-factor code when provided', async () => {
      const mockResponse = { success: true };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.login('user@example.com', 'password123', '123456');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/login',
        expect.objectContaining({
          body: JSON.stringify({
            username: 'user@example.com',
            password: 'password123',
            two_factor_code: '123456',
          }),
        })
      );
    });
  });

  describe('checkAuth', () => {
    it('should check authentication status', async () => {
      const mockResponse = { authenticated: true };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.checkAuth();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/check-auth',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getManifest', () => {
    it('should get manifest without filters', async () => {
      const mockResponse = { games: [] };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.getManifest();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/manifest',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });

    it('should apply OS type filters', async () => {
      const mockResponse = { games: [] };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.getManifest({ osTypes: ['windows', 'linux'] });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/manifest?os_types=windows&os_types=linux',
        expect.any(Object)
      );
    });

    it('should apply language filters', async () => {
      const mockResponse = { games: [] };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.getManifest({ languages: ['en', 'de'] });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/manifest?languages=en&languages=de',
        expect.any(Object)
      );
    });

    it('should apply updates only filter', async () => {
      const mockResponse = { games: [] };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.getManifest({ updatesOnly: true });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/manifest?updates_only=true',
        expect.any(Object)
      );
    });

    it('should apply search filter', async () => {
      const mockResponse = { games: [] };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.getManifest({ search: 'witcher' });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/manifest?search=witcher',
        expect.any(Object)
      );
    });

    it('should combine multiple filters', async () => {
      const mockResponse = { games: [] };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.getManifest({
        osTypes: ['windows'],
        languages: ['en'],
        updatesOnly: true,
        search: 'game',
      });

      const url = global.fetch.mock.calls[0][0];
      expect(url).toContain('os_types=windows');
      expect(url).toContain('languages=en');
      expect(url).toContain('updates_only=true');
      expect(url).toContain('search=game');
    });
  });

  describe('updateManifest', () => {
    it('should send update request with options', async () => {
      const mockResponse = { updated: 10, added: 5 };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.updateManifest({
        osTypes: ['windows'],
        languages: ['en'],
        skipKnownGames: true,
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/update',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            os_types: ['windows'],
            languages: ['en'],
            skip_known_games: true,
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should use default options when not provided', async () => {
      const mockResponse = { updated: 0 };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.updateManifest();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/update',
        expect.objectContaining({
          body: JSON.stringify({
            os_types: [],
            languages: [],
            skip_known_games: false,
          }),
        })
      );
    });
  });

  describe('startDownload', () => {
    it('should send download request with all options', async () => {
      const mockResponse = { task_id: 'task-123' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const request = {
        gameIds: ['game1', 'game2'],
        saveDir: '/downloads',
        osTypes: ['windows'],
        languages: ['en'],
        skipExtras: true,
        skipGalaxy: false,
        skipStandalone: false,
        threads: 8,
      };

      const result = await client.startDownload(request);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/download',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            game_ids: ['game1', 'game2'],
            save_dir: '/downloads',
            os_types: ['windows'],
            languages: ['en'],
            skip_extras: true,
            skip_galaxy: false,
            skip_standalone: false,
            threads: 8,
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should use default options for optional fields', async () => {
      const mockResponse = { task_id: 'task-123' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await client.startDownload({
        gameIds: ['game1'],
        saveDir: '/downloads',
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/download',
        expect.objectContaining({
          body: JSON.stringify({
            game_ids: ['game1'],
            save_dir: '/downloads',
            os_types: [],
            languages: [],
            skip_extras: false,
            skip_galaxy: false,
            skip_standalone: false,
            threads: 4,
          }),
        })
      );
    });
  });

  describe('getDownloadProgress', () => {
    it('should create EventSource for progress updates', () => {
      const taskId = 'task-123';
      client.getDownloadProgress(taskId);

      expect(global.EventSource).toHaveBeenCalledWith(
        'http://localhost:8000/api/download-progress/task-123'
      );
    });
  });

  describe('addWithoutDownload', () => {
    it('should send add without download request', async () => {
      const mockResponse = { added: 5 };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.addWithoutDownload({
        gameIds: ['game1', 'game2'],
        saveDir: '/downloads',
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/add_without_download',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            game_ids: ['game1', 'game2'],
            save_dir: '/downloads',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('error handling', () => {
    it('should throw APIError for 4xx client errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Bad request' }),
      });

      const error = await client.healthCheck().catch(e => e);
      expect(error).toBeInstanceOf(APIError);
      expect(error.message).toBe('Bad request');
      expect(error.status).toBe(400);
    });

    it('should not retry 4xx errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      });

      await expect(client.healthCheck()).rejects.toThrow(APIError);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should retry 5xx server errors', async () => {
      // First two calls fail with 500, third succeeds
      global.fetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Server error' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Server error' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'ok' }),
        });

      const result = await client.healthCheck();

      expect(global.fetch).toHaveBeenCalledTimes(3);
      expect(result).toEqual({ status: 'ok' });
    });

    it('should throw APIError after max retries for 5xx errors', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ detail: 'Service unavailable' }),
      });

      await expect(client.healthCheck()).rejects.toThrow(APIError);
      expect(global.fetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
    });

    it('should retry network errors', async () => {
      // First two calls fail with network error, third succeeds
      global.fetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'ok' }),
        });

      const result = await client.healthCheck();

      expect(global.fetch).toHaveBeenCalledTimes(3);
      expect(result).toEqual({ status: 'ok' });
    });

    it('should throw NetworkError after max retries for network errors', async () => {
      global.fetch.mockRejectedValue(new Error('Connection refused'));

      await expect(client.healthCheck()).rejects.toThrow(NetworkError);
      expect(global.fetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
    });

    it('should use exponential backoff for retries', async () => {
      const startTime = Date.now();
      
      global.fetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'ok' }),
        });

      await client.healthCheck();

      const elapsed = Date.now() - startTime;
      // Should wait at least 100ms + 200ms = 300ms for two retries
      expect(elapsed).toBeGreaterThanOrEqual(300);
    });

    it('should handle malformed error responses', async () => {
      // Mock all 4 attempts (initial + 3 retries) to fail with malformed JSON
      for (let i = 0; i < 4; i++) {
        global.fetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => {
            throw new Error('Invalid JSON');
          },
        });
      }

      const error = await client.healthCheck().catch(e => e);
      expect(error).toBeInstanceOf(APIError);
      expect(error.message).toBe('HTTP 500');
      expect(error.status).toBe(500);
    });
  });

  describe('updateBaseUrl', () => {
    it('should update base URL', () => {
      const newUrl = 'http://localhost:9000';
      client.updateBaseUrl(newUrl);
      expect(client.baseUrl).toBe(newUrl);
    });

    it('should remove trailing slash from new URL', () => {
      client.updateBaseUrl('http://localhost:9000/');
      expect(client.baseUrl).toBe('http://localhost:9000');
    });
  });

  describe('timeout handling', () => {
    it('should abort request after timeout', async () => {
      // Mock fetch to simulate abort behavior
      global.fetch.mockImplementationOnce((url, options) => {
        return new Promise((resolve, reject) => {
          // Simulate a long-running request
          const timeout = setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({ status: 'ok' }),
            });
          }, 1000);
          
          // Listen for abort signal
          if (options.signal) {
            options.signal.addEventListener('abort', () => {
              clearTimeout(timeout);
              reject(new Error('The operation was aborted'));
            });
          }
        });
      });

      const shortTimeoutClient = new APIClient(baseUrl, {
        timeout: 100,
        maxRetries: 0,
      });

      await expect(shortTimeoutClient.healthCheck()).rejects.toThrow();
    }, 10000); // 10 second Jest timeout
  });
});
