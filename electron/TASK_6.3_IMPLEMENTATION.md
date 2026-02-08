# Task 6.3 Implementation: Property Test for Window Bounds Persistence

## Overview

Implemented comprehensive property-based tests for window bounds persistence using fast-check. The tests validate **Property 6: Window Bounds Persistence** which ensures that window size and position are correctly saved and restored across application sessions.

**Validates: Requirements 9.2, 15.5**

## Implementation Details

### Test File Created

- `electron/__tests__/window-bounds-persistence.property.test.js`

### Property Tests Implemented

The test suite includes 8 property-based tests that verify different aspects of window bounds persistence:

#### 1. **Exact Persistence of Valid Bounds**
- **Property**: For any valid window bounds (within screen limits), when saved and then loaded, the bounds should be restored exactly.
- **Generator**: Creates arbitrary valid window bounds (width: 1024-3840, height: 768-2160, x: 0-1000, y: 0-500)
- **Assertion**: Loaded bounds match original bounds exactly
- **Runs**: 100 iterations

#### 2. **Minimum Dimension Enforcement**
- **Property**: For any window bounds, after validation, the width should always be at least 1024 and height at least 768.
- **Generator**: Creates arbitrary bounds including invalid ones (width: 100-5000, height: 100-3000)
- **Assertion**: Validated bounds meet minimum requirements
- **Runs**: 100 iterations

#### 3. **Invalid Dimension Replacement**
- **Property**: For any window bounds with invalid dimensions (non-numeric, negative, or too small), validation should replace them with valid defaults.
- **Generator**: Creates bounds with potentially invalid dimensions (null, undefined, 'invalid', NaN, negative, below minimum)
- **Assertion**: Invalid dimensions are replaced with valid defaults (≥1024 width, ≥768 height)
- **Runs**: 100 iterations

#### 4. **Off-Screen Position Reset**
- **Property**: For any window position where the window center would be off-screen, validation should reset the position to undefined (centered).
- **Generator**: Creates bounds with positions way off-screen (x: 5000-10000, y: 5000-10000)
- **Assertion**: Position is reset to undefined (centered), dimensions are preserved
- **Runs**: 100 iterations

#### 5. **Multi-Monitor Position Preservation**
- **Property**: For any valid window bounds on a multi-monitor setup, validation should preserve the position if it's visible on any display.
- **Generator**: Creates bounds that could be on any of three monitors (primary, right, left)
- **Assertion**: Position is preserved if on a valid display, reset if not
- **Runs**: 100 iterations

#### 6. **Sequential Changes Persistence**
- **Property**: For any sequence of window bound changes (resize, move), the final saved state should match the last bounds set.
- **Generator**: Creates a sequence of 1-10 valid bound changes
- **Assertion**: Loaded bounds match the last bounds in the sequence
- **Runs**: 100 iterations

#### 7. **Idempotent Round-Trip**
- **Property**: For any valid bounds, the round-trip of save → load → validate should preserve the bounds exactly (idempotent operation).
- **Generator**: Creates valid window bounds with positions that ensure window center is on-screen
- **Assertion**: After round-trip and re-validation, bounds remain unchanged
- **Runs**: 100 iterations

#### 8. **Centered Window Position Preservation**
- **Property**: For any bounds with undefined x and y (centered window), validation should preserve the undefined values.
- **Generator**: Creates bounds with undefined position
- **Assertion**: Position remains undefined, dimensions are preserved
- **Runs**: 100 iterations

## Bug Fix

During test implementation, discovered and fixed a bug in `validateWindowBounds` function:

### Issue
The function checked `typeof bounds.width !== 'number'` but `NaN` is of type `'number'`, so it passed the type check and wasn't properly handled.

### Fix
Added explicit `isNaN()` check:

```javascript
// Before
if (typeof bounds.width !== 'number' || bounds.width < 1024) {

// After
if (typeof bounds.width !== 'number' || isNaN(bounds.width) || bounds.width < 1024) {
```

Applied to both width and height validation.

## Test Results

All tests pass successfully:

```
Property 6: Window Bounds Persistence
  ✓ should persist and restore valid window bounds exactly (12 ms)
  ✓ should enforce minimum dimensions after validation (7 ms)
  ✓ should replace invalid dimensions with defaults (10 ms)
  ✓ should reset off-screen positions to centered (6 ms)
  ✓ should preserve valid positions on multi-monitor setups (6 ms)
  ✓ should persist the most recent bounds after multiple changes (3 ms)
  ✓ should be idempotent for valid bounds (save-load-validate preserves bounds) (6 ms)
  ✓ should preserve undefined position for centered windows (6 ms)

Tests: 8 passed, 8 total
```

## Integration with Existing Tests

The property tests complement the existing unit tests in `window-state-persistence.test.js`:
- **Unit tests**: Verify specific examples and edge cases (11 tests)
- **Property tests**: Verify universal properties across all inputs (8 tests)

Total test coverage for window bounds persistence: **19 tests**

## Key Design Decisions

1. **Generator Strategy**: Used `fc.record()` to generate structured window bounds objects with appropriate constraints for each property being tested.

2. **Multi-Monitor Testing**: Mocked a three-monitor setup (primary, right, left) to test position validation across different display configurations.

3. **Idempotency Testing**: Used `fc.chain()` to generate positions that are guaranteed to be valid for the given window dimensions, ensuring the test validates true idempotency rather than error correction.

4. **Comprehensive Coverage**: Tests cover:
   - Valid bounds persistence
   - Invalid input handling (NaN, null, undefined, strings, negative values)
   - Off-screen detection and correction
   - Multi-monitor support
   - Sequential state changes
   - Idempotent operations
   - Centered window handling

## Requirements Validation

✅ **Requirement 9.2**: "THE application window SHALL be resizable and remember its size and position between sessions"
- Validated by tests 1, 6, 7 (persistence of size and position)

✅ **Requirement 15.5**: "THE Electron_App SHALL save window size and position for restoration on next launch"
- Validated by all 8 tests (comprehensive save/load/validate cycle)

## Conclusion

Task 6.3 is complete. The property-based tests provide comprehensive validation of window bounds persistence across a wide range of inputs and scenarios, ensuring robust behavior in production. The tests run 100 iterations each (800 total test cases) to verify the properties hold universally.
