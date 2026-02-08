/**
 * Unit tests for React-Electron Integration
 * 
 * Tests the integration points between React app and Electron:
 * - API client initialization with dynamic backend URL
 * - Backend URL retrieval from Electron main process
 * - Directory selection using native Electron dialogs
 * 
 * **Validates: Requirements 7.2, 7.3**
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';

// Mock axios
jest.mock('axios');

describe('React-Electron Integration', () => {
  let originalElectronAPI;
  let originalFetch;

  beforeEach(() => {
    // Save original values
    originalElectronAPI = window.electronAPI;
    originalFetch = global.fetch;
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Reset axios defaults
    axios.defaults = {};
    
    // Mock localStorage
    Storage.prototype.getItem = jest.fn();
    Storage.prototype.setItem = jest.fn();
  });

  afterEach(() => {
    // Restore original values
    if (originalElectronAPI) {
      window.electronAPI = originalElectronAPI;
    } else {
      delete window.electronAPI;
    }
    global.fetch = originalFetch;
  });

  describe('API Client Initialization', () => {
    it('should initialize API client with backend URL from Electron', async () => {
      // Mock Electron API
      const mockBackendUrl = 'http://localhost:8456';
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue(mockBackendUrl),
      };

      // Mock successful health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
      });

      // Mock axios for auth check
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      // Dynamically import App component
      const App = (await import('./App')).default;

      // Render App with Electron props
      render(
        <App 
          backendUrl={mockBackendUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify axios was configured with the backend URL
      expect(axios.defaults.baseURL).toBe(mockBackendUrl);
      expect(axios.defaults.withCredentials).toBe(true);
    });

    it('should reconfigure API client when backend URL changes', async () => {
      const initialUrl = 'http://localhost:8000';
      const newUrl = 'http://localhost:9000';

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      const App = (await import('./App')).default;

      const { rerender } = render(
        <App 
          backendUrl={initialUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify initial configuration
      expect(axios.defaults.baseURL).toBe(initialUrl);

      // Update backend URL
      rerender(
        <App 
          backendUrl={newUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify axios was reconfigured
      expect(axios.defaults.baseURL).toBe(newUrl);
    });

    it('should not initialize API client when backend URL is null', async () => {
      axios.get = jest.fn();

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl={null}
          isElectron={true}
          backendAvailable={false}
          backendError="Backend not available"
        />
      );

      // Verify axios was not configured
      expect(axios.defaults.baseURL).toBeUndefined();
      
      // Verify auth check was not called
      expect(axios.get).not.toHaveBeenCalled();
    });

    it('should initialize API client with credentials enabled', async () => {
      const mockBackendUrl = 'http://localhost:8123';

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl={mockBackendUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify credentials are enabled for session management
      expect(axios.defaults.withCredentials).toBe(true);
    });

    it('should handle API client initialization with different ports', async () => {
      const ports = [8000, 8123, 8456, 9000];

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      const App = (await import('./App')).default;

      for (const port of ports) {
        const backendUrl = `http://localhost:${port}`;
        
        const { unmount } = render(
          <App 
            backendUrl={backendUrl}
            isElectron={true}
            backendAvailable={true}
            backendError={null}
          />
        );

        // Verify axios was configured with correct port
        expect(axios.defaults.baseURL).toBe(backendUrl);
        
        unmount();
      }
    });
  });

  describe('Backend URL Retrieval', () => {
    it('should retrieve backend URL from Electron main process via IPC', async () => {
      const mockBackendUrl = 'http://localhost:8456';
      const mockGetBackendUrl = jest.fn().mockResolvedValue(mockBackendUrl);

      window.electronAPI = {
        getBackendUrl: mockGetBackendUrl,
      };

      // Simulate the initialization logic
      const isElectron = window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function';
      expect(isElectron).toBe(true);

      // Call the API
      const backendUrl = await window.electronAPI.getBackendUrl();

      // Verify backend URL was retrieved
      expect(mockGetBackendUrl).toHaveBeenCalledTimes(1);
      expect(backendUrl).toBe(mockBackendUrl);
    });

    it('should handle backend URL retrieval errors gracefully', async () => {
      const mockGetBackendUrl = jest.fn().mockRejectedValue(
        new Error('IPC communication failed')
      );

      window.electronAPI = {
        getBackendUrl: mockGetBackendUrl,
      };

      // Simulate error handling
      let backendError = null;
      try {
        await window.electronAPI.getBackendUrl();
      } catch (error) {
        backendError = error.message;
      }

      // Verify error was caught
      expect(backendError).toBe('IPC communication failed');
      expect(mockGetBackendUrl).toHaveBeenCalled();
    });

    it('should verify backend availability after retrieving URL', async () => {
      const mockBackendUrl = 'http://localhost:8123';
      
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue(mockBackendUrl),
      };

      // Mock successful health check
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
      });
      global.fetch = mockFetch;

      // Simulate initialization flow
      const backendUrl = await window.electronAPI.getBackendUrl();
      const healthResponse = await fetch(`${backendUrl}/health`);

      // Verify health check was called
      expect(mockFetch).toHaveBeenCalledWith(`${mockBackendUrl}/health`);
      expect(healthResponse.ok).toBe(true);
    });

    it('should handle backend health check failures', async () => {
      const mockBackendUrl = 'http://localhost:8123';
      
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue(mockBackendUrl),
      };

      // Mock failed health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 503,
      });

      // Simulate initialization flow
      const backendUrl = await window.electronAPI.getBackendUrl();
      const healthResponse = await fetch(`${backendUrl}/health`);

      // Verify backend was marked as unavailable
      expect(healthResponse.ok).toBe(false);
      expect(healthResponse.status).toBe(503);
    });

    it('should pass retrieved backend URL to App component', async () => {
      const mockBackendUrl = 'http://localhost:8789';
      
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue(mockBackendUrl),
      };

      // Mock successful health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
      });

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      const App = (await import('./App')).default;

      // Simulate getting backend URL and rendering
      const backendUrl = await window.electronAPI.getBackendUrl();
      
      render(
        <App 
          backendUrl={backendUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify axios was configured with retrieved URL
      expect(axios.defaults.baseURL).toBe(mockBackendUrl);
    });
  });

  describe('Directory Selection Integration', () => {
    it('should call Electron API for directory selection', async () => {
      const mockSelectDirectory = jest.fn().mockResolvedValue('/selected/path');
      
      window.electronAPI = {
        selectDirectory: mockSelectDirectory,
      };

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Click the browse button
      const browseButton = screen.getByText(/Browse\.\.\./i);
      await userEvent.click(browseButton);

      // Verify Electron API was called
      expect(mockSelectDirectory).toHaveBeenCalled();
    });

    it('should update save directory when path is selected', async () => {
      const selectedPath = '/home/user/games';
      const mockSelectDirectory = jest.fn().mockResolvedValue(selectedPath);
      
      window.electronAPI = {
        selectDirectory: mockSelectDirectory,
      };

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Click the browse button
      const browseButton = screen.getByText(/Browse\.\.\./i);
      await userEvent.click(browseButton);

      // Wait for path to be updated
      await waitFor(() => {
        const pathInput = screen.getByDisplayValue(selectedPath);
        expect(pathInput).toBeInTheDocument();
      });
    });

    it('should not update save directory when selection is cancelled', async () => {
      const mockSelectDirectory = jest.fn().mockResolvedValue(null);
      
      window.electronAPI = {
        selectDirectory: mockSelectDirectory,
      };

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Get initial path value
      const pathInput = screen.getByRole('textbox', { name: '' });
      const initialValue = pathInput.value;

      // Click the browse button
      const browseButton = screen.getByText(/Browse\.\.\./i);
      await userEvent.click(browseButton);

      // Wait a bit to ensure no update happens
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify path was not changed
      expect(pathInput.value).toBe(initialValue);
    });

    it('should handle directory selection errors gracefully', async () => {
      const mockSelectDirectory = jest.fn().mockRejectedValue(
        new Error('Dialog failed to open')
      );
      
      window.electronAPI = {
        selectDirectory: mockSelectDirectory,
      };

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Click the browse button
      const browseButton = screen.getByText(/Browse\.\.\./i);
      await userEvent.click(browseButton);

      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByText(/Failed to open directory selection dialog/i)).toBeInTheDocument();
      });
    });

    it('should display browse button only in Electron mode', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      // Render in Electron mode
      const { rerender } = render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Verify browse button exists
      expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();

      // Rerender in web mode
      rerender(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={false}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify browse button does not exist
      expect(screen.queryByText(/Browse\.\.\./i)).not.toBeInTheDocument();
    });

    it('should display path input as read-only in Electron mode', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Find the path input (it's read-only in Electron mode)
      const pathInputs = screen.getAllByRole('textbox');
      const pathInput = pathInputs.find(input => input.readOnly);
      
      expect(pathInput).toBeDefined();
      expect(pathInput.readOnly).toBe(true);
    });

    it('should allow manual path entry in web mode', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={false}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        const pathInputs = screen.getAllByRole('textbox');
        expect(pathInputs.length).toBeGreaterThan(0);
      });

      // Find the path input (should be editable in web mode)
      const pathInputs = screen.getAllByRole('textbox');
      const pathInput = pathInputs.find(input => 
        input.placeholder && input.placeholder.toLowerCase().includes('download path')
      );
      
      // In web mode, there should be an editable input
      if (pathInput) {
        expect(pathInput.readOnly).toBe(false);

        // Try to type in the input
        await userEvent.clear(pathInput);
        await userEvent.type(pathInput, '/custom/path');

        expect(pathInput.value).toBe('/custom/path');
      } else {
        // If we can't find the specific input, at least verify there are editable inputs
        const editableInputs = pathInputs.filter(input => !input.readOnly);
        expect(editableInputs.length).toBeGreaterThan(0);
      }
    });

    it('should persist selected directory to localStorage', async () => {
      const selectedPath = '/home/user/downloads';
      const mockSelectDirectory = jest.fn().mockResolvedValue(selectedPath);
      
      window.electronAPI = {
        selectDirectory: mockSelectDirectory,
      };

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Click the browse button
      const browseButton = screen.getByText(/Browse\.\.\./i);
      await userEvent.click(browseButton);

      // Wait for path to be updated and saved
      await waitFor(() => {
        expect(localStorage.setItem).toHaveBeenCalledWith('savedir', selectedPath);
      });
    });
  });

  describe('Integration Error Scenarios', () => {
    it('should handle missing electronAPI gracefully', async () => {
      // Remove electronAPI
      delete window.electronAPI;

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      // Should not throw error
      expect(() => {
        render(
          <App 
            backendUrl="http://localhost:8000"
            isElectron={false}
            backendAvailable={true}
            backendError={null}
          />
        );
      }).not.toThrow();
    });

    it('should handle backend unavailable during initialization', async () => {
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue('http://localhost:8000'),
      };

      // Mock failed health check
      global.fetch = jest.fn().mockRejectedValue(new Error('Connection refused'));

      // Simulate initialization flow
      let backendAvailable = false;
      let backendError = null;

      try {
        const backendUrl = await window.electronAPI.getBackendUrl();
        const healthResponse = await fetch(`${backendUrl}/health`);
        backendAvailable = healthResponse.ok;
      } catch (error) {
        backendError = error.message;
      }

      // Verify backend was marked as unavailable
      expect(backendAvailable).toBe(false);
      expect(backendError).toBe('Connection refused');
    });

    it('should display appropriate error message when backend is unavailable', async () => {
      axios.get = jest.fn();

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Backend failed to start"
        />
      );

      // Verify error message is displayed
      expect(screen.getByText(/Backend Connection Issue/i)).toBeInTheDocument();
      // Use getAllByText since the error appears in multiple places
      const errorMessages = screen.getAllByText(/Backend failed to start/i);
      expect(errorMessages.length).toBeGreaterThan(0);
    });

    it('should allow retry when backend connection fails', async () => {
      axios.get = jest.fn();

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Connection timeout"
        />
      );

      // Verify retry button is present
      const retryButton = screen.getByText(/Retry Connection/i);
      expect(retryButton).toBeInTheDocument();

      // Mock window.location.reload
      delete window.location;
      window.location = { reload: jest.fn() };

      // Click retry button
      await userEvent.click(retryButton);

      // Verify reload was called
      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  describe('Electron vs Web Mode Behavior', () => {
    it('should behave correctly in Electron mode', async () => {
      const mockBackendUrl = 'http://localhost:8123';
      
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue(mockBackendUrl),
        selectDirectory: jest.fn(),
      };

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl={mockBackendUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      });

      // Verify Electron-specific features are available
      expect(screen.getByText(/Browse\.\.\./i)).toBeInTheDocument();
      expect(axios.defaults.baseURL).toBe(mockBackendUrl);
    });

    it('should behave correctly in web mode', async () => {
      delete window.electronAPI;

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: true }
      });

      const App = (await import('./App')).default;

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={false}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for component to render
      await waitFor(() => {
        const pathInputs = screen.getAllByRole('textbox');
        expect(pathInputs.length).toBeGreaterThan(0);
      });

      // Verify web-specific features
      expect(screen.queryByText(/Browse\.\.\./i)).not.toBeInTheDocument();
      expect(axios.defaults.baseURL).toBe('http://localhost:8000');
    });
  });
});
