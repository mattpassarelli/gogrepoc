/**
 * macOS Build Configuration Tests
 * 
 * Tests for Task 15.2: Configure electron-builder for macOS
 * Validates Requirements 8.2, 8.4
 */

const fs = require('fs');
const path = require('path');

describe('macOS Build Configuration', () => {
  let packageJson;
  let buildConfig;

  beforeAll(() => {
    const packagePath = path.join(__dirname, '..', 'package.json');
    packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    buildConfig = packageJson.build;
  });

  describe('Package.json Configuration', () => {
    test('should have build configuration', () => {
      expect(buildConfig).toBeDefined();
      expect(typeof buildConfig).toBe('object');
    });

    test('should have mac configuration section', () => {
      expect(buildConfig.mac).toBeDefined();
      expect(typeof buildConfig.mac).toBe('object');
    });
  });

  describe('DMG Configuration (Requirement 8.2)', () => {
    test('should configure DMG as a target', () => {
      expect(buildConfig.mac.target).toBeDefined();
      expect(Array.isArray(buildConfig.mac.target)).toBe(true);
      
      const dmgTarget = buildConfig.mac.target.find(t => t.target === 'dmg');
      expect(dmgTarget).toBeDefined();
    });

    test('should support both x64 and arm64 architectures for DMG', () => {
      const dmgTarget = buildConfig.mac.target.find(t => t.target === 'dmg');
      expect(dmgTarget.arch).toBeDefined();
      expect(Array.isArray(dmgTarget.arch)).toBe(true);
      expect(dmgTarget.arch).toContain('x64');
      expect(dmgTarget.arch).toContain('arm64');
    });
  });

  describe('.app Bundle Configuration (Requirement 8.2)', () => {
    test('should configure zip target for .app bundle distribution', () => {
      const zipTarget = buildConfig.mac.target.find(t => t.target === 'zip');
      expect(zipTarget).toBeDefined();
    });

    test('should support both x64 and arm64 architectures for zip', () => {
      const zipTarget = buildConfig.mac.target.find(t => t.target === 'zip');
      expect(zipTarget.arch).toBeDefined();
      expect(Array.isArray(zipTarget.arch)).toBe(true);
      expect(zipTarget.arch).toContain('x64');
      expect(zipTarget.arch).toContain('arm64');
    });
  });

  describe('Application Icon Configuration', () => {
    test('should specify icon.icns file', () => {
      expect(buildConfig.mac.icon).toBeDefined();
      expect(buildConfig.mac.icon).toBe('build/icon.icns');
    });

    test('should have correct icon path format', () => {
      expect(buildConfig.mac.icon).toMatch(/\.icns$/);
      expect(buildConfig.mac.icon).toMatch(/^build\//);
    });

    test('icon path should be relative to package.json', () => {
      const iconPath = buildConfig.mac.icon;
      expect(iconPath).not.toMatch(/^\//); // Should not be absolute
      expect(iconPath).not.toMatch(/^\.\.\//); // Should not go up directories
    });
  });

  describe('Application Category Configuration', () => {
    test('should set application category', () => {
      expect(buildConfig.mac.category).toBeDefined();
      expect(typeof buildConfig.mac.category).toBe('string');
    });

    test('should use valid macOS category', () => {
      const validCategories = [
        'public.app-category.business',
        'public.app-category.developer-tools',
        'public.app-category.education',
        'public.app-category.entertainment',
        'public.app-category.finance',
        'public.app-category.games',
        'public.app-category.graphics-design',
        'public.app-category.lifestyle',
        'public.app-category.medical',
        'public.app-category.music',
        'public.app-category.news',
        'public.app-category.photography',
        'public.app-category.productivity',
        'public.app-category.reference',
        'public.app-category.social-networking',
        'public.app-category.sports',
        'public.app-category.travel',
        'public.app-category.utilities',
        'public.app-category.video',
        'public.app-category.weather'
      ];
      
      expect(validCategories).toContain(buildConfig.mac.category);
    });

    test('should use utilities category for GOGRepoc', () => {
      expect(buildConfig.mac.category).toBe('public.app-category.utilities');
    });
  });

  describe('Code Signing Configuration', () => {
    test('should allow code signing to be configured', () => {
      // Code signing is optional and configured via environment variables
      // We just verify the configuration doesn't prevent it
      expect(buildConfig.mac).toBeDefined();
      
      // If code signing is configured, it should have valid properties
      if (buildConfig.mac.identity) {
        expect(typeof buildConfig.mac.identity).toBe('string');
      }
      
      if (buildConfig.mac.hardenedRuntime !== undefined) {
        expect(typeof buildConfig.mac.hardenedRuntime).toBe('boolean');
      }
    });

    test('should not require code signing for development builds', () => {
      // Verify that code signing is not mandatory in the config
      // (it can be disabled via CSC_IDENTITY_AUTO_DISCOVERY=false)
      expect(buildConfig.mac.identity).toBeUndefined();
    });
  });

  describe('Backend Bundle Integration (Requirement 8.4)', () => {
    test('should include extraResources configuration', () => {
      expect(buildConfig.extraResources).toBeDefined();
      expect(Array.isArray(buildConfig.extraResources)).toBe(true);
    });

    test('should include backend directory in extraResources', () => {
      const backendResource = buildConfig.extraResources.find(
        r => r.to === 'backend'
      );
      expect(backendResource).toBeDefined();
      expect(backendResource.from).toMatch(/backend\/dist/);
    });

    test('should include all backend files', () => {
      const backendResource = buildConfig.extraResources.find(
        r => r.to === 'backend'
      );
      expect(backendResource.filter).toBeDefined();
      expect(backendResource.filter).toContain('**/*');
    });
  });

  describe('Build Output Configuration', () => {
    test('should specify output directory', () => {
      expect(buildConfig.directories).toBeDefined();
      expect(buildConfig.directories.output).toBe('dist');
    });

    test('should specify build resources directory', () => {
      expect(buildConfig.directories.buildResources).toBe('build');
    });
  });

  describe('Application Metadata', () => {
    test('should have appId for macOS', () => {
      expect(buildConfig.appId).toBeDefined();
      expect(typeof buildConfig.appId).toBe('string');
      expect(buildConfig.appId).toMatch(/^[a-z0-9.]+$/);
    });

    test('should have product name', () => {
      expect(buildConfig.productName).toBeDefined();
      expect(typeof buildConfig.productName).toBe('string');
      expect(buildConfig.productName).toBe('GOGRepoc');
    });
  });

  describe('Files Configuration', () => {
    test('should include necessary files for macOS build', () => {
      expect(buildConfig.files).toBeDefined();
      expect(Array.isArray(buildConfig.files)).toBe(true);
      
      // Should include main process
      expect(buildConfig.files).toContain('main.js');
      
      // Should include preload script
      expect(buildConfig.files).toContain('preload.js');
      
      // Should include package.json
      expect(buildConfig.files).toContain('package.json');
    });
  });

  describe('Cross-Platform Consistency', () => {
    test('should have consistent configuration across platforms', () => {
      // All platforms should use the same appId
      expect(buildConfig.appId).toBeDefined();
      
      // All platforms should use the same productName
      expect(buildConfig.productName).toBeDefined();
      
      // All platforms should include the backend
      expect(buildConfig.extraResources).toBeDefined();
    });

    test('should have platform-specific icon formats', () => {
      // macOS uses .icns
      expect(buildConfig.mac.icon).toMatch(/\.icns$/);
      
      // Windows uses .ico
      if (buildConfig.win) {
        expect(buildConfig.win.icon).toMatch(/\.ico$/);
      }
      
      // Linux uses .png
      if (buildConfig.linux) {
        expect(buildConfig.linux.icon).toMatch(/\.png$/);
      }
    });
  });

  describe('Documentation', () => {
    test('should have macOS build documentation', () => {
      const docPath = path.join(__dirname, '..', 'build', 'MACOS_BUILD.md');
      expect(fs.existsSync(docPath)).toBe(true);
    });

    test('macOS documentation should contain key sections', () => {
      const docPath = path.join(__dirname, '..', 'build', 'MACOS_BUILD.md');
      const content = fs.readFileSync(docPath, 'utf8');
      
      expect(content).toContain('# macOS Build Configuration');
      expect(content).toContain('## DMG Configuration');
      expect(content).toContain('## Code Signing');
      expect(content).toContain('## Application Bundle Structure');
      expect(content).toContain('## Requirements Validation');
    });
  });

  describe('Build Script Configuration', () => {
    test('should have build:mac script', () => {
      expect(packageJson.scripts).toBeDefined();
      expect(packageJson.scripts['build:mac']).toBeDefined();
    });

    test('build:mac script should use electron-builder', () => {
      expect(packageJson.scripts['build:mac']).toContain('electron-builder');
      expect(packageJson.scripts['build:mac']).toContain('--mac');
    });
  });

  describe('Architecture Support', () => {
    test('should support Intel Macs (x64)', () => {
      const targets = buildConfig.mac.target;
      const hasX64 = targets.some(t => t.arch && t.arch.includes('x64'));
      expect(hasX64).toBe(true);
    });

    test('should support Apple Silicon Macs (arm64)', () => {
      const targets = buildConfig.mac.target;
      const hasArm64 = targets.some(t => t.arch && t.arch.includes('arm64'));
      expect(hasArm64).toBe(true);
    });

    test('should build for both architectures by default', () => {
      // Each target should support both architectures
      buildConfig.mac.target.forEach(target => {
        expect(target.arch).toContain('x64');
        expect(target.arch).toContain('arm64');
      });
    });
  });

  describe('Requirements Validation', () => {
    test('validates Requirement 8.2: DMG file creation', () => {
      const dmgTarget = buildConfig.mac.target.find(t => t.target === 'dmg');
      expect(dmgTarget).toBeDefined();
    });

    test('validates Requirement 8.2: .app bundle creation', () => {
      // The zip target creates a .app bundle
      const zipTarget = buildConfig.mac.target.find(t => t.target === 'zip');
      expect(zipTarget).toBeDefined();
    });

    test('validates Requirement 8.4: includes Electron app', () => {
      expect(buildConfig.files).toBeDefined();
      expect(buildConfig.files).toContain('main.js');
      expect(buildConfig.files).toContain('preload.js');
    });

    test('validates Requirement 8.4: includes PyInstaller bundle', () => {
      const backendResource = buildConfig.extraResources.find(
        r => r.to === 'backend'
      );
      expect(backendResource).toBeDefined();
    });
  });
});

describe('macOS Build Configuration Summary', () => {
  test('should have complete macOS configuration', () => {
    const packagePath = path.join(__dirname, '..', 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const buildConfig = packageJson.build;

    // Summary of all required configuration
    const requirements = {
      'DMG target configured': buildConfig.mac.target.some(t => t.target === 'dmg'),
      'ZIP target configured': buildConfig.mac.target.some(t => t.target === 'zip'),
      'x64 architecture supported': buildConfig.mac.target.some(t => t.arch?.includes('x64')),
      'arm64 architecture supported': buildConfig.mac.target.some(t => t.arch?.includes('arm64')),
      'Icon configured': buildConfig.mac.icon === 'build/icon.icns',
      'Category set': buildConfig.mac.category === 'public.app-category.utilities',
      'Backend included': buildConfig.extraResources.some(r => r.to === 'backend'),
      'Build script exists': packageJson.scripts['build:mac'] !== undefined
    };

    // All requirements should be met
    Object.entries(requirements).forEach(([requirement, met]) => {
      expect(met).toBe(true);
    });

    // Log summary
    console.log('\n✓ macOS Build Configuration Summary:');
    Object.entries(requirements).forEach(([requirement, met]) => {
      console.log(`  ${met ? '✓' : '✗'} ${requirement}`);
    });
  });
});
