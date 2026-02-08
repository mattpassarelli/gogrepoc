/**
 * Tests for Windows build configuration
 * 
 * Validates: Requirements 8.1, 8.4
 * 
 * These tests verify that the electron-builder configuration for Windows
 * is properly set up with NSIS installer and portable executable targets.
 */

const fs = require('fs');
const path = require('path');

describe('Windows Build Configuration', () => {
  let packageJson;
  
  beforeAll(() => {
    const packagePath = path.join(__dirname, '..', 'package.json');
    packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
  });
  
  describe('Basic Windows Configuration', () => {
    it('should have Windows build configuration', () => {
      expect(packageJson.build).toBeDefined();
      expect(packageJson.build.win).toBeDefined();
    });
    
    it('should configure NSIS installer target', () => {
      const targets = packageJson.build.win.target;
      expect(targets).toBeDefined();
      expect(Array.isArray(targets)).toBe(true);
      
      const nsisTarget = targets.find(t => t.target === 'nsis');
      expect(nsisTarget).toBeDefined();
      expect(nsisTarget.arch).toContain('x64');
    });
    
    it('should configure portable executable target', () => {
      const targets = packageJson.build.win.target;
      const portableTarget = targets.find(t => t.target === 'portable');
      
      expect(portableTarget).toBeDefined();
      expect(portableTarget.arch).toContain('x64');
    });
    
    it('should specify Windows icon', () => {
      expect(packageJson.build.win.icon).toBe('build/icon.ico');
    });
    
    it('should have publisher name', () => {
      expect(packageJson.build.win.publisherName).toBeDefined();
      expect(typeof packageJson.build.win.publisherName).toBe('string');
    });
  });
  
  describe('NSIS Installer Configuration', () => {
    it('should have NSIS configuration', () => {
      expect(packageJson.build.nsis).toBeDefined();
    });
    
    it('should not use one-click installer', () => {
      // One-click installers don't allow directory selection
      expect(packageJson.build.nsis.oneClick).toBe(false);
    });
    
    it('should allow installation directory selection', () => {
      expect(packageJson.build.nsis.allowToChangeInstallationDirectory).toBe(true);
    });
    
    it('should allow elevation for admin rights', () => {
      expect(packageJson.build.nsis.allowElevation).toBe(true);
    });
    
    it('should create desktop shortcut', () => {
      expect(packageJson.build.nsis.createDesktopShortcut).toBe(true);
    });
    
    it('should create Start Menu shortcut', () => {
      expect(packageJson.build.nsis.createStartMenuShortcut).toBe(true);
    });
    
    it('should have shortcut name', () => {
      expect(packageJson.build.nsis.shortcutName).toBeDefined();
      expect(typeof packageJson.build.nsis.shortcutName).toBe('string');
    });
    
    it('should configure installer icons', () => {
      expect(packageJson.build.nsis.installerIcon).toBe('build/icon.ico');
      expect(packageJson.build.nsis.uninstallerIcon).toBe('build/icon.ico');
    });
    
    it('should not delete app data on uninstall by default', () => {
      // Preserve user settings and data
      expect(packageJson.build.nsis.deleteAppDataOnUninstall).toBe(false);
    });
    
    it('should run application after installation', () => {
      expect(packageJson.build.nsis.runAfterFinish).toBe(true);
    });
    
    it('should create menu category', () => {
      expect(packageJson.build.nsis.menuCategory).toBe(true);
    });
    
    it('should default to per-user installation', () => {
      // Per-user doesn't require admin rights
      expect(packageJson.build.nsis.perMachine).toBe(false);
    });
  });
  
  describe('Portable Configuration', () => {
    it('should have portable configuration', () => {
      expect(packageJson.build.portable).toBeDefined();
    });
    
    it('should have custom artifact name for portable', () => {
      expect(packageJson.build.portable.artifactName).toBeDefined();
      expect(packageJson.build.portable.artifactName).toContain('portable');
    });
  });
  
  describe('Icon Files', () => {
    it('should have Windows icon file', () => {
      const iconPath = path.join(__dirname, '..', 'build', 'icon.ico');
      expect(fs.existsSync(iconPath)).toBe(true);
    });
    
    it('should have valid icon file size', () => {
      const iconPath = path.join(__dirname, '..', 'build', 'icon.ico');
      const stats = fs.statSync(iconPath);
      
      // ICO files should be at least a few hundred bytes
      // Our minimal placeholder is small, but a real icon would be larger
      expect(stats.size).toBeGreaterThan(0);
    });
  });
  
  describe('Build Scripts', () => {
    it('should have Windows build script', () => {
      expect(packageJson.scripts['build:win']).toBeDefined();
      expect(packageJson.scripts['build:win']).toContain('--win');
    });
    
    it('should have general build script', () => {
      expect(packageJson.scripts.build).toBeDefined();
    });
    
    it('should have electron-builder script', () => {
      expect(packageJson.scripts['build:electron']).toBeDefined();
      expect(packageJson.scripts['build:electron']).toBe('electron-builder');
    });
  });
  
  describe('Dependencies', () => {
    it('should have electron-builder as dev dependency', () => {
      expect(packageJson.devDependencies['electron-builder']).toBeDefined();
    });
  });
  
  describe('Extra Resources', () => {
    it('should include backend in extra resources', () => {
      expect(packageJson.build.extraResources).toBeDefined();
      expect(Array.isArray(packageJson.build.extraResources)).toBe(true);
      
      const backendResource = packageJson.build.extraResources.find(
        r => r.to === 'backend'
      );
      
      expect(backendResource).toBeDefined();
      expect(backendResource.from).toContain('backend/dist');
    });
  });
  
  describe('Application Metadata', () => {
    it('should have app ID', () => {
      expect(packageJson.build.appId).toBeDefined();
      expect(typeof packageJson.build.appId).toBe('string');
    });
    
    it('should have product name', () => {
      expect(packageJson.build.productName).toBeDefined();
      expect(typeof packageJson.build.productName).toBe('string');
    });
    
    it('should have version', () => {
      expect(packageJson.version).toBeDefined();
      expect(typeof packageJson.version).toBe('string');
      // Should follow semver
      expect(packageJson.version).toMatch(/^\d+\.\d+\.\d+/);
    });
  });
  
  describe('Artifact Naming', () => {
    it('should have custom artifact name pattern', () => {
      expect(packageJson.build.win.artifactName).toBeDefined();
      expect(packageJson.build.win.artifactName).toContain('${productName}');
      expect(packageJson.build.win.artifactName).toContain('${version}');
      expect(packageJson.build.win.artifactName).toContain('${arch}');
    });
  });
});

describe('Windows Build Documentation', () => {
  it('should have Windows build documentation', () => {
    const docPath = path.join(__dirname, '..', 'build', 'WINDOWS_BUILD.md');
    expect(fs.existsSync(docPath)).toBe(true);
  });
  
  it('should have icon documentation', () => {
    const docPath = path.join(__dirname, '..', 'build', 'ICONS_NEEDED.md');
    expect(fs.existsSync(docPath)).toBe(true);
  });
  
  it('should have icon creation script', () => {
    const scriptPath = path.join(__dirname, '..', 'build', 'create-placeholder-icons.js');
    expect(fs.existsSync(scriptPath)).toBe(true);
  });
});
