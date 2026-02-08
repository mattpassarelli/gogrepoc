# Task 12.1 Implementation: Settings Schema and Defaults

## Overview

This document describes the implementation of Task 12.1: Create settings schema and defaults.

**Requirements Addressed:**
- 15.3: Store settings in platform-appropriate location
- 15.4: Use sensible defaults for corrupted/missing settings

## Implementation

### Files Created

1. **`electron/settings-schema.js`** - Settings schema module
   - Defines complete settings schema with types and defaults
   - Provides validation and sanitization functions
   - Handles corrupted settings by falling back to defaults
   - Exports configuration for electron-store

2. **`electron/__tests__/settings-schema.test.js`** - Comprehensive unit tests
   - Tests all validation functions
   - Tests corrupted settings handling
   - Tests window bounds validation
   - 37 test cases covering all edge cases

### Settings Schema

The settings schema defines all application settings with their types, defaults, and validation rules:

```javascript
{
  // Download settings
  lastDirectory: string | null,
  defaultDownloadPath: string | null,
  
  // Window state
  windowBounds: {
    width: number (min: 1024),
    height: number (min: 768),
    x: number | undefined,
    y: number | undefined
  },
  
  // Backend settings
  backendPort: number | null (range: 8000-9000),
  
  // UI preferences
  theme: 'light' | 'dark' | 'system',
  
  // Update settings
  autoUpdate: boolean,
  checkUpdateOnStartup: boolean
}
```

### Key Features

#### 1. Type Validation

Each setting has a defined type and the validation functions ensure values match:

```javascript
validateSetting('theme', 'dark')      // ✓ Returns 'dark'
validateSetting('theme', 'invalid')   // ✗ Returns 'system' (default)
validateSetting('autoUpdate', true)   // ✓ Returns true
validateSetting('autoUpdate', 'yes')  // ✗ Returns true (default)
```

#### 2. Range Validation

Number settings can have min/max constraints:

```javascript
validateSetting('backendPort', 8080)   // ✓ Returns 8080
validateSetting('backendPort', 7999)   // ✗ Returns null (below min)
validateSetting('backendPort', 9001)   // ✗ Returns null (above max)
```

#### 3. Enum Validation

String settings can be restricted to specific values:

```javascript
validateSetting('theme', 'light')    // ✓ Valid enum value
validateSetting('theme', 'dark')     // ✓ Valid enum value
validateSetting('theme', 'system')   // ✓ Valid enum value
validateSetting('theme', 'custom')   // ✗ Returns 'system' (default)
```

#### 4. Nested Object Validation

Complex settings like windowBounds have nested validation:

```javascript
validateSetting('windowBounds', {
  width: 1280,
  height: 800,
  x: 100,
  y: 100
})  // ✓ All fields valid

validateSetting('windowBounds', {
  width: 500,    // Below min of 1024
  height: 'bad', // Wrong type
  x: 100,
  y: 100
})  // ✗ Returns { width: 1024, height: 768, x: undefined, y: undefined }
```

#### 5. Corrupted Settings Handling

The `validateAllSettings()` function handles various corruption scenarios:

```javascript
// Null/undefined settings
validateAllSettings(null)       // Returns all defaults
validateAllSettings(undefined)  // Returns all defaults

// Partially missing settings
validateAllSettings({ theme: 'dark' })
// Returns: { theme: 'dark', ...other defaults }

// Invalid values
validateAllSettings({
  theme: 'invalid',
  backendPort: 10000,
  autoUpdate: 'yes'
})
// Returns all defaults for invalid values
```

#### 6. Window Bounds Screen Validation

The `validateWindowBounds()` function includes special logic to ensure windows are visible:

```javascript
// Window off-screen
validateWindowBounds({
  width: 1280,
  height: 800,
  x: 5000,  // Way off screen
  y: 5000
}, screen)
// Returns: { width: 1280, height: 800, x: undefined, y: undefined }
// Electron will center the window

// Window on second display
validateWindowBounds({
  width: 1280,
  height: 800,
  x: 2000,  // On second display
  y: 100
}, screen)
// Returns: { width: 1280, height: 800, x: 2000, y: 100 }
// Window is visible, position preserved
```

### Integration with main.js

The settings schema is integrated into main.js:

1. **Store Initialization**: Uses `getStoreConfig()` to initialize electron-store with defaults
2. **Window Bounds Validation**: Uses `validateWindowBounds()` with screen module
3. **Automatic Fallback**: electron-store automatically uses defaults for missing settings

```javascript
// Before (hardcoded defaults)
const store = new Store({
  defaults: {
    lastDirectory: null,
    windowBounds: { ... },
    // ... more defaults
  }
});

// After (using schema)
const { getStoreConfig, validateWindowBounds: validateWindowBoundsSchema } = require('./settings-schema');
const store = new Store(getStoreConfig());
```

### Platform-Appropriate Storage

electron-store automatically stores settings in platform-appropriate locations:

- **Windows**: `%APPDATA%\gogrepoc-desktop\config.json`
- **macOS**: `~/Library/Application Support/gogrepoc-desktop/config.json`
- **Linux**: `~/.config/gogrepoc-desktop/config.json`

This satisfies Requirement 15.3.

### Default Values

All settings have sensible defaults defined in the schema:

| Setting | Default | Rationale |
|---------|---------|-----------|
| `lastDirectory` | `null` | No directory selected yet |
| `defaultDownloadPath` | `null` | User hasn't set a default |
| `windowBounds.width` | `1024` | Minimum width per requirements |
| `windowBounds.height` | `768` | Minimum height per requirements |
| `windowBounds.x` | `undefined` | Let Electron center window |
| `windowBounds.y` | `undefined` | Let Electron center window |
| `backendPort` | `null` | Port assigned dynamically |
| `theme` | `'system'` | Follow OS theme |
| `autoUpdate` | `true` | Keep users up-to-date |
| `checkUpdateOnStartup` | `true` | Check for updates proactively |

This satisfies Requirement 15.4.

## Testing

### Unit Tests

37 comprehensive unit tests cover:

- ✅ Default settings generation
- ✅ String validation (including enums)
- ✅ Number validation (including ranges)
- ✅ Boolean validation
- ✅ Object validation (nested schemas)
- ✅ Corrupted settings handling
- ✅ Missing settings handling
- ✅ Window bounds screen validation
- ✅ Store configuration generation

All tests pass successfully.

### Test Coverage

```
Settings Schema
  getDefaultSettings
    ✓ should return all default settings
    ✓ should return a new object each time (not a reference)
  validateSetting
    string settings
      ✓ should accept valid string values
      ✓ should accept null for nullable string settings
      ✓ should return default for invalid type
      ✓ should validate enum values
    number settings
      ✓ should accept valid number values
      ✓ should accept null for nullable number settings
      ✓ should return default for invalid type
      ✓ should return default for NaN
      ✓ should validate min range
      ✓ should validate max range
      ✓ should accept values within range
    boolean settings
      ✓ should accept true
      ✓ should accept false
      ✓ should return default for invalid type
    object settings
      ✓ should validate windowBounds with valid values
      ✓ should use defaults for invalid width
      ✓ should use defaults for invalid height
      ✓ should accept undefined x and y
      ✓ should use defaults for NaN values
      ✓ should use defaults for wrong types
    unknown settings
      ✓ should return value as-is for unknown setting keys
  validateAllSettings
    ✓ should validate all settings and return valid object
    ✓ should use defaults for corrupted settings
    ✓ should return all defaults for null settings
    ✓ should return all defaults for undefined settings
    ✓ should return all defaults for non-object settings
    ✓ should handle partially missing settings
  validateWindowBounds
    ✓ should validate bounds without screen module
    ✓ should return centered bounds when x or y is undefined
    ✓ should validate bounds with screen module
    ✓ should reset position when window would be off-screen
    ✓ should handle multiple displays
  getStoreConfig
    ✓ should return electron-store configuration
  SETTINGS_SCHEMA
    ✓ should define all required settings
    ✓ should have proper schema structure for each setting

Test Suites: 1 passed, 1 total
Tests:       37 passed, 37 total
```

## Benefits

1. **Centralized Schema**: All settings defined in one place
2. **Type Safety**: Validation ensures type correctness
3. **Corruption Resilience**: Automatic fallback to defaults
4. **Maintainability**: Easy to add new settings
5. **Documentation**: Schema serves as documentation
6. **Testability**: Validation logic is fully testable

## Future Enhancements

Possible future improvements:

1. **Schema Versioning**: Handle settings migration between versions
2. **Custom Validators**: Support custom validation functions
3. **Settings UI**: Generate settings UI from schema
4. **Export/Import**: Allow users to export/import settings
5. **Settings Reset**: Add function to reset all settings to defaults

## Conclusion

Task 12.1 is complete. The settings schema provides:

- ✅ Formal interface definition for all settings
- ✅ Default values for all settings
- ✅ Corrupted settings handling with fallback to defaults
- ✅ Platform-appropriate storage location
- ✅ Comprehensive test coverage

The implementation satisfies Requirements 15.3 and 15.4.
