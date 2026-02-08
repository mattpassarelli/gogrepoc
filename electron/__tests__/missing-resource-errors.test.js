/**
 * Unit tests for missing resource error handling
 * Tests error messages when backend executable or other resources are missing
 * 
 * Task 5.4: Write unit tests for missing resource errors
 * Requirements: 12.5
 */

const path = require('path');
const fs = require('fs');
const os = require('os');
const {
  getBackendExecutablePath,
  getResourcePath,
  verifyPathExists
} = require('../path-utils');

// Mock electron-log to avoid file system operations during tests
jest.mock('electron-log', () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  transports: {
    file: {
      getFile: () => ({ path: '/mock/log/path' })
    }
  }
}));

describe('Missing Resource Error Tests', () => {
  let originalEnv;
  let originalArgv;
  let originalResourcesPath;

  beforeEach(() => {
    // Save original values
    originalEnv = process.env.NODE_ENV;
    originalArgv = process.argv;
    originalResourcesPath = process.resourcesPath;
    
    // Clear mocks
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Restore original values
    process.env.NODE_ENV = originalEnv;
    process.argv = originalArgv;
    if (originalResourcesPath !== undefined) {
      process.resourcesPath = originalResourcesPath;
    } else {
      delete process.resourcesPath;
    }
  });

  describe('Backend Executable Missing Errors', () => {
    it('should provide clear error message when backend executable is missing', () => {
      // Set up production mode
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      // Create temp directory without backend executable
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        // Verify error message contains all required information
        expect(error.message).toContain('Backend executable not found');
        expect(error.message).toContain('Platform:');
        expect(error.message).toContain('Expected file:');
        expect(error.message).toContain('Resources path:');
        expect(error.message).toContain('reinstall');
        
        // Verify it includes the actual path that was checked
        expect(error.message).toContain(tempDir);
      } finally {
        // Cleanup
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should include platform-specific executable name in error message', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        // Verify platform-specific executable name is mentioned
        const expectedExeName = process.platform === 'win32' ? 
          'gogrepoc-backend.exe' : 'gogrepoc-backend';
        expect(error.message).toContain(expectedExeName);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should provide error when backend directory is missing', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      // Create temp directory but no backend subdirectory
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Backend executable not found');
        expect(error.message).toContain('backend');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should provide error when backend exists but is not executable on Unix', () => {
      // Skip this test on Windows
      if (process.platform === 'win32') {
        return;
      }

      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      const backendDir = path.join(tempDir, 'backend');
      fs.mkdirSync(backendDir, { recursive: true });
      
      // Create backend file but don't make it executable
      const exePath = path.join(backendDir, 'gogrepoc-backend');
      fs.writeFileSync(exePath, 'mock executable');
      fs.chmodSync(exePath, 0o644); // Read/write but not executable

      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('not executable');
        expect(error.message).toContain('permissions');
        expect(error.message).toContain(exePath);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should return null when resourcesPath is undefined (treated as development)', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      delete process.resourcesPath;

      // When resourcesPath is undefined, isDevelopmentMode() returns true
      // So the function returns null (development mode behavior)
      const result = getBackendExecutablePath();
      expect(result).toBe(null);
    });
  });

  describe('General Resource Missing Errors', () => {
    it('should provide clear error message when required resource is missing', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));

      try {
        getResourcePath('icons/missing-icon.png', { 
          required: true,
          devBasePath: tempDir 
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Required resource not found');
        expect(error.message).toContain('icons/missing-icon.png');
        expect(error.message).toContain('Expected location:');
        expect(error.message).toContain('Mode:');
        expect(error.message).toContain('development');
        expect(error.message).toContain('build');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should include full path in error message for missing resource', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      const resourcePath = 'config/settings.json';

      try {
        getResourcePath(resourcePath, { 
          required: true,
          devBasePath: tempDir 
        });
        fail('Should have thrown an error');
      } catch (error) {
        // Should include the full resolved path
        const expectedPath = path.join(tempDir, resourcePath);
        expect(error.message).toContain(expectedPath);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should indicate production mode in error message when in production', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getResourcePath('data/missing-data.json', { required: true });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Mode: production');
        expect(error.message).toContain('Required resource not found');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should not throw error for optional missing resources', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));

      try {
        // Should not throw for optional resources
        const result = getResourcePath('optional/missing.txt', { 
          required: false,
          devBasePath: tempDir 
        });
        
        // Should still return a path (even though file doesn't exist)
        expect(result).toBeDefined();
        expect(typeof result).toBe('string');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should use development path when resourcesPath is undefined', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      delete process.resourcesPath;

      // When resourcesPath is undefined, isDevelopmentMode() returns true
      // So it uses development mode path resolution
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      
      try {
        const result = getResourcePath('some/resource.txt', { 
          required: false,
          devBasePath: tempDir 
        });
        
        // Should use devBasePath since it's treated as development mode
        expect(result).toContain(tempDir);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });
  });

  describe('Path Verification Errors', () => {
    it('should provide clear error message when verifying non-existent path', () => {
      const nonExistentPath = path.join(os.tmpdir(), 'definitely-does-not-exist-' + Date.now(), 'file.txt');

      try {
        verifyPathExists(nonExistentPath, 'Test configuration file');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Test configuration file not found');
        expect(error.message).toContain(nonExistentPath);
        expect(error.message).toContain('ensure the file exists');
      }
    });

    it('should include custom description in error message', () => {
      const nonExistentPath = path.join(os.tmpdir(), 'missing-' + Date.now() + '.txt');
      const customDescription = 'Application database';

      try {
        verifyPathExists(nonExistentPath, customDescription);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain(customDescription);
        expect(error.message).toContain('not found');
      }
    });

    it('should provide error when file exists but is not readable', () => {
      // Skip this test on Windows (permissions work differently)
      if (process.platform === 'win32') {
        return;
      }

      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      const testFile = path.join(tempDir, 'unreadable.txt');
      
      // Create file and make it unreadable
      fs.writeFileSync(testFile, 'test content');
      fs.chmodSync(testFile, 0o000); // No permissions

      try {
        verifyPathExists(testFile, 'Test file');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('not readable');
        expect(error.message).toContain('permissions');
        expect(error.message).toContain(testFile);
      } finally {
        // Restore permissions before cleanup
        try {
          fs.chmodSync(testFile, 0o644);
        } catch (e) {
          // Ignore if already deleted
        }
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should use default description when none provided', () => {
      const nonExistentPath = path.join(os.tmpdir(), 'missing-' + Date.now() + '.txt');

      try {
        verifyPathExists(nonExistentPath);
        fail('Should have thrown an error');
      } catch (error) {
        // Should use default "Resource" description
        expect(error.message).toContain('Resource not found');
      }
    });
  });

  describe('Error Message Quality', () => {
    it('should provide actionable guidance in backend missing error', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        // Should suggest what user should do
        expect(error.message).toContain('reinstall');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should provide actionable guidance in resource missing error', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));

      try {
        getResourcePath('missing.txt', { 
          required: true,
          devBasePath: tempDir 
        });
        fail('Should have thrown an error');
      } catch (error) {
        // Should suggest what developer should do
        expect(error.message).toContain('build');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should provide actionable guidance in path verification error', () => {
      const nonExistentPath = path.join(os.tmpdir(), 'missing-' + Date.now() + '.txt');

      try {
        verifyPathExists(nonExistentPath);
        fail('Should have thrown an error');
      } catch (error) {
        // Should suggest checking file existence
        expect(error.message).toContain('ensure the file exists');
      }
    });

    it('should include all diagnostic information in backend error', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        // Should include multiple pieces of diagnostic info
        const diagnosticFields = [
          'Platform:',
          'Expected file:',
          'Resources path:'
        ];
        
        for (const field of diagnosticFields) {
          expect(error.message).toContain(field);
        }
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should format error messages with clear structure', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        // Error message should have newlines for readability
        expect(error.message).toContain('\n');
        
        // Should have multiple lines of information
        const lines = error.message.split('\n');
        expect(lines.length).toBeGreaterThan(1);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing backend directory gracefully', () => {
      process.env.NODE_ENV = 'production';
      process.argv = ['node', 'main.js'];
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      // Don't create backend directory
      process.resourcesPath = tempDir;

      try {
        getBackendExecutablePath();
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Backend executable not found');
        // Should still provide helpful error even though directory is missing
        expect(error.message).toContain('backend');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should handle deeply nested missing resources', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      const deepPath = 'level1/level2/level3/missing.txt';

      try {
        getResourcePath(deepPath, { 
          required: true,
          devBasePath: tempDir 
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Required resource not found');
        expect(error.message).toContain(deepPath);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should handle resources with special characters in path', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));
      const specialPath = 'files/my-file (1).txt';

      try {
        getResourcePath(specialPath, { 
          required: true,
          devBasePath: tempDir 
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('Required resource not found');
        expect(error.message).toContain(specialPath);
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it('should handle empty resource path', () => {
      process.env.NODE_ENV = 'development';
      
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'electron-test-'));

      try {
        // Empty path resolves to the base directory itself, which exists
        // So we test that it doesn't crash and returns a valid path
        const result = getResourcePath('', { 
          required: false,
          devBasePath: tempDir 
        });
        
        // Should return the base directory path
        expect(result).toBeDefined();
        expect(typeof result).toBe('string');
      } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    });
  });
});
