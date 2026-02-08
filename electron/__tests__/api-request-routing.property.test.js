/**
 * Property-Based Tests for API Request Routing
 * Feature: electron-desktop-app
 * Property 5: API Request Routing
 * 
 * **Validates: Requirements 7.1**
 * 
 * Property: For any API request made by the renderer process, the request
 * should be sent to the backend URL with the dynamically assigned port.
 * 
 * This test verifies that:
 * 1. All API requests use the configured base URL
 * 2. The port from the base URL is correctly included in requests
 * 3. Endpoint paths are correctly appended to the base URL
 * 4. Query parameters are properly formatted and included
 */

const fc = require('fast-check');
const { APIClient } = require('../renderer/api-client');

// Mock fetch globally
global.fetch = jest.fn();
global.EventSource = jest.fn();

describe('Property 5: API Request Routing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Property: For any valid backend URL (with any port), all API requests
   * should be routed to that URL with the correct port.
   * 
   * **Validates: Requirements 7.1**
   */
  it('should route all API requests to the backend URL with dynamically assigned port', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary backend URLs with different ports
        fc.record({
          host: fc.constantFrom('localhost', '127.0.0.1'),
          port: fc.integer({ min: 8000, max: 9000 }),
          endpoint: fc.constantFrom(
            '/health',
            '/api/login',
            '/api/check-auth',
            '/api/manifest',
            '/api/update',
            '/api/download',
            '/api/add_without_download'
          ),
        }),
        async ({ host, port, endpoint }) => {
          // Clear mocks for this iteration
          jest.clearAllMocks();
          
          // Arrange: Create API client with the generated backend URL
          const baseUrl = `http://${host}:${port}`;
          const client = new APIClient(baseUrl, { maxRetries: 0 });

          // Mock successful response
          global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ success: true }),
          });

          // Act: Make a request to the endpoint
          try {
            await client._request(endpoint);
          } catch (error) {
            // Ignore errors, we're only checking the URL
          }

          // Assert: Verify the request was made to the correct URL with the correct port
          expect(global.fetch).toHaveBeenCalledTimes(1);
          const calledUrl = global.fetch.mock.calls[0][0];
          
          // Property 1: URL should start with the base URL
          expect(calledUrl).toContain(`http://${host}:${port}`);
          
          // Property 2: URL should include the endpoint path
          expect(calledUrl).toBe(`http://${host}:${port}${endpoint}`);
          
          // Property 3: Port should be exactly as specified (not default or changed)
          const urlObj = new URL(calledUrl);
          expect(urlObj.port).toBe(String(port));
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: For any API method call, the request should use the base URL
   * configured in the client, regardless of which method is called.
   * 
   * **Validates: Requirements 7.1**
   */
  it('should route requests from all API methods to the configured backend URL', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary backend URLs and method calls
        fc.record({
          host: fc.constantFrom('localhost', '127.0.0.1'),
          port: fc.integer({ min: 8000, max: 9000 }),
          method: fc.constantFrom(
            'healthCheck',
            'checkAuth',
            'getManifest',
            'updateManifest',
            'startDownload',
            'addWithoutDownload'
          ),
        }),
        async ({ host, port, method }) => {
          // Clear mocks for this iteration
          jest.clearAllMocks();
          
          // Arrange: Create API client with the generated backend URL
          const baseUrl = `http://${host}:${port}`;
          const client = new APIClient(baseUrl, { maxRetries: 0 });

          // Mock successful response
          global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ success: true }),
          });

          // Act: Call the API method
          try {
            switch (method) {
              case 'healthCheck':
                await client.healthCheck();
                break;
              case 'checkAuth':
                await client.checkAuth();
                break;
              case 'getManifest':
                await client.getManifest();
                break;
              case 'updateManifest':
                await client.updateManifest();
                break;
              case 'startDownload':
                await client.startDownload({
                  gameIds: ['test'],
                  saveDir: '/tmp',
                });
                break;
              case 'addWithoutDownload':
                await client.addWithoutDownload({
                  gameIds: ['test'],
                  saveDir: '/tmp',
                });
                break;
            }
          } catch (error) {
            // Ignore errors, we're only checking the URL
          }

          // Assert: Verify the request was made to the correct backend URL
          expect(global.fetch).toHaveBeenCalledTimes(1);
          const calledUrl = global.fetch.mock.calls[0][0];
          
          // Property: All requests should use the configured host and port
          expect(calledUrl).toContain(`http://${host}:${port}`);
          
          const urlObj = new URL(calledUrl);
          expect(urlObj.hostname).toBe(host);
          expect(urlObj.port).toBe(String(port));
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: When the backend URL is updated, all subsequent requests
   * should use the new URL with the new port.
   * 
   * **Validates: Requirements 7.1, 7.3**
   */
  it('should route requests to the new backend URL after updateBaseUrl is called', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create two different backend URLs
        fc.record({
          initialHost: fc.constantFrom('localhost', '127.0.0.1'),
          initialPort: fc.integer({ min: 8000, max: 8500 }),
          newHost: fc.constantFrom('localhost', '127.0.0.1'),
          newPort: fc.integer({ min: 8501, max: 9000 }),
        }),
        async ({ initialHost, initialPort, newHost, newPort }) => {
          // Clear mocks for this iteration
          jest.clearAllMocks();
          
          // Arrange: Create API client with initial URL
          const initialUrl = `http://${initialHost}:${initialPort}`;
          const client = new APIClient(initialUrl, { maxRetries: 0 });

          // Mock successful responses
          global.fetch.mockResolvedValue({
            ok: true,
            json: async () => ({ success: true }),
          });

          // Act: Make a request with initial URL
          try {
            await client.healthCheck();
          } catch (error) {
            // Ignore errors
          }

          // Assert: First request uses initial URL
          expect(global.fetch).toHaveBeenCalledTimes(1);
          const firstUrl = global.fetch.mock.calls[0][0];
          expect(firstUrl).toContain(`http://${initialHost}:${initialPort}`);

          // Act: Update base URL and make another request
          const newUrl = `http://${newHost}:${newPort}`;
          client.updateBaseUrl(newUrl);
          
          try {
            await client.healthCheck();
          } catch (error) {
            // Ignore errors
          }

          // Assert: Second request uses new URL
          expect(global.fetch).toHaveBeenCalledTimes(2);
          const secondUrl = global.fetch.mock.calls[1][0];
          expect(secondUrl).toContain(`http://${newHost}:${newPort}`);
          
          // Property: The new URL should have the new port
          const urlObj = new URL(secondUrl);
          expect(urlObj.port).toBe(String(newPort));
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: For any query parameters, the request URL should correctly
   * include them while maintaining the base URL and port.
   * 
   * **Validates: Requirements 7.1**
   */
  it('should route requests with query parameters to the correct backend URL', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create backend URLs with various query parameters
        fc.record({
          host: fc.constantFrom('localhost', '127.0.0.1'),
          port: fc.integer({ min: 8000, max: 9000 }),
          osTypes: fc.array(
            fc.constantFrom('windows', 'linux', 'mac'),
            { minLength: 0, maxLength: 3 }
          ),
          languages: fc.array(
            fc.constantFrom('en', 'de', 'fr', 'es'),
            { minLength: 0, maxLength: 4 }
          ),
          search: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: null }),
        }),
        async ({ host, port, osTypes, languages, search }) => {
          // Clear mocks for this iteration
          jest.clearAllMocks();
          
          // Arrange: Create API client with the generated backend URL
          const baseUrl = `http://${host}:${port}`;
          const client = new APIClient(baseUrl, { maxRetries: 0 });

          // Mock successful response
          global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ games: [] }),
          });

          // Act: Make a request with query parameters
          try {
            await client.getManifest({
              osTypes: osTypes.length > 0 ? osTypes : undefined,
              languages: languages.length > 0 ? languages : undefined,
              search: search || undefined,
            });
          } catch (error) {
            // Ignore errors
          }

          // Assert: Verify the request was made to the correct URL
          expect(global.fetch).toHaveBeenCalledTimes(1);
          const calledUrl = global.fetch.mock.calls[0][0];
          
          // Property 1: URL should start with the base URL and port
          const urlObj = new URL(calledUrl);
          expect(urlObj.protocol).toBe('http:');
          expect(urlObj.hostname).toBe(host);
          expect(urlObj.port).toBe(String(port));
          
          // Property 2: URL should include the correct endpoint
          expect(urlObj.pathname).toBe('/api/manifest');
          
          // Property 3: Query parameters should be present if provided
          if (osTypes.length > 0) {
            const osParams = urlObj.searchParams.getAll('os_types');
            expect(osParams.length).toBeGreaterThan(0);
          }
          
          if (languages.length > 0) {
            const langParams = urlObj.searchParams.getAll('languages');
            expect(langParams.length).toBeGreaterThan(0);
          }
          
          if (search) {
            expect(urlObj.searchParams.get('search')).toBe(search);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: For any POST request with a body, the request should be sent
   * to the correct backend URL with the correct port.
   * 
   * **Validates: Requirements 7.1**
   */
  it('should route POST requests with request bodies to the correct backend URL', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create backend URLs and POST request data
        fc.record({
          host: fc.constantFrom('localhost', '127.0.0.1'),
          port: fc.integer({ min: 8000, max: 9000 }),
          gameIds: fc.array(fc.string({ minLength: 1, maxLength: 10 }), {
            minLength: 1,
            maxLength: 5,
          }),
          saveDir: fc.string({ minLength: 1, maxLength: 50 }),
        }),
        async ({ host, port, gameIds, saveDir }) => {
          // Clear mocks for this iteration
          jest.clearAllMocks();
          
          // Arrange: Create API client with the generated backend URL
          const baseUrl = `http://${host}:${port}`;
          const client = new APIClient(baseUrl, { maxRetries: 0 });

          // Mock successful response
          global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ task_id: 'test-task' }),
          });

          // Act: Make a POST request
          try {
            await client.startDownload({
              gameIds,
              saveDir,
            });
          } catch (error) {
            // Ignore errors
          }

          // Assert: Verify the request was made to the correct URL
          expect(global.fetch).toHaveBeenCalledTimes(1);
          const [calledUrl, options] = global.fetch.mock.calls[0];
          
          // Property 1: URL should use the correct host and port
          const urlObj = new URL(calledUrl);
          expect(urlObj.hostname).toBe(host);
          expect(urlObj.port).toBe(String(port));
          
          // Property 2: URL should include the correct endpoint
          expect(urlObj.pathname).toBe('/api/download');
          
          // Property 3: Request should be POST method
          expect(options.method).toBe('POST');
          
          // Property 4: Request body should be present
          expect(options.body).toBeDefined();
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: Trailing slashes in the base URL should not affect routing.
   * All requests should be routed correctly regardless of trailing slash.
   * 
   * **Validates: Requirements 7.1**
   */
  it('should route requests correctly regardless of trailing slash in base URL', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create backend URLs with and without trailing slashes
        fc.record({
          host: fc.constantFrom('localhost', '127.0.0.1'),
          port: fc.integer({ min: 8000, max: 9000 }),
          hasTrailingSlash: fc.boolean(),
          endpoint: fc.constantFrom(
            '/health',
            '/api/login',
            '/api/manifest'
          ),
        }),
        async ({ host, port, hasTrailingSlash, endpoint }) => {
          // Clear mocks for this iteration
          jest.clearAllMocks();
          
          // Arrange: Create API client with or without trailing slash
          const baseUrl = hasTrailingSlash
            ? `http://${host}:${port}/`
            : `http://${host}:${port}`;
          const client = new APIClient(baseUrl, { maxRetries: 0 });

          // Mock successful response
          global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ success: true }),
          });

          // Act: Make a request
          try {
            await client._request(endpoint);
          } catch (error) {
            // Ignore errors
          }

          // Assert: Verify the request URL is correctly formed
          expect(global.fetch).toHaveBeenCalledTimes(1);
          const calledUrl = global.fetch.mock.calls[0][0];
          
          // Property 1: URL should not have double slashes (except in protocol)
          const urlWithoutProtocol = calledUrl.replace('http://', '');
          expect(urlWithoutProtocol).not.toContain('//');
          
          // Property 2: URL should have the correct structure
          expect(calledUrl).toBe(`http://${host}:${port}${endpoint}`);
          
          // Property 3: Port should be correct
          const urlObj = new URL(calledUrl);
          expect(urlObj.port).toBe(String(port));
        }
      ),
      { numRuns: 100 }
    );
  });
});
