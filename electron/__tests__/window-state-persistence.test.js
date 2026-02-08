/**
 * Unit tests for window state persistence
 * Tests Task 6.2: Implement window state persistence
 * Requirements: 9.2, 15.5
 */

const { validateWindowBounds } = require('../main');

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
  BrowserWindow: jest.fn(),
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

jest.mock('electron-store');

describe('Window State Persistence', () => {
  describe('validateWindowBounds', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should accept valid window bounds within screen', () => {
      const bounds = {
        width: 1200,
        height: 900,
        x: 100,
        y: 100
      };

      const result = validateWindowBounds(bounds);

      expect(result).toEqual(bounds);
    });

    it('should reset to defaults if width is too small', () => {
      const bounds = {
        width: 800, // Less than minimum 1024
        height: 900,
        x: 100,
        y: 100
      };

      const result = validateWindowBounds(bounds);

      expect(result.width).toBe(1024);
      expect(result.height).toBe(900);
    });

    it('should reset to defaults if height is too small', () => {
      const bounds = {
        width: 1200,
        height: 600, // Less than minimum 768
        x: 100,
        y: 100
      };

      const result = validateWindowBounds(bounds);

      expect(result.width).toBe(1200);
      expect(result.height).toBe(768);
    });

    it('should reset to defaults if width is invalid', () => {
      const bounds = {
        width: 'invalid',
        height: 900,
        x: 100,
        y: 100
      };

      const result = validateWindowBounds(bounds);

      expect(result.width).toBe(1024);
    });

    it('should reset to defaults if height is invalid', () => {
      const bounds = {
        width: 1200,
        height: null,
        x: 100,
        y: 100
      };

      const result = validateWindowBounds(bounds);

      expect(result.height).toBe(768);
    });

    it('should allow undefined x and y for centered window', () => {
      const bounds = {
        width: 1200,
        height: 900,
        x: undefined,
        y: undefined
      };

      const result = validateWindowBounds(bounds);

      expect(result.x).toBeUndefined();
      expect(result.y).toBeUndefined();
      expect(result.width).toBe(1200);
      expect(result.height).toBe(900);
    });

    it('should reset position if window would be off-screen', () => {
      const bounds = {
        width: 1200,
        height: 900,
        x: 5000, // Way off screen
        y: 5000
      };

      const result = validateWindowBounds(bounds);

      // Position should be reset to undefined (centered)
      expect(result.x).toBeUndefined();
      expect(result.y).toBeUndefined();
      // Size should be preserved
      expect(result.width).toBe(1200);
      expect(result.height).toBe(900);
    });

    it('should accept window position at edge of screen', () => {
      const bounds = {
        width: 1200,
        height: 900,
        x: 360, // Center at 960 (360 + 1200/2)
        y: 90   // Center at 540 (90 + 900/2)
      };

      const result = validateWindowBounds(bounds);

      expect(result).toEqual(bounds);
    });

    it('should handle multiple displays', () => {
      const { screen } = require('electron');
      screen.getAllDisplays.mockReturnValueOnce([
        { bounds: { x: 0, y: 0, width: 1920, height: 1080 } },
        { bounds: { x: 1920, y: 0, width: 1920, height: 1080 } }
      ]);

      const bounds = {
        width: 1200,
        height: 900,
        x: 2000, // On second display
        y: 100
      };

      const result = validateWindowBounds(bounds);

      // Should be valid on second display
      expect(result).toEqual(bounds);
    });

    it('should reset if window center is off all displays', () => {
      const { screen } = require('electron');
      screen.getAllDisplays.mockReturnValueOnce([
        { bounds: { x: 0, y: 0, width: 1920, height: 1080 } },
        { bounds: { x: 1920, y: 0, width: 1920, height: 1080 } }
      ]);

      const bounds = {
        width: 1200,
        height: 900,
        x: -2000, // Way off to the left
        y: 100
      };

      const result = validateWindowBounds(bounds);

      expect(result.x).toBeUndefined();
      expect(result.y).toBeUndefined();
    });

    it('should handle edge case with negative coordinates on multi-monitor setup', () => {
      const { screen } = require('electron');
      screen.getAllDisplays.mockReturnValueOnce([
        { bounds: { x: -1920, y: 0, width: 1920, height: 1080 } }, // Left monitor
        { bounds: { x: 0, y: 0, width: 1920, height: 1080 } }       // Right monitor
      ]);

      const bounds = {
        width: 1200,
        height: 900,
        x: -1500, // On left monitor
        y: 100
      };

      const result = validateWindowBounds(bounds);

      // Should be valid on left display
      expect(result).toEqual(bounds);
    });
  });
});
