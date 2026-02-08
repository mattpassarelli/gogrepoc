/**
 * Tests for production build scripts
 * Task 16.2: Create production build scripts
 * Validates: Requirements 11.2
 */

const fs = require('fs');
const path = require('path');

describe('Production Build Scripts', () => {
  let packageJson;

  beforeAll(() => {
    const packageJsonPath = path.join(__dirname, '..', 'package.json');
    packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  });

  describe('Backend Build Script', () => {
    test('should have build:backend script', () => {
      expect(packageJson.scripts['build:backend']).toBeDefined();
    });

    test('build:backend should run PyInstaller', () => {
      const script = packageJson.scripts['build:backend'];
      expect(script).toContain('pyinstaller');
      expect(script).toContain('gogrepoc.spec');
    });

    test('build:backend should run in backend directory', () => {
      const script = packageJson.scripts['build:backend'];
      expect(script).toContain('cd ../backend');
    });
  });

  describe('Frontend Build Script', () => {
    test('should not have separate build:frontend script (handled by React build)', () => {
      // Frontend build is handled separately in the ui/ directory
      // This is intentional - the Electron build process expects the React app
      // to be pre-built in ui/build/
      expect(packageJson.scripts['build:frontend']).toBeUndefined();
    });
  });

  describe('Electron Build Script', () => {
    test('should have build:electron script', () => {
      expect(packageJson.scripts['build:electron']).toBeDefined();
    });

    test('build:electron should run electron-builder', () => {
      const script = packageJson.scripts['build:electron'];
      expect(script).toBe('electron-builder');
    });
  });

  describe('Main Build Script', () => {
    test('should have main build script', () => {
      expect(packageJson.scripts.build).toBeDefined();
    });

    test('build script should run all build steps in sequence', () => {
      const script = packageJson.scripts.build;
      expect(script).toContain('build:backend');
      expect(script).toContain('build:electron');
      expect(script).toMatch(/build:backend.*&&.*build:electron/);
    });

    test('build script should run backend build before electron build', () => {
      const script = packageJson.scripts.build;
      const backendIndex = script.indexOf('build:backend');
      const electronIndex = script.indexOf('build:electron');
      expect(backendIndex).toBeLessThan(electronIndex);
    });
  });

  describe('Platform-Specific Build Scripts', () => {
    test('should have build:win script', () => {
      expect(packageJson.scripts['build:win']).toBeDefined();
    });

    test('build:win should target Windows', () => {
      const script = packageJson.scripts['build:win'];
      expect(script).toContain('electron-builder');
      expect(script).toContain('--win');
    });

    test('should have build:mac script', () => {
      expect(packageJson.scripts['build:mac']).toBeDefined();
    });

    test('build:mac should target macOS', () => {
      const script = packageJson.scripts['build:mac'];
      expect(script).toContain('electron-builder');
      expect(script).toContain('--mac');
    });

    test('should have build:linux script', () => {
      expect(packageJson.scripts['build:linux']).toBeDefined();
    });

    test('build:linux should target Linux', () => {
      const script = packageJson.scripts['build:linux'];
      expect(script).toContain('electron-builder');
      expect(script).toContain('--linux');
    });
  });

  describe('Build Configuration', () => {
    test('should have electron-builder configuration', () => {
      expect(packageJson.build).toBeDefined();
    });

    test('should include backend in extraResources', () => {
      expect(packageJson.build.extraResources).toBeDefined();
      const backendResource = packageJson.build.extraResources.find(
        r => r.to === 'backend'
      );
      expect(backendResource).toBeDefined();
      expect(backendResource.from).toContain('backend/dist');
    });

    test('should have output directory configured', () => {
      expect(packageJson.build.directories).toBeDefined();
      expect(packageJson.build.directories.output).toBe('dist');
    });

    test('should have build resources directory configured', () => {
      expect(packageJson.build.directories.buildResources).toBe('build');
    });
  });

  describe('Build Script Validation', () => {
    test('all build scripts should be valid shell commands', () => {
      const buildScripts = [
        'build',
        'build:backend',
        'build:electron',
        'build:win',
        'build:mac',
        'build:linux'
      ];

      buildScripts.forEach(scriptName => {
        const script = packageJson.scripts[scriptName];
        expect(script).toBeDefined();
        expect(typeof script).toBe('string');
        expect(script.length).toBeGreaterThan(0);
      });
    });

    test('build scripts should not contain syntax errors', () => {
      const buildScripts = [
        'build',
        'build:backend',
        'build:electron',
        'build:win',
        'build:mac',
        'build:linux'
      ];

      buildScripts.forEach(scriptName => {
        const script = packageJson.scripts[scriptName];
        // Check for common syntax errors
        expect(script).not.toMatch(/&&\s*$/); // No trailing &&
        expect(script).not.toMatch(/^\s*&&/); // No leading &&
        expect(script).not.toMatch(/&&\s*&&/); // No double &&
      });
    });
  });

  describe('Build Dependencies', () => {
    test('should have electron-builder as dev dependency', () => {
      expect(packageJson.devDependencies['electron-builder']).toBeDefined();
    });

    test('should have electron as dev dependency', () => {
      expect(packageJson.devDependencies.electron).toBeDefined();
    });
  });

  describe('Build Script Documentation', () => {
    test('package.json should have description', () => {
      expect(packageJson.description).toBeDefined();
      expect(packageJson.description.length).toBeGreaterThan(0);
    });

    test('package.json should have version', () => {
      expect(packageJson.version).toBeDefined();
      expect(packageJson.version).toMatch(/^\d+\.\d+\.\d+$/);
    });

    test('package.json should have name', () => {
      expect(packageJson.name).toBeDefined();
      expect(packageJson.name).toBe('gogrepoc-desktop');
    });
  });
});
