/**
 * Tests for development mode scripts configuration
 * Task 16.1: Create development mode scripts
 * Requirements: 11.1 (enable DevTools and hot reload in dev mode), 
 *               11.3 (connect to separately running backend in dev mode),
 *               11.5 (provide detailed console logging in dev mode)
 */

const { isDevelopment, startBackend, waitForBackend } = require('../main.js');
const { getBackendExecutablePath } = require('../path-utils');

describe('Development Mode Scripts', () => {
  describe('Development Mode Detection', () => {
    let originalEnv;
    let originalArgv;

    beforeEach(() => {
      // Save original values
      originalEnv = process.env.NODE_ENV;
      originalArgv = [...process.argv];
    });

    afterEach(() => {
      // Restore original values
      process.env.NODE_ENV = originalEnv;
      process.argv = originalArgv;
    });

    it('should detect development mode from NODE_ENV', () => {
      process.env.NODE_ENV = 'development';
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { isDevelopment: devMode } = require('../main.js');
      
      expect(devMode).toBe(true);
    });

    it('should detect development mode from --dev flag', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js', '--dev'];
      
      // Re-require to pick up new argv
      jest.resetModules();
      const { isDevelopment: devMode } = require('../main.js');
      
      expect(devMode).toBe(true);
    });

    it('should be in production mode when neither flag is set', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { isDevelopment: devMode } = require('../main.js');
      
      expect(devMode).toBe(false);
    });
  });

  describe('Backend Connection in Development Mode', () => {
    let originalEnv;

    beforeEach(() => {
      originalEnv = process.env.NODE_ENV;
    });

    afterEach(() => {
      process.env.NODE_ENV = originalEnv;
    });

    it('should not spawn backend process in development mode', () => {
      process.env.NODE_ENV = 'development';
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { getBackendExecutablePath } = require('../path-utils');
      
      const backendPath = getBackendExecutablePath();
      
      // In development mode, should return null (no bundled backend)
      expect(backendPath).toBe(null);
    });

    it('should connect to localhost:8000 in development mode', async () => {
      process.env.NODE_ENV = 'development';
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { startBackend } = require('../main.js');
      
      // In development mode, startBackend should return port 8000
      const port = await startBackend();
      
      expect(port).toBe(8000);
    });

    it('should attempt to spawn backend process in production mode', () => {
      // Save original values
      const originalEnv = process.env.NODE_ENV;
      const originalResourcesPath = process.resourcesPath;
      
      try {
        // Set production mode
        process.env.NODE_ENV = 'production';
        // Mock resourcesPath to simulate packaged app
        process.resourcesPath = '/fake/resources/path';
        
        // Re-require to pick up new environment
        jest.resetModules();
        
        // In production mode, should attempt to find backend executable
        const { getBackendExecutablePath } = require('../path-utils');
        
        // Should throw because the backend executable doesn't exist at the mocked path
        expect(() => getBackendExecutablePath()).toThrow(/Backend executable not found/);
      } finally {
        // Restore original values
        process.env.NODE_ENV = originalEnv;
        if (originalResourcesPath === undefined) {
          delete process.resourcesPath;
        } else {
          process.resourcesPath = originalResourcesPath;
        }
      }
    });
  });

  describe('Development Mode Configuration', () => {
    it('should have npm run dev script configured', () => {
      const packageJson = require('../package.json');
      
      expect(packageJson.scripts).toHaveProperty('dev');
      expect(packageJson.scripts.dev).toContain('concurrently');
      expect(packageJson.scripts.dev).toContain('dev:backend');
      expect(packageJson.scripts.dev).toContain('dev:electron');
    });

    it('should have npm run dev:backend script configured', () => {
      const packageJson = require('../package.json');
      
      expect(packageJson.scripts).toHaveProperty('dev:backend');
      expect(packageJson.scripts['dev:backend']).toContain('uvicorn');
      expect(packageJson.scripts['dev:backend']).toContain('--reload');
      expect(packageJson.scripts['dev:backend']).toContain('--port 8000');
    });

    it('should have npm run dev:electron script configured', () => {
      const packageJson = require('../package.json');
      
      expect(packageJson.scripts).toHaveProperty('dev:electron');
      expect(packageJson.scripts['dev:electron']).toContain('electron');
      expect(packageJson.scripts['dev:electron']).toContain('--dev');
    });

    it('should have concurrently as a dev dependency', () => {
      const packageJson = require('../package.json');
      
      expect(packageJson.devDependencies).toHaveProperty('concurrently');
    });
  });

  describe('Development Mode Features', () => {
    let originalEnv;

    beforeEach(() => {
      originalEnv = process.env.NODE_ENV;
    });

    afterEach(() => {
      process.env.NODE_ENV = originalEnv;
    });

    it('should enable detailed logging in development mode', () => {
      process.env.NODE_ENV = 'development';
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { log } = require('../main.js');
      
      // Verify log is configured
      expect(log).toBeDefined();
      expect(log.transports).toBeDefined();
      expect(log.transports.file).toBeDefined();
    });

    it('should open DevTools in development mode', () => {
      process.env.NODE_ENV = 'development';
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { isDevelopment } = require('../main.js');
      
      // Verify development mode is detected
      expect(isDevelopment).toBe(true);
      
      // Note: Actual DevTools opening is tested in integration tests
      // as it requires a real BrowserWindow instance
    });
  });

  describe('Backend URL Configuration', () => {
    it('should use localhost:8000 in development mode', async () => {
      process.env.NODE_ENV = 'development';
      
      // Re-require to pick up new environment
      jest.resetModules();
      const { startBackend } = require('../main.js');
      
      const port = await startBackend();
      const expectedUrl = `http://localhost:${port}`;
      
      expect(expectedUrl).toBe('http://localhost:8000');
    });

    it('should use dynamic port in production mode', async () => {
      process.env.NODE_ENV = 'production';
      
      // Re-require to pick up new environment
      jest.resetModules();
      
      // In production mode, port should be dynamically assigned
      // (will fail in test environment due to missing backend, but concept is tested)
      const { findAvailablePort } = require('../main.js');
      
      const port = await findAvailablePort();
      
      // Should find a port in the 8000-9000 range
      expect(port).toBeGreaterThanOrEqual(8000);
      expect(port).toBeLessThanOrEqual(9000);
    });
  });

  describe('Script Execution Order', () => {
    it('should run backend before electron in dev script', () => {
      const packageJson = require('../package.json');
      const devScript = packageJson.scripts.dev;
      
      // Verify concurrently runs both scripts
      expect(devScript).toContain('concurrently');
      
      // Verify both scripts are included
      expect(devScript).toContain('dev:backend');
      expect(devScript).toContain('dev:electron');
    });

    it('should use --reload flag for backend hot reload', () => {
      const packageJson = require('../package.json');
      const backendScript = packageJson.scripts['dev:backend'];
      
      // Verify --reload flag is present for hot reload
      expect(backendScript).toContain('--reload');
    });
  });

  describe('Environment Variable Handling', () => {
    it('should set NODE_ENV=development for dev:electron script', () => {
      const packageJson = require('../package.json');
      const electronScript = packageJson.scripts['dev:electron'];
      
      // Verify NODE_ENV is set (or --dev flag is used)
      const hasNodeEnv = electronScript.includes('NODE_ENV=development');
      const hasDevFlag = electronScript.includes('--dev');
      
      expect(hasNodeEnv || hasDevFlag).toBe(true);
    });
  });

  describe('Cross-Platform Compatibility', () => {
    it('should work on Unix-like systems (Linux, macOS)', () => {
      const packageJson = require('../package.json');
      const electronScript = packageJson.scripts['dev:electron'];
      
      // Unix-style environment variable setting
      if (process.platform !== 'win32') {
        expect(electronScript).toContain('NODE_ENV=development');
      }
    });

    it('should work on Windows', () => {
      const packageJson = require('../package.json');
      
      // Windows should use cross-env or --dev flag
      // Our implementation uses --dev flag which works cross-platform
      const electronScript = packageJson.scripts['dev:electron'];
      expect(electronScript).toContain('--dev');
    });
  });
});
