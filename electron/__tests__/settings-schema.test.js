/**
 * Unit tests for settings schema and validation
 * Task 12.1: Create settings schema and defaults
 * Requirements: 15.3, 15.4
 */

const {
  SETTINGS_SCHEMA,
  getDefaultSettings,
  validateSetting,
  validateAllSettings,
  validateWindowBounds,
  getStoreConfig
} = require('../settings-schema');

describe('Settings Schema', () => {
  describe('getDefaultSettings', () => {
    it('should return all default settings', () => {
      const defaults = getDefaultSettings();
      
      expect(defaults).toHaveProperty('lastDirectory', null);
      expect(defaults).toHaveProperty('defaultDownloadPath', null);
      expect(defaults).toHaveProperty('windowBounds');
      expect(defaults.windowBounds).toEqual({
        width: 1024,
        height: 768,
        x: undefined,
        y: undefined
      });
      expect(defaults).toHaveProperty('backendPort', null);
      expect(defaults).toHaveProperty('theme', 'system');
      expect(defaults).toHaveProperty('autoUpdate', true);
      expect(defaults).toHaveProperty('checkUpdateOnStartup', true);
    });
    
    it('should return a new object each time (not a reference)', () => {
      const defaults1 = getDefaultSettings();
      const defaults2 = getDefaultSettings();
      
      expect(defaults1).not.toBe(defaults2);
      expect(defaults1).toEqual(defaults2);
    });
  });
  
  describe('validateSetting', () => {
    describe('string settings', () => {
      it('should accept valid string values', () => {
        const result = validateSetting('lastDirectory', '/path/to/directory');
        expect(result).toBe('/path/to/directory');
      });
      
      it('should accept null for nullable string settings', () => {
        const result = validateSetting('lastDirectory', null);
        expect(result).toBe(null);
      });
      
      it('should return default for invalid type', () => {
        const result = validateSetting('lastDirectory', 123);
        expect(result).toBe(null);
      });
      
      it('should validate enum values', () => {
        expect(validateSetting('theme', 'light')).toBe('light');
        expect(validateSetting('theme', 'dark')).toBe('dark');
        expect(validateSetting('theme', 'system')).toBe('system');
        expect(validateSetting('theme', 'invalid')).toBe('system');
      });
    });
    
    describe('number settings', () => {
      it('should accept valid number values', () => {
        const result = validateSetting('backendPort', 8080);
        expect(result).toBe(8080);
      });
      
      it('should accept null for nullable number settings', () => {
        const result = validateSetting('backendPort', null);
        expect(result).toBe(null);
      });
      
      it('should return default for invalid type', () => {
        const result = validateSetting('backendPort', 'not a number');
        expect(result).toBe(null);
      });
      
      it('should return default for NaN', () => {
        const result = validateSetting('backendPort', NaN);
        expect(result).toBe(null);
      });
      
      it('should validate min range', () => {
        const result = validateSetting('backendPort', 7999);
        expect(result).toBe(null); // Below min of 8000
      });
      
      it('should validate max range', () => {
        const result = validateSetting('backendPort', 9001);
        expect(result).toBe(null); // Above max of 9000
      });
      
      it('should accept values within range', () => {
        expect(validateSetting('backendPort', 8000)).toBe(8000);
        expect(validateSetting('backendPort', 8500)).toBe(8500);
        expect(validateSetting('backendPort', 9000)).toBe(9000);
      });
    });
    
    describe('boolean settings', () => {
      it('should accept true', () => {
        const result = validateSetting('autoUpdate', true);
        expect(result).toBe(true);
      });
      
      it('should accept false', () => {
        const result = validateSetting('autoUpdate', false);
        expect(result).toBe(false);
      });
      
      it('should return default for invalid type', () => {
        const result = validateSetting('autoUpdate', 'yes');
        expect(result).toBe(true); // Default is true
      });
    });
    
    describe('object settings', () => {
      it('should validate windowBounds with valid values', () => {
        const bounds = {
          width: 1280,
          height: 800,
          x: 100,
          y: 100
        };
        
        const result = validateSetting('windowBounds', bounds);
        expect(result).toEqual(bounds);
      });
      
      it('should use defaults for invalid width', () => {
        const bounds = {
          width: 500, // Below min of 1024
          height: 800,
          x: 100,
          y: 100
        };
        
        const result = validateSetting('windowBounds', bounds);
        expect(result.width).toBe(1024);
        expect(result.height).toBe(800);
      });
      
      it('should use defaults for invalid height', () => {
        const bounds = {
          width: 1280,
          height: 500, // Below min of 768
          x: 100,
          y: 100
        };
        
        const result = validateSetting('windowBounds', bounds);
        expect(result.width).toBe(1280);
        expect(result.height).toBe(768);
      });
      
      it('should accept undefined x and y', () => {
        const bounds = {
          width: 1280,
          height: 800,
          x: undefined,
          y: undefined
        };
        
        const result = validateSetting('windowBounds', bounds);
        expect(result).toEqual(bounds);
      });
      
      it('should use defaults for NaN values', () => {
        const bounds = {
          width: NaN,
          height: NaN,
          x: NaN,
          y: NaN
        };
        
        const result = validateSetting('windowBounds', bounds);
        expect(result).toEqual({
          width: 1024,
          height: 768,
          x: undefined,
          y: undefined
        });
      });
      
      it('should use defaults for wrong types', () => {
        const bounds = {
          width: '1280',
          height: '800',
          x: '100',
          y: '100'
        };
        
        const result = validateSetting('windowBounds', bounds);
        expect(result).toEqual({
          width: 1024,
          height: 768,
          x: undefined,
          y: undefined
        });
      });
    });
    
    describe('unknown settings', () => {
      it('should return value as-is for unknown setting keys', () => {
        const result = validateSetting('unknownSetting', 'some value');
        expect(result).toBe('some value');
      });
    });
  });
  
  describe('validateAllSettings', () => {
    it('should validate all settings and return valid object', () => {
      const settings = {
        lastDirectory: '/path/to/dir',
        defaultDownloadPath: null,
        windowBounds: {
          width: 1280,
          height: 800,
          x: 100,
          y: 100
        },
        backendPort: 8080,
        theme: 'dark',
        autoUpdate: false,
        checkUpdateOnStartup: true
      };
      
      const result = validateAllSettings(settings);
      expect(result).toEqual(settings);
    });
    
    it('should use defaults for corrupted settings', () => {
      const corruptedSettings = {
        lastDirectory: 123, // Wrong type
        windowBounds: {
          width: 500, // Below min
          height: 'invalid', // Wrong type
          x: 100,
          y: 100
        },
        backendPort: 10000, // Above max
        theme: 'invalid', // Not in enum
        autoUpdate: 'yes' // Wrong type
      };
      
      const result = validateAllSettings(corruptedSettings);
      
      expect(result.lastDirectory).toBe(null);
      expect(result.windowBounds.width).toBe(1024);
      expect(result.windowBounds.height).toBe(768);
      expect(result.backendPort).toBe(null);
      expect(result.theme).toBe('system');
      expect(result.autoUpdate).toBe(true);
    });
    
    it('should return all defaults for null settings', () => {
      const result = validateAllSettings(null);
      expect(result).toEqual(getDefaultSettings());
    });
    
    it('should return all defaults for undefined settings', () => {
      const result = validateAllSettings(undefined);
      expect(result).toEqual(getDefaultSettings());
    });
    
    it('should return all defaults for non-object settings', () => {
      const result = validateAllSettings('not an object');
      expect(result).toEqual(getDefaultSettings());
    });
    
    it('should handle partially missing settings', () => {
      const partialSettings = {
        lastDirectory: '/path/to/dir',
        theme: 'light'
        // Other settings missing
      };
      
      const result = validateAllSettings(partialSettings);
      
      expect(result.lastDirectory).toBe('/path/to/dir');
      expect(result.theme).toBe('light');
      expect(result.defaultDownloadPath).toBe(null);
      expect(result.windowBounds).toEqual({
        width: 1024,
        height: 768,
        x: undefined,
        y: undefined
      });
      expect(result.backendPort).toBe(null);
      expect(result.autoUpdate).toBe(true);
      expect(result.checkUpdateOnStartup).toBe(true);
    });
  });
  
  describe('validateWindowBounds', () => {
    it('should validate bounds without screen module', () => {
      const bounds = {
        width: 1280,
        height: 800,
        x: 100,
        y: 100
      };
      
      const result = validateWindowBounds(bounds);
      expect(result).toEqual(bounds);
    });
    
    it('should return centered bounds when x or y is undefined', () => {
      const bounds = {
        width: 1280,
        height: 800,
        x: undefined,
        y: undefined
      };
      
      const result = validateWindowBounds(bounds);
      expect(result).toEqual({
        width: 1280,
        height: 800,
        x: undefined,
        y: undefined
      });
    });
    
    it('should validate bounds with screen module', () => {
      const mockScreen = {
        getAllDisplays: () => [{
          bounds: { x: 0, y: 0, width: 1920, height: 1080 }
        }]
      };
      
      const bounds = {
        width: 1280,
        height: 800,
        x: 100,
        y: 100
      };
      
      const result = validateWindowBounds(bounds, mockScreen);
      expect(result).toEqual(bounds);
    });
    
    it('should reset position when window would be off-screen', () => {
      const mockScreen = {
        getAllDisplays: () => [{
          bounds: { x: 0, y: 0, width: 1920, height: 1080 }
        }]
      };
      
      const bounds = {
        width: 1280,
        height: 800,
        x: 5000, // Way off screen
        y: 5000
      };
      
      const result = validateWindowBounds(bounds, mockScreen);
      expect(result).toEqual({
        width: 1280,
        height: 800,
        x: undefined,
        y: undefined
      });
    });
    
    it('should handle multiple displays', () => {
      const mockScreen = {
        getAllDisplays: () => [
          { bounds: { x: 0, y: 0, width: 1920, height: 1080 } },
          { bounds: { x: 1920, y: 0, width: 1920, height: 1080 } }
        ]
      };
      
      // Window on second display
      const bounds = {
        width: 1280,
        height: 800,
        x: 2000,
        y: 100
      };
      
      const result = validateWindowBounds(bounds, mockScreen);
      expect(result).toEqual(bounds);
    });
  });
  
  describe('getStoreConfig', () => {
    it('should return electron-store configuration', () => {
      const config = getStoreConfig();
      
      expect(config).toHaveProperty('defaults');
      expect(config.defaults).toEqual(getDefaultSettings());
    });
  });
  
  describe('SETTINGS_SCHEMA', () => {
    it('should define all required settings', () => {
      expect(SETTINGS_SCHEMA).toHaveProperty('lastDirectory');
      expect(SETTINGS_SCHEMA).toHaveProperty('defaultDownloadPath');
      expect(SETTINGS_SCHEMA).toHaveProperty('windowBounds');
      expect(SETTINGS_SCHEMA).toHaveProperty('backendPort');
      expect(SETTINGS_SCHEMA).toHaveProperty('theme');
      expect(SETTINGS_SCHEMA).toHaveProperty('autoUpdate');
      expect(SETTINGS_SCHEMA).toHaveProperty('checkUpdateOnStartup');
    });
    
    it('should have proper schema structure for each setting', () => {
      for (const [key, schema] of Object.entries(SETTINGS_SCHEMA)) {
        expect(schema).toHaveProperty('type');
        expect(schema).toHaveProperty('default');
        expect(schema).toHaveProperty('description');
      }
    });
  });
});
