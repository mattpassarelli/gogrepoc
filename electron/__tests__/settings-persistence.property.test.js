/**
 * Property-Based Test: Settings Persistence
 * Task 12.3: Write property test for settings persistence
 * 
 * Property 12: Settings Persistence
 * **Validates: Requirements 15.1**
 * 
 * For any user setting (download directory, window bounds, preferences),
 * when the setting is changed and the app is restarted, the setting should
 * be restored to the saved value.
 * 
 * This test verifies that:
 * 1. Any valid setting value can be saved
 * 2. The saved value persists across app restarts (store instances)
 * 3. The retrieved value matches the saved value exactly
 */

const fc = require('fast-check');
const Store = require('electron-store');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { getStoreConfig } = require('../settings-schema');

describe('Property 12: Settings Persistence', () => {
  // Create a temporary directory for test stores
  const testStoreDir = path.join(os.tmpdir(), 'gogrepoc-test-stores');
  
  beforeAll(() => {
    // Ensure test directory exists
    if (!fs.existsSync(testStoreDir)) {
      fs.mkdirSync(testStoreDir, { recursive: true });
    }
  });
  
  afterAll(() => {
    // Clean up test directory
    if (fs.existsSync(testStoreDir)) {
      fs.rmSync(testStoreDir, { recursive: true, force: true });
    }
  });
  
  /**
   * Generator for valid setting keys
   */
  const settingKeyArb = fc.constantFrom(
    'lastDirectory',
    'defaultDownloadPath',
    'backendPort',
    'theme',
    'autoUpdate',
    'checkUpdateOnStartup'
  );
  
  /**
   * Generator for valid setting values based on key
   */
  const settingValueArb = (key) => {
    switch (key) {
      case 'lastDirectory':
      case 'defaultDownloadPath':
        return fc.oneof(
          fc.constant(null),
          fc.string({ minLength: 1, maxLength: 100 }).map(s => `/path/to/${s}`)
        );
      
      case 'backendPort':
        return fc.oneof(
          fc.constant(null),
          fc.integer({ min: 8000, max: 9000 })
        );
      
      case 'theme':
        return fc.constantFrom('light', 'dark', 'system');
      
      case 'autoUpdate':
      case 'checkUpdateOnStartup':
        return fc.boolean();
      
      default:
        return fc.constant(null);
    }
  };
  
  /**
   * Generator for window bounds
   */
  const windowBoundsArb = fc.record({
    width: fc.integer({ min: 1024, max: 3840 }),
    height: fc.integer({ min: 768, max: 2160 }),
    x: fc.oneof(
      fc.constant(undefined),
      fc.integer({ min: -1000, max: 5000 })
    ),
    y: fc.oneof(
      fc.constant(undefined),
      fc.integer({ min: -1000, max: 5000 })
    )
  });
  
  it('should persist any valid setting value across store instances', () => {
    fc.assert(
      fc.property(
        settingKeyArb,
        fc.nat(10000), // Random store ID to avoid conflicts
        (key, storeId) => {
          // Generate appropriate value for this key
          const value = fc.sample(settingValueArb(key), 1)[0];
          const storeName = `test-store-${storeId}`;
          const storePath = path.join(testStoreDir, storeName);
          
          // Clean up any existing store
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
          
          // Create first store instance and save setting
          const store1 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          store1.set(key, value);
          
          // Verify setting was saved
          const savedValue = store1.get(key);
          expect(savedValue).toEqual(value);
          
          // Create second store instance (simulates app restart)
          const store2 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          // Verify setting persisted
          const retrievedValue = store2.get(key);
          expect(retrievedValue).toEqual(value);
          
          // Property: Retrieved value must match saved value
          expect(retrievedValue).toEqual(savedValue);
          
          // Clean up
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  it('should persist window bounds across store instances', () => {
    fc.assert(
      fc.property(
        windowBoundsArb,
        fc.nat(10000), // Random store ID
        (bounds, storeId) => {
          const storeName = `test-store-bounds-${storeId}`;
          const storePath = path.join(testStoreDir, storeName);
          
          // Clean up any existing store
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
          
          // Create first store instance and save window bounds
          const store1 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          store1.set('windowBounds', bounds);
          
          // Verify bounds were saved
          const savedBounds = store1.get('windowBounds');
          expect(savedBounds).toEqual(bounds);
          
          // Create second store instance (simulates app restart)
          const store2 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          // Verify bounds persisted
          const retrievedBounds = store2.get('windowBounds');
          expect(retrievedBounds).toEqual(bounds);
          
          // Property: Retrieved bounds must match saved bounds
          expect(retrievedBounds).toEqual(savedBounds);
          
          // Property: All fields must be preserved
          expect(retrievedBounds.width).toBe(bounds.width);
          expect(retrievedBounds.height).toBe(bounds.height);
          expect(retrievedBounds.x).toBe(bounds.x);
          expect(retrievedBounds.y).toBe(bounds.y);
          
          // Clean up
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  it('should persist multiple settings simultaneously', () => {
    fc.assert(
      fc.property(
        fc.record({
          lastDirectory: fc.oneof(
            fc.constant(null),
            fc.string({ minLength: 1, maxLength: 50 }).map(s => `/dir/${s}`)
          ),
          theme: fc.constantFrom('light', 'dark', 'system'),
          autoUpdate: fc.boolean(),
          backendPort: fc.oneof(
            fc.constant(null),
            fc.integer({ min: 8000, max: 9000 })
          )
        }),
        fc.nat(10000), // Random store ID
        (settings, storeId) => {
          const storeName = `test-store-multi-${storeId}`;
          const storePath = path.join(testStoreDir, storeName);
          
          // Clean up any existing store
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
          
          // Create first store instance and save all settings
          const store1 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          for (const [key, value] of Object.entries(settings)) {
            store1.set(key, value);
          }
          
          // Create second store instance (simulates app restart)
          const store2 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          // Verify all settings persisted
          for (const [key, expectedValue] of Object.entries(settings)) {
            const retrievedValue = store2.get(key);
            
            // Property: Each setting must persist independently
            expect(retrievedValue).toEqual(expectedValue);
          }
          
          // Clean up
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  it('should handle setting updates (overwriting previous values)', () => {
    fc.assert(
      fc.property(
        settingKeyArb,
        fc.nat(10000), // Random store ID
        (key, storeId) => {
          // Generate two different values for this key
          const values = fc.sample(settingValueArb(key), 2);
          const value1 = values[0];
          const value2 = values[1];
          const storeName = `test-store-update-${storeId}`;
          const storePath = path.join(testStoreDir, storeName);
          
          // Clean up any existing store
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
          
          // Create store and save first value
          const store1 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          store1.set(key, value1);
          expect(store1.get(key)).toEqual(value1);
          
          // Update to second value
          store1.set(key, value2);
          expect(store1.get(key)).toEqual(value2);
          
          // Create new store instance (simulates app restart)
          const store2 = new Store({
            ...getStoreConfig(),
            cwd: testStoreDir,
            name: storeName
          });
          
          // Property: Latest value should persist, not the first value
          const retrievedValue = store2.get(key);
          expect(retrievedValue).toEqual(value2);
          
          // Clean up
          if (fs.existsSync(`${storePath}.json`)) {
            fs.unlinkSync(`${storePath}.json`);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
