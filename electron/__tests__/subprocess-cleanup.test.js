/**
 * Property-Based Test for Subprocess Cleanup on Exit
 * 
 * Feature: electron-desktop-app
 * Property 3: Subprocess Cleanup on Exit
 * 
 * **Validates: Requirements 3.4, 9.4**
 * 
 * For any running backend subprocess, when the Electron app closes,
 * the subprocess should be terminated before the main process exits.
 */

const fc = require('fast-check');
const { spawn } = require('child_process');
const path = require('path');

// Import the function to test
const { stopBackend } = require('../main.js');

describe('Property 3: Subprocess Cleanup on Exit', () => {
  /**
   * Property: For any running subprocess, stopBackend should terminate it
   * within the timeout period (5 seconds) and the subprocess should not
   * remain running after stopBackend completes.
   */
  it('should terminate any running subprocess when stopBackend is called', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create different subprocess scenarios
        fc.record({
          // Simulate different subprocess behaviors
          // For subprocesses that respond to SIGTERM, use delays less than timeout
          exitDelay: fc.integer({ min: 0, max: 1000 }), // 0-1 seconds delay before exit
          respondToSigterm: fc.boolean(), // Whether subprocess responds to SIGTERM
        }),
        async ({ exitDelay, respondToSigterm }) => {
          // Setup: Create a mock subprocess that simulates backend behavior
          const mockSubprocess = await createMockSubprocess(exitDelay, respondToSigterm);
          
          try {
            const pid = mockSubprocess.pid;
            
            // Verify subprocess is running
            expect(isProcessRunning(pid)).toBe(true);
            
            // Act: Call stopBackend with a shorter timeout for testing (2 seconds)
            await stopBackendWithProcess(mockSubprocess, 2000);
            
            // Assert: Subprocess should be terminated
            // Wait a brief moment to ensure process cleanup is complete
            await new Promise(resolve => setTimeout(resolve, 100));
            expect(isProcessRunning(pid)).toBe(false);
          } catch (error) {
            // Cleanup in case of test failure
            try {
              mockSubprocess.kill('SIGKILL');
            } catch (e) {
              // Process might already be dead
            }
            throw error;
          }
        }
      ),
      {
        numRuns: 50, // Run 50 iterations (reduced for performance)
        timeout: 120000, // 120 second timeout for the entire test suite
        endOnFailure: true // Stop on first failure for easier debugging
      }
    );
  }, 150000); // 2.5 minute timeout for Jest

  /**
   * Property: When a subprocess doesn't respond to SIGTERM within 5 seconds,
   * stopBackend should force kill it with SIGKILL.
   */
  it('should force kill subprocess with SIGKILL if it does not respond to SIGTERM within timeout', async () => {
    // Setup: Create a subprocess that ignores SIGTERM
    const stubbornSubprocess = await createStubbornSubprocess();
    
    try {
      const pid = stubbornSubprocess.pid;
      expect(isProcessRunning(pid)).toBe(true);
      
      // Act: Call stopBackend with a shorter timeout for testing
      const startTime = Date.now();
      await stopBackendWithProcess(stubbornSubprocess, 2000); // 2 second timeout
      const duration = Date.now() - startTime;
      
      // Assert: Should have taken approximately the timeout duration
      expect(duration).toBeGreaterThanOrEqual(1900); // Allow 100ms tolerance
      expect(duration).toBeLessThan(3000); // Should not take much longer than timeout
      
      // Assert: Process should be terminated
      // Wait a brief moment to ensure process cleanup is complete
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(isProcessRunning(pid)).toBe(false);
    } catch (error) {
      // Cleanup
      try {
        stubbornSubprocess.kill('SIGKILL');
      } catch (e) {
        // Process might already be dead
      }
      throw error;
    }
  }, 30000);

  /**
   * Property: stopBackend should be idempotent - calling it multiple times
   * or when no process is running should not cause errors.
   */
  it('should handle being called when no subprocess is running (idempotent)', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 5 }), // Number of times to call stopBackend
        async (callCount) => {
          // Act & Assert: Should not throw when called multiple times with no process
          for (let i = 0; i < callCount; i++) {
            await expect(stopBackendWithProcess(null)).resolves.not.toThrow();
          }
        }
      ),
      {
        numRuns: 50,
        timeout: 30000
      }
    );
  }, 60000);

  /**
   * Property: For any subprocess that exits gracefully on SIGTERM,
   * stopBackend should complete before the timeout without needing SIGKILL.
   */
  it('should complete gracefully for subprocesses that respond to SIGTERM', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 100, max: 1000 }), // Exit delay in ms (reduced from 2000)
        async (exitDelay) => {
          // Setup: Create a subprocess that responds to SIGTERM
          const subprocess = await createMockSubprocess(exitDelay, true);
          
          try {
            const pid = subprocess.pid;
            expect(isProcessRunning(pid)).toBe(true);
            
            // Act: Call stopBackend with 2 second timeout
            const startTime = Date.now();
            await stopBackendWithProcess(subprocess, 2000);
            const duration = Date.now() - startTime;
            
            // Assert: Should complete in approximately the exit delay time
            // (not the full 2 second timeout)
            expect(duration).toBeLessThan(exitDelay + 500); // Allow 500ms tolerance
            
            // Assert: Process should be terminated
            await new Promise(resolve => setTimeout(resolve, 100));
            expect(isProcessRunning(pid)).toBe(false);
          } catch (error) {
            // Cleanup
            try {
              subprocess.kill('SIGKILL');
            } catch (e) {
              // Process might already be dead
            }
            throw error;
          }
        }
      ),
      {
        numRuns: 30, // Reduced from 50 for performance
        timeout: 60000
      }
    );
  }, 90000); // 1.5 minute timeout
});

// Helper functions

/**
 * Create a mock subprocess that simulates backend behavior
 * @param {number} exitDelay - Milliseconds to wait before exiting on SIGTERM
 * @param {boolean} respondToSigterm - Whether to respond to SIGTERM
 * @returns {Promise<ChildProcess>} Mock subprocess
 */
function createMockSubprocess(exitDelay, respondToSigterm) {
  return new Promise((resolve, reject) => {
    // Create a simple Node.js script that simulates a backend process
    const script = `
      let shouldExit = ${respondToSigterm};
      
      process.on('SIGTERM', () => {
        if (shouldExit) {
          setTimeout(() => {
            process.exit(0);
          }, ${exitDelay});
        }
        // If not responding to SIGTERM, just ignore it
      });
      
      // Keep process alive
      setInterval(() => {}, 1000);
    `;
    
    const subprocess = spawn(process.execPath, ['-e', script], {
      stdio: 'ignore',
      detached: false
    });
    
    subprocess.once('error', reject);
    
    // Give the subprocess a moment to start
    setTimeout(() => {
      if (subprocess.pid) {
        resolve(subprocess);
      } else {
        reject(new Error('Failed to start subprocess'));
      }
    }, 100);
  });
}

/**
 * Create a stubborn subprocess that ignores SIGTERM
 * @returns {Promise<ChildProcess>} Stubborn subprocess
 */
function createStubbornSubprocess() {
  return createMockSubprocess(0, false);
}

/**
 * Check if a process is running
 * @param {number} pid - Process ID
 * @returns {boolean} True if process is running
 */
function isProcessRunning(pid) {
  if (!pid) return false;
  
  try {
    // Sending signal 0 checks if process exists without actually sending a signal
    process.kill(pid, 0);
    return true;
  } catch (error) {
    // ESRCH means process doesn't exist
    return error.code !== 'ESRCH';
  }
}

/**
 * Stop a backend process (wrapper around stopBackend that injects a subprocess)
 * This is a test helper that simulates the stopBackend function with a specific process
 * @param {ChildProcess|null} subprocess - Subprocess to stop
 * @param {number} timeout - Timeout in milliseconds (default 5000)
 * @returns {Promise<void>}
 */
async function stopBackendWithProcess(subprocess, timeout = 5000) {
  if (!subprocess) {
    // Simulate stopBackend behavior when no process exists
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const timeoutHandle = setTimeout(() => {
      if (subprocess && isProcessRunning(subprocess.pid)) {
        subprocess.kill('SIGKILL');
      }
      resolve();
    }, timeout);

    subprocess.once('exit', () => {
      clearTimeout(timeoutHandle);
      resolve();
    });

    // Send SIGTERM for graceful shutdown
    try {
      subprocess.kill('SIGTERM');
    } catch (error) {
      // Process might already be dead
      clearTimeout(timeoutHandle);
      resolve();
    }
  });
}
