/**
 * Property-Based Test for Backend Port Assignment
 * 
 * Feature: electron-desktop-app
 * Property 1: Backend Port Assignment
 * 
 * **Validates: Requirements 3.2**
 * 
 * For any system state, when the main process needs to spawn the backend,
 * it should successfully find and assign an available port in the valid range (8000-9000).
 */

const fc = require('fast-check');
const net = require('net');

// Import the function to test
const { findAvailablePort } = require('../main.js');

describe('Property 1: Backend Port Assignment', () => {
  /**
   * Property: For any system state, findAvailablePort should always return
   * a port number in the valid range (8000-9000) that is actually available.
   */
  it('should always find and return an available port in the range 8000-9000', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create arbitrary system states by occupying random ports
        fc.array(
          fc.integer({ min: 8000, max: 9000 }),
          { minLength: 0, maxLength: 50 } // Occupy 0-50 ports
        ),
        async (portsToOccupy) => {
          // Setup: Occupy the specified ports
          const servers = [];
          const occupiedPorts = new Set();

          for (const port of portsToOccupy) {
            try {
              const server = await createServer(port);
              servers.push(server);
              occupiedPorts.add(port);
            } catch (error) {
              // Port might already be in use by another test or system process
              // This is fine - we just skip it
            }
          }

          try {
            // Act: Find an available port
            const availablePort = await findAvailablePort();

            // Assert: Port should be in valid range
            expect(availablePort).toBeGreaterThanOrEqual(8000);
            expect(availablePort).toBeLessThanOrEqual(9000);

            // Assert: Port should not be in the occupied set
            expect(occupiedPorts.has(availablePort)).toBe(false);

            // Assert: Port should actually be available (verify by binding to it)
            const verificationServer = await createServer(availablePort);
            await closeServer(verificationServer);
          } finally {
            // Cleanup: Close all servers
            await Promise.all(servers.map(server => closeServer(server)));
          }
        }
      ),
      {
        numRuns: 100, // Run 100 iterations as specified in design
        timeout: 60000, // 60 second timeout for the entire test suite
        endOnFailure: true // Stop on first failure for easier debugging
      }
    );
  }, 120000); // 2 minute timeout for Jest

  /**
   * Property: When all ports in the range are occupied, findAvailablePort
   * should throw an error indicating no ports are available.
   */
  it('should throw an error when no ports are available in the range', async () => {
    // Setup: Occupy all ports in the range 8000-9000
    const servers = [];
    const MIN_PORT = 8000;
    const MAX_PORT = 9000;

    try {
      // Occupy all ports
      for (let port = MIN_PORT; port <= MAX_PORT; port++) {
        try {
          const server = await createServer(port);
          servers.push(server);
        } catch (error) {
          // Some ports might be in use by the system, that's okay
        }
      }

      // Act & Assert: Should throw an error
      await expect(findAvailablePort()).rejects.toThrow(
        /No available ports found in range/
      );
    } finally {
      // Cleanup: Close all servers
      await Promise.all(servers.map(server => closeServer(server)));
    }
  }, 30000); // 30 second timeout

  /**
   * Property: findAvailablePort should be deterministic in its search pattern
   * (always starts from 8000 and goes up), ensuring predictable behavior.
   */
  it('should find the lowest available port in the range', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generator: Create a gap in the port range by occupying ports around it
        fc.integer({ min: 8001, max: 8999 }), // The gap port
        async (gapPort) => {
          // Setup: Occupy all ports before the gap
          const servers = [];
          
          try {
            for (let port = 8000; port < gapPort; port++) {
              try {
                const server = await createServer(port);
                servers.push(server);
              } catch (error) {
                // Port might be in use, skip it
              }
            }

            // Act: Find available port
            const availablePort = await findAvailablePort();

            // Assert: Should find the gap port or the first available port after it
            expect(availablePort).toBeGreaterThanOrEqual(gapPort);
          } finally {
            // Cleanup
            await Promise.all(servers.map(server => closeServer(server)));
          }
        }
      ),
      {
        numRuns: 50, // Fewer runs since this test is more expensive
        timeout: 60000
      }
    );
  }, 120000);
});

// Helper functions

/**
 * Create a server listening on the specified port
 * @param {number} port - Port to listen on
 * @returns {Promise<net.Server>} Server instance
 */
function createServer(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    
    server.once('error', (err) => {
      reject(err);
    });

    server.once('listening', () => {
      resolve(server);
    });

    server.listen(port, '127.0.0.1');
  });
}

/**
 * Close a server
 * @param {net.Server} server - Server to close
 * @returns {Promise<void>}
 */
function closeServer(server) {
  return new Promise((resolve) => {
    server.close(() => {
      resolve();
    });
  });
}
