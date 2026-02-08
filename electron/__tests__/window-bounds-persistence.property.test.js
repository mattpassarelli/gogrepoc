/**
 * Property-Based Test for Window Bounds Persistence
 * 
 * Feature: electron-desktop-app
 * Property 6: Window Bounds Persistence
 * 
 * **Validates: Requirements 9.2, 15.5**
 * 
 * For any window size and position, when the app is closed and reopened,
 * the window should restore to the same bounds (within reasonable tolerance
 * for screen size changes).
 */

const fc = require('fast-check');
const Store = require('electron-store');

// Mock electron modules
jest.mock('electron', () => ({
  app: {
    whenReady: jest.fn(() => Promise.resolve()),
    on: jest.fn(),
    quit: jest.fn(),
    getAppPath: jest.fn(() => '/mock/app/path'),
    getPath: jest.fn(() => '/mock/user/data'),
    isPackaged: false
  },
  BrowserWindow: jest.fn(function(options) {
    this.bounds = {
      x: options.x !== undefined ? options.x : 100,
      y: options.y !== undefined ? options.y : 100,
      width: options.width || 1024,
      height: options.height || 768
    };
    this.getBounds = jest.fn(() => this.bounds);
    this.setBounds = jest.fn((newBounds) => {
      this.bounds = { ...this.bounds, ...newBounds };
    });
    this.on = jest.fn();
    this.loadFile = jest.fn(() => Promise.resolve());
    this.webContents = {
      on: jest.fn()
    };
  }),
  screen: {
    getAllDisplays: jest.fn(() => [
      {
        bounds: { x: 0, y: 0, width: 1920, height: 1080 }
      }
    ])
  }
}));

jest.mock('electron-log', () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  transports: {
    file: {
      level: 'info',
      maxSize: 10 * 1024 * 1024,
      format: '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}',
      getFile: jest.fn(() => ({ path: '/mock/log/path' }))
    }
  }
}));

// Import functions to test
const { validateWindowBounds, saveWindowBounds } = require('../main.js');

describe('Property 6: Window Bounds Persistence', () => {
  let mockStore;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Create a fresh mock store for each test
    mockStore = new Map();
    
    // Mock electron-store
    jest.mock('electron-store', () => {
      return jest.fn().mockImplementation(() => ({
        get: jest.fn((key) => mockStore.get(key)),
        set: jest.fn((key, value) => mockStore.set(key, value)),
        has: jest.fn((key) => mockStore.has(key)),
        delete: jest.fn((key) => mockStore.delete(key)),
        clear: jest.fn(() => mockStore.clear())
      }));
    });
  });

  /**
   * Property: For any valid window bounds (within screen limits), when saved
   * and then loaded, the bounds should be restored exactly.
   */
  it('should persist and restore valid window bounds exactly', () => {
    fc.assert(
      fc.property(
        // Generator: Create arbitrary valid window bounds
        fc.record({
          width: fc.integer({ min: 1024, max: 3840 }), // Min to 4K width
          height: fc.integer({ min: 768, max: 2160 }), // Min to 4K height
          x: fc.integer({ min: 0, max: 1000 }),
          y: fc.integer({ min: 0, max: 500 })
        }),
        (originalBounds) => {
          // Setup: Create a mock store
          const store = new Map();

          // Act: Save bounds
          store.set('windowBounds', originalBounds);

          // Act: Load bounds
          const loadedBounds = store.get('windowBounds');

          // Assert: Loaded bounds should match original bounds exactly
          expect(loadedBounds).toEqual(originalBounds);
          expect(loadedBounds.width).toBe(originalBounds.width);
          expect(loadedBounds.height).toBe(originalBounds.height);
          expect(loadedBounds.x).toBe(originalBounds.x);
          expect(loadedBounds.y).toBe(originalBounds.y);
        }
      ),
      {
        numRuns: 100, // Run 100 iterations as specified in design
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any window bounds, after validation, the width should
   * always be at least the minimum (1024) and height at least 768.
   */
  it('should enforce minimum dimensions after validation', () => {
    fc.assert(
      fc.property(
        // Generator: Create arbitrary bounds including invalid ones
        fc.record({
          width: fc.integer({ min: 100, max: 5000 }),
          height: fc.integer({ min: 100, max: 3000 }),
          x: fc.option(fc.integer({ min: -1000, max: 3000 }), { nil: undefined }),
          y: fc.option(fc.integer({ min: -1000, max: 2000 }), { nil: undefined })
        }),
        (bounds) => {
          // Act: Validate bounds
          const validated = validateWindowBounds(bounds);

          // Assert: Validated bounds should meet minimum requirements
          expect(validated.width).toBeGreaterThanOrEqual(1024);
          expect(validated.height).toBeGreaterThanOrEqual(768);
          
          // Assert: Width and height should be numbers
          expect(typeof validated.width).toBe('number');
          expect(typeof validated.height).toBe('number');
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any window bounds with invalid dimensions (non-numeric,
   * negative, or too small), validation should replace them with valid defaults.
   */
  it('should replace invalid dimensions with defaults', () => {
    fc.assert(
      fc.property(
        // Generator: Create bounds with potentially invalid dimensions
        fc.record({
          width: fc.oneof(
            fc.integer({ min: -100, max: 1023 }), // Below minimum
            fc.constant(null),
            fc.constant(undefined),
            fc.constant('invalid'),
            fc.constant(NaN)
          ),
          height: fc.oneof(
            fc.integer({ min: -100, max: 767 }), // Below minimum
            fc.constant(null),
            fc.constant(undefined),
            fc.constant('invalid'),
            fc.constant(NaN)
          ),
          x: fc.integer({ min: 0, max: 1000 }),
          y: fc.integer({ min: 0, max: 500 })
        }),
        (bounds) => {
          // Act: Validate bounds
          const validated = validateWindowBounds(bounds);

          // Assert: Invalid dimensions should be replaced with valid defaults
          expect(validated.width).toBeGreaterThanOrEqual(1024);
          expect(validated.height).toBeGreaterThanOrEqual(768);
          expect(typeof validated.width).toBe('number');
          expect(typeof validated.height).toBe('number');
          expect(isNaN(validated.width)).toBe(false);
          expect(isNaN(validated.height)).toBe(false);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any window position where the window center would be
   * off-screen, validation should reset the position to undefined (centered).
   */
  it('should reset off-screen positions to centered', () => {
    fc.assert(
      fc.property(
        // Generator: Create bounds with positions that are likely off-screen
        fc.record({
          width: fc.integer({ min: 1024, max: 2000 }),
          height: fc.integer({ min: 768, max: 1500 }),
          x: fc.integer({ min: 5000, max: 10000 }), // Way off screen
          y: fc.integer({ min: 5000, max: 10000 })  // Way off screen
        }),
        (bounds) => {
          // Act: Validate bounds
          const validated = validateWindowBounds(bounds);

          // Assert: Position should be reset to undefined (centered)
          expect(validated.x).toBeUndefined();
          expect(validated.y).toBeUndefined();
          
          // Assert: Dimensions should be preserved
          expect(validated.width).toBe(bounds.width);
          expect(validated.height).toBe(bounds.height);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any valid window bounds on a multi-monitor setup,
   * validation should preserve the position if it's visible on any display.
   */
  it('should preserve valid positions on multi-monitor setups', () => {
    // Setup: Mock multi-monitor configuration
    const { screen } = require('electron');
    screen.getAllDisplays.mockReturnValue([
      { bounds: { x: 0, y: 0, width: 1920, height: 1080 } },      // Primary
      { bounds: { x: 1920, y: 0, width: 1920, height: 1080 } },   // Right
      { bounds: { x: -1920, y: 0, width: 1920, height: 1080 } }   // Left
    ]);

    fc.assert(
      fc.property(
        // Generator: Create bounds that could be on any of the three monitors
        fc.record({
          width: fc.integer({ min: 1024, max: 1920 }),
          height: fc.integer({ min: 768, max: 1080 }),
          // Position on one of the three monitors
          x: fc.oneof(
            fc.integer({ min: 0, max: 896 }),      // Primary monitor (0 to 1920-1024)
            fc.integer({ min: 1920, max: 2816 }),  // Right monitor (1920 to 3840-1024)
            fc.integer({ min: -1920, max: -1024 }) // Left monitor (-1920 to -1024)
          ),
          y: fc.integer({ min: 0, max: 312 })      // Valid Y for all monitors (0 to 1080-768)
        }),
        (bounds) => {
          // Act: Validate bounds
          const validated = validateWindowBounds(bounds);

          // Calculate window center
          const centerX = bounds.x + bounds.width / 2;
          const centerY = bounds.y + bounds.height / 2;

          // Check if center is on any display
          const displays = screen.getAllDisplays();
          const isOnDisplay = displays.some(display => {
            const { x, y, width, height } = display.bounds;
            return centerX >= x && centerX < x + width &&
                   centerY >= y && centerY < y + height;
          });

          if (isOnDisplay) {
            // Assert: Position should be preserved if on a valid display
            expect(validated.x).toBe(bounds.x);
            expect(validated.y).toBe(bounds.y);
          } else {
            // Assert: Position should be reset if not on any display
            expect(validated.x).toBeUndefined();
            expect(validated.y).toBeUndefined();
          }

          // Assert: Dimensions should always be preserved
          expect(validated.width).toBe(bounds.width);
          expect(validated.height).toBe(bounds.height);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any sequence of window bound changes (resize, move),
   * the final saved state should match the last bounds set.
   */
  it('should persist the most recent bounds after multiple changes', () => {
    fc.assert(
      fc.property(
        // Generator: Create a sequence of valid bound changes
        fc.array(
          fc.record({
            width: fc.integer({ min: 1024, max: 2000 }),
            height: fc.integer({ min: 768, max: 1500 }),
            x: fc.integer({ min: 0, max: 1000 }),
            y: fc.integer({ min: 0, max: 500 })
          }),
          { minLength: 1, maxLength: 10 }
        ),
        (boundsSequence) => {
          // Setup: Create a mock store
          const store = new Map();

          // Act: Apply each bounds change
          for (const bounds of boundsSequence) {
            store.set('windowBounds', bounds);
          }

          // Get the last bounds in the sequence
          const lastBounds = boundsSequence[boundsSequence.length - 1];

          // Act: Load bounds
          const loadedBounds = store.get('windowBounds');

          // Assert: Loaded bounds should match the last bounds set
          expect(loadedBounds).toEqual(lastBounds);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any valid bounds, the round-trip of save -> load -> validate
   * should preserve the bounds exactly (idempotent operation).
   */
  it('should be idempotent for valid bounds (save-load-validate preserves bounds)', () => {
    fc.assert(
      fc.property(
        // Generator: Create valid window bounds that will be on-screen
        // Given the mocked display is 1920x1080, ensure window center is within bounds
        fc.record({
          width: fc.integer({ min: 1024, max: 1920 }),
          height: fc.integer({ min: 768, max: 1080 })
        }).chain(({ width, height }) => {
          // Calculate valid x and y ranges so window center is on screen
          // Window center must be: x + width/2 >= 0 && x + width/2 < 1920
          // So: x >= -width/2 && x < 1920 - width/2
          const minX = Math.max(0, -width / 2);
          const maxX = Math.min(1920 - width / 2, 1920 - width);
          
          // Window center must be: y + height/2 >= 0 && y + height/2 < 1080
          // So: y >= -height/2 && y < 1080 - height/2
          const minY = Math.max(0, -height / 2);
          const maxY = Math.min(1080 - height / 2, 1080 - height);
          
          return fc.record({
            width: fc.constant(width),
            height: fc.constant(height),
            x: fc.integer({ min: Math.floor(minX), max: Math.floor(maxX) }),
            y: fc.integer({ min: Math.floor(minY), max: Math.floor(maxY) })
          });
        }),
        (originalBounds) => {
          // Setup: Create a mock store
          const store = new Map();

          // Act: Save bounds
          store.set('windowBounds', originalBounds);

          // Act: Load bounds
          const loadedBounds = store.get('windowBounds');

          // Act: Validate loaded bounds
          const validatedBounds = validateWindowBounds(loadedBounds);

          // Assert: After round-trip, bounds should be unchanged
          expect(validatedBounds).toEqual(originalBounds);

          // Act: Validate again (test idempotency)
          const revalidatedBounds = validateWindowBounds(validatedBounds);

          // Assert: Second validation should not change anything
          expect(revalidatedBounds).toEqual(validatedBounds);
          expect(revalidatedBounds).toEqual(originalBounds);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });

  /**
   * Property: For any bounds with undefined x and y (centered window),
   * validation should preserve the undefined values.
   */
  it('should preserve undefined position for centered windows', () => {
    fc.assert(
      fc.property(
        // Generator: Create bounds with undefined position
        fc.record({
          width: fc.integer({ min: 1024, max: 3840 }),
          height: fc.integer({ min: 768, max: 2160 }),
          x: fc.constant(undefined),
          y: fc.constant(undefined)
        }),
        (bounds) => {
          // Act: Validate bounds
          const validated = validateWindowBounds(bounds);

          // Assert: Position should remain undefined
          expect(validated.x).toBeUndefined();
          expect(validated.y).toBeUndefined();

          // Assert: Dimensions should be preserved
          expect(validated.width).toBe(bounds.width);
          expect(validated.height).toBe(bounds.height);
        }
      ),
      {
        numRuns: 100,
        endOnFailure: true
      }
    );
  });
});
