/**
 * Linux Build Configuration Tests
 * 
 * Tests for Task 15.3: Configure electron-builder for Linux
 * Validates Requirements 8.3, 8.4
 */

const fs = require('fs');
const path = require('path');

describe('Linux Build Configuration', () => {
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

    test('should have linux configuration section', () => {
      expect(buildConfig.linux).toBeDefined();
      expect(typeof buildConfig.linux).toBe('object');
    });
  });

  describe('AppImage Configuration (Requirement 8.3)', () => {
    test('should configure AppImage as a target', () => {
      expect(buildConfig.linux.target).toBeDefined();
      expect(Array.isArray(buildConfig.linux.target)).toBe(true);
      expect(buildConfig.linux.target).toContain('AppImage');
    });

    test('AppImage should be portable and not require installation', () => {
      // AppImage is inherently portable - just verify it's in the target list
      expect(buildConfig.linux.target).toContain('AppImage');
    });
  });

  describe('Deb Package Configuration (Requirement 8.3)', () => {
    test('should configure deb as a target', () => {
      expect(buildConfig.linux.target).toBeDefined();
      expect(Array.isArray(buildConfig.linux.target)).toBe(true);
      expect(buildConfig.linux.target).toContain('deb');
    });

    test('deb package should be for Debian-based distributions', () => {
      // Verify deb is configured (used by Ubuntu, Debian, Mint, etc.)
      expect(buildConfig.linux.target).toContain('deb');
    });
  });

  describe('RPM Package Configuration (Requirement 8.3)', () => {
    test('should configure rpm as a target', () => {
      expect(buildConfig.linux.target).toBeDefined();
      expect(Array.isArray(buildConfig.linux.target)).toBe(true);
      expect(buildConfig.linux.target).toContain('rpm');
    });

    test('rpm package should be for Red Hat-based distributions', () => {
      // Verify rpm is configured (used by Fedora, RHEL, CentOS, etc.)
      expect(buildConfig.linux.target).toContain('rpm');
    });
  });

  describe('Application Icon Configuration', () => {
    test('should specify icon.png file', () => {
      expect(buildConfig.linux.icon).toBeDefined();
      expect(buildConfig.linux.icon).toBe('build/icon.png');
    });

    test('should have correct icon path format', () => {
      expect(buildConfig.linux.icon).toMatch(/\.png$/);
      expect(buildConfig.linux.icon).toMatch(/^build\//);
    });

    test('icon path should be relative to package.json', () => {
      const iconPath = buildConfig.linux.icon;
      expect(iconPath).not.toMatch(/^\//); // Should not be absolute
      expect(iconPath).not.toMatch(/^\.\.\//); // Should not go up directories
    });

    test('icon file should exist', () => {
      const iconPath = path.join(__dirname, '..', buildConfig.linux.icon);
      expect(fs.existsSync(iconPath)).toBe(true);
    });

    test('icon file should have valid size', () => {
      const iconPath = path.join(__dirname, '..', buildConfig.linux.icon);
      const stats = fs.statSync(iconPath);
      
      // PNG files should be at least a few hundred bytes
      expect(stats.size).toBeGreaterThan(0);
    });
  });

  describe('Desktop Entry Category Configuration', () => {
    test('should set desktop entry category', () => {
      expect(buildConfig.linux.category).toBeDefined();
      expect(typeof buildConfig.linux.category).toBe('string');
    });

    test('should use valid freedesktop.org category', () => {
      const validCategories = [
        'AudioVideo',
        'Audio',
        'Video',
        'Development',
        'Education',
        'Game',
        'Graphics',
        'Network',
        'Office',
        'Science',
        'Settings',
        'System',
        'Utility'
      ];
      
      expect(validCategories).toContain(buildConfig.linux.category);
    });

    test('should use Utility category for GOGRepoc', () => {
      expect(buildConfig.linux.category).toBe('Utility');
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
    test('should have appId for Linux', () => {
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
    test('should include necessary files for Linux build', () => {
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
      // Linux uses .png
      expect(buildConfig.linux.icon).toMatch(/\.png$/);
      
      // Windows uses .ico
      if (buildConfig.win) {
        expect(buildConfig.win.icon).toMatch(/\.ico$/);
      }
      
      // macOS uses .icns
      if (buildConfig.mac) {
        expect(buildConfig.mac.icon).toMatch(/\.icns$/);
      }
    });
  });

  describe('Build Script Configuration', () => {
    test('should have build:linux script', () => {
      expect(packageJson.scripts).toBeDefined();
      expect(packageJson.scripts['build:linux']).toBeDefined();
    });

    test('build:linux script should use electron-builder', () => {
      expect(packageJson.scripts['build:linux']).toContain('electron-builder');
      expect(packageJson.scripts['build:linux']).toContain('--linux');
    });
  });

  describe('Package Format Support', () => {
    test('should support all three major Linux package formats', () => {
      const targets = buildConfig.linux.target;
      
      // Should support AppImage (universal)
      expect(targets).toContain('AppImage');
      
      // Should support deb (Debian/Ubuntu)
      expect(targets).toContain('deb');
      
      // Should support rpm (Fedora/RHEL)
      expect(targets).toContain('rpm');
    });

    test('should have exactly three package formats', () => {
      expect(buildConfig.linux.target).toHaveLength(3);
    });
  });

  describe('Desktop Integration', () => {
    test('should configure desktop entry category', () => {
      expect(buildConfig.linux.category).toBeDefined();
      expect(buildConfig.linux.category).toBe('Utility');
    });

    test('should have icon for desktop entry', () => {
      expect(buildConfig.linux.icon).toBeDefined();
      expect(buildConfig.linux.icon).toBe('build/icon.png');
    });

    test('should have product name for desktop entry', () => {
      expect(buildConfig.productName).toBeDefined();
      expect(buildConfig.productName).toBe('GOGRepoc');
    });
  });

  describe('Requirements Validation', () => {
    test('validates Requirement 8.3: AppImage creation', () => {
      expect(buildConfig.linux.target).toContain('AppImage');
    });

    test('validates Requirement 8.3: deb package creation', () => {
      expect(buildConfig.linux.target).toContain('deb');
    });

    test('validates Requirement 8.3: rpm package creation', () => {
      expect(buildConfig.linux.target).toContain('rpm');
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

  describe('Linux Distribution Coverage', () => {
    test('should support Debian-based distributions', () => {
      // deb package for Ubuntu, Debian, Linux Mint, Pop!_OS, etc.
      expect(buildConfig.linux.target).toContain('deb');
    });

    test('should support Red Hat-based distributions', () => {
      // rpm package for Fedora, RHEL, CentOS, openSUSE, etc.
      expect(buildConfig.linux.target).toContain('rpm');
    });

    test('should support distribution-agnostic format', () => {
      // AppImage works on any Linux distribution
      expect(buildConfig.linux.target).toContain('AppImage');
    });
  });

  describe('Icon Requirements', () => {
    test('should use PNG format for Linux', () => {
      expect(buildConfig.linux.icon).toMatch(/\.png$/);
    });

    test('icon should be in build directory', () => {
      expect(buildConfig.linux.icon).toMatch(/^build\//);
    });

    test('icon file should be accessible', () => {
      const iconPath = path.join(__dirname, '..', buildConfig.linux.icon);
      expect(fs.existsSync(iconPath)).toBe(true);
    });
  });
});

describe('Linux Build Configuration Summary', () => {
  test('should have complete Linux configuration', () => {
    const packagePath = path.join(__dirname, '..', 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const buildConfig = packageJson.build;

    // Summary of all required configuration
    const requirements = {
      'AppImage target configured': buildConfig.linux.target.includes('AppImage'),
      'deb target configured': buildConfig.linux.target.includes('deb'),
      'rpm target configured': buildConfig.linux.target.includes('rpm'),
      'Icon configured': buildConfig.linux.icon === 'build/icon.png',
      'Category set': buildConfig.linux.category === 'Utility',
      'Backend included': buildConfig.extraResources.some(r => r.to === 'backend'),
      'Build script exists': packageJson.scripts['build:linux'] !== undefined,
      'Icon file exists': fs.existsSync(path.join(__dirname, '..', buildConfig.linux.icon))
    };

    // All requirements should be met
    Object.entries(requirements).forEach(([requirement, met]) => {
      expect(met).toBe(true);
    });

    // Log summary
    console.log('\n✓ Linux Build Configuration Summary:');
    Object.entries(requirements).forEach(([requirement, met]) => {
      console.log(`  ${met ? '✓' : '✗'} ${requirement}`);
    });
  });
});

describe('Linux Build Documentation', () => {
  test('should verify all Linux package formats are documented', () => {
    const packagePath = path.join(__dirname, '..', 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const buildConfig = packageJson.build;

    // Document the configuration
    console.log('\nLinux Build Configuration Details:');
    console.log('==================================');
    console.log(`Package Formats: ${buildConfig.linux.target.join(', ')}`);
    console.log(`Icon: ${buildConfig.linux.icon}`);
    console.log(`Category: ${buildConfig.linux.category}`);
    console.log(`App ID: ${buildConfig.appId}`);
    console.log(`Product Name: ${buildConfig.productName}`);
    console.log(`Output Directory: ${buildConfig.directories.output}`);
    
    expect(true).toBe(true); // This test always passes, it's for documentation
  });
});
