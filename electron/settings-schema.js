/**
 * Settings Schema and Defaults
 * Task 12.1: Create settings schema and defaults
 * Requirements: 15.3 (store settings in platform-appropriate location), 15.4 (use sensible defaults for corrupted/missing settings)
 * 
 * This module defines the complete settings schema for the GOGRepoc Electron application,
 * provides default values for all settings, and includes validation/sanitization functions
 * to handle corrupted settings by falling back to defaults.
 */

/**
 * Settings Schema Definition
 * 
 * This schema defines all application settings with their types and default values.
 * Settings are persisted using electron-store, which automatically stores them in
 * platform-appropriate locations:
 * - Windows: %APPDATA%\gogrepoc-desktop\config.json
 * - macOS: ~/Library/Application Support/gogrepoc-desktop/config.json
 * - Linux: ~/.config/gogrepoc-desktop/config.json
 */
const SETTINGS_SCHEMA = {
  // Download settings
  lastDirectory: {
    type: 'string',
    nullable: true,
    default: null,
    description: 'Last selected download directory path'
  },
  
  defaultDownloadPath: {
    type: 'string',
    nullable: true,
    default: null,
    description: 'Default download directory path (if set by user)'
  },
  
  // Window state
  windowBounds: {
    type: 'object',
    default: {
      width: 1024,
      height: 768,
      x: undefined,
      y: undefined
    },
    description: 'Window size and position',
    schema: {
      width: { type: 'number', min: 1024, default: 1024 },
      height: { type: 'number', min: 768, default: 768 },
      x: { type: 'number', nullable: true, default: undefined },
      y: { type: 'number', nullable: true, default: undefined }
    }
  },
  
  // Backend settings
  backendPort: {
    type: 'number',
    nullable: true,
    default: null,
    min: 8000,
    max: 9000,
    description: 'Last used backend port (for informational purposes)'
  },
  
  // UI preferences
  theme: {
    type: 'string',
    default: 'system',
    enum: ['light', 'dark', 'system'],
    description: 'UI theme preference'
  },
  
  // Update settings
  autoUpdate: {
    type: 'boolean',
    default: true,
    description: 'Enable automatic updates'
  },
  
  checkUpdateOnStartup: {
    type: 'boolean',
    default: true,
    description: 'Check for updates when application starts'
  }
};

/**
 * Get default values for all settings
 * @returns {Object} Default settings object
 */
function getDefaultSettings() {
  const defaults = {};
  
  for (const [key, schema] of Object.entries(SETTINGS_SCHEMA)) {
    defaults[key] = schema.default;
  }
  
  return defaults;
}

/**
 * Validate and sanitize a setting value according to its schema
 * Falls back to default value if validation fails
 * 
 * @param {string} key - Setting key
 * @param {*} value - Setting value to validate
 * @returns {*} Validated value or default if invalid
 */
function validateSetting(key, value) {
  const schema = SETTINGS_SCHEMA[key];
  
  if (!schema) {
    // Unknown setting key, return value as-is
    return value;
  }
  
  // Handle null values
  if (value === null || value === undefined) {
    if (schema.nullable) {
      return value;
    }
    return schema.default;
  }
  
  // Type validation
  const actualType = Array.isArray(value) ? 'array' : typeof value;
  if (actualType !== schema.type) {
    return schema.default;
  }
  
  // Type-specific validation
  switch (schema.type) {
    case 'string':
      // Enum validation
      if (schema.enum && !schema.enum.includes(value)) {
        return schema.default;
      }
      return value;
      
    case 'number':
      // NaN check
      if (isNaN(value)) {
        return schema.default;
      }
      
      // Range validation
      if (schema.min !== undefined && value < schema.min) {
        return schema.default;
      }
      if (schema.max !== undefined && value > schema.max) {
        return schema.default;
      }
      return value;
      
    case 'boolean':
      return value;
      
    case 'object':
      // Validate nested object schema
      if (schema.schema) {
        return validateObjectSetting(value, schema);
      }
      return value;
      
    default:
      return value;
  }
}

/**
 * Validate and sanitize an object setting with nested schema
 * 
 * @param {Object} value - Object value to validate
 * @param {Object} schema - Schema definition for the object
 * @returns {Object} Validated object with defaults for invalid fields
 */
function validateObjectSetting(value, schema) {
  const validated = {};
  
  for (const [fieldKey, fieldSchema] of Object.entries(schema.schema)) {
    const fieldValue = value[fieldKey];
    
    // Handle null/undefined
    if (fieldValue === null || fieldValue === undefined) {
      if (fieldSchema.nullable) {
        validated[fieldKey] = fieldValue;
      } else {
        validated[fieldKey] = fieldSchema.default;
      }
      continue;
    }
    
    // Type validation
    const actualType = typeof fieldValue;
    if (actualType !== fieldSchema.type) {
      validated[fieldKey] = fieldSchema.default;
      continue;
    }
    
    // Number-specific validation
    if (fieldSchema.type === 'number') {
      if (isNaN(fieldValue)) {
        validated[fieldKey] = fieldSchema.default;
        continue;
      }
      
      if (fieldSchema.min !== undefined && fieldValue < fieldSchema.min) {
        validated[fieldKey] = fieldSchema.default;
        continue;
      }
      
      if (fieldSchema.max !== undefined && fieldValue > fieldSchema.max) {
        validated[fieldKey] = fieldSchema.default;
        continue;
      }
    }
    
    validated[fieldKey] = fieldValue;
  }
  
  return validated;
}

/**
 * Validate and sanitize all settings
 * Handles corrupted settings by falling back to defaults
 * 
 * @param {Object} settings - Settings object to validate
 * @returns {Object} Validated settings with defaults for invalid values
 */
function validateAllSettings(settings) {
  if (!settings || typeof settings !== 'object') {
    return getDefaultSettings();
  }
  
  const validated = {};
  
  for (const key of Object.keys(SETTINGS_SCHEMA)) {
    // If setting is missing from input, use default
    if (!(key in settings)) {
      validated[key] = SETTINGS_SCHEMA[key].default;
    } else {
      validated[key] = validateSetting(key, settings[key]);
    }
  }
  
  return validated;
}

/**
 * Get electron-store configuration with schema and defaults
 * This configuration should be passed to the Store constructor
 * 
 * @returns {Object} electron-store configuration
 */
function getStoreConfig() {
  return {
    defaults: getDefaultSettings(),
    // electron-store will automatically use platform-appropriate location
    // No need to specify 'cwd' or 'configName' unless customization is needed
  };
}

/**
 * Validate window bounds to ensure window is visible on screen
 * This is a specialized validation for windowBounds that considers screen geometry
 * 
 * @param {Object} bounds - Window bounds to validate
 * @param {Object} screen - Electron screen module (optional, for testing)
 * @returns {Object} Validated bounds
 */
function validateWindowBounds(bounds, screen = null) {
  // Use defaults if bounds are invalid
  const defaults = SETTINGS_SCHEMA.windowBounds.default;
  
  // Basic validation
  const validated = validateSetting('windowBounds', bounds);
  
  // If screen module not provided, return basic validation
  if (!screen) {
    return validated;
  }
  
  // If x or y are undefined, let Electron center the window
  if (validated.x === undefined || validated.y === undefined) {
    return {
      width: validated.width,
      height: validated.height,
      x: undefined,
      y: undefined
    };
  }
  
  // Check if window would be visible on any display
  const displays = screen.getAllDisplays();
  let isVisible = false;
  
  for (const display of displays) {
    const { x, y, width, height } = display.bounds;
    
    // Check if at least part of the window would be visible on this display
    // Window is visible if its center point is within the display bounds
    const windowCenterX = validated.x + validated.width / 2;
    const windowCenterY = validated.y + validated.height / 2;
    
    if (windowCenterX >= x && windowCenterX < x + width &&
        windowCenterY >= y && windowCenterY < y + height) {
      isVisible = true;
      break;
    }
  }
  
  if (!isVisible) {
    // Window would be off-screen, reset position to center
    return {
      width: validated.width,
      height: validated.height,
      x: undefined,
      y: undefined
    };
  }
  
  return validated;
}

module.exports = {
  SETTINGS_SCHEMA,
  getDefaultSettings,
  validateSetting,
  validateAllSettings,
  validateWindowBounds,
  getStoreConfig
};
