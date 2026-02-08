/**
 * Unit tests for React app initialization
 * 
 * Tests the initialization logic that detects Electron environment,
 * gets backend URL, and handles backend unavailable states.
 * 
 * Requirements: 7.2, 7.3, 7.5
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

// Mock ReactDOM
jest.mock('react-dom/client', () => ({
  createRoot: jest.fn(() => ({
    render: jest.fn(),
  })),
}));

// Mock App component
jest.mock('./App', () => {
  return function MockApp(props) {
    return (
      <div data-testid="mock-app">
        <div data-testid="backend-url">{props.backendUrl}</div>
        <div data-testid="is-electron">{props.isElectron ? 'true' : 'false'}</div>
        <div data-testid="backend-available">{props.backendAvailable ? 'true' : 'false'}</div>
        <div data-testid="backend-error">{props.backendError || 'none'}</div>
      </div>
    );
  };
});

// Mock ErrorBoundary
jest.mock('./ErrorBoundary', () => {
  return function MockErrorBoundary({ children }) {
    return <div>{children}</div>;
  };
});

describe('React App Initialization', () => {
  let originalFetch;
  let originalElectronAPI;

  beforeEach(() => {
    // Save original fetch
    originalFetch = global.fetch;
    
    // Save original electronAPI
    originalElectronAPI = window.electronAPI;
    
    // Clear mocks
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Restore original fetch
    global.fetch = originalFetch;
    
    // Restore original electronAPI
    if (originalElectronAPI) {
      window.electronAPI = originalElectronAPI;
    } else {
      delete window.electronAPI;
    }
  });

  describe('Electron Environment Detection', () => {
    test('should detect Electron environment when electronAPI is available', async () => {
      // Mock electronAPI
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue('http://localhost:8123'),
      };

      // Mock successful health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
      });

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Dynamically import to trigger initialization
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify App was rendered with correct props
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        backendUrl: 'http://localhost:8123',
        isElectron: true,
        backendAvailable: true,
        backendError: null,
      });
    });

    test('should use environment variable in standalone web mode', async () => {
      // Remove electronAPI
      delete window.electronAPI;

      // Set environment variable
      process.env.REACT_APP_API_URL = 'http://localhost:9000';

      // Mock successful health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
      });

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify App was rendered with correct props
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        backendUrl: 'http://localhost:9000',
        isElectron: false,
      });
    });

    test('should default to localhost:8000 when no environment variable set', async () => {
      // Remove electronAPI
      delete window.electronAPI;

      // Clear environment variable
      delete process.env.REACT_APP_API_URL;

      // Mock successful health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
      });

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify App was rendered with correct props
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        backendUrl: 'http://localhost:8000',
        isElectron: false,
      });
    });
  });

  describe('Backend URL Retrieval', () => {
    test('should get backend URL from electronAPI in Electron mode', async () => {
      const mockGetBackendUrl = jest.fn().mockResolvedValue('http://localhost:8456');
      
      window.electronAPI = {
        getBackendUrl: mockGetBackendUrl,
      };

      // Mock successful health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
      });

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockGetBackendUrl).toHaveBeenCalled();
      });

      // Verify backend URL was retrieved
      expect(mockGetBackendUrl).toHaveBeenCalledTimes(1);
    });

    test('should handle electronAPI.getBackendUrl errors', async () => {
      window.electronAPI = {
        getBackendUrl: jest.fn().mockRejectedValue(new Error('IPC failed')),
      };

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify App was rendered with error state
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        isElectron: true,
        backendAvailable: false,
        backendError: 'IPC failed',
      });
    });
  });

  describe('Backend Health Check', () => {
    test('should verify backend is available with health check', async () => {
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue('http://localhost:8123'),
      };

      // Mock successful health check
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
      });
      global.fetch = mockFetch;

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('http://localhost:8123/health');
      });

      // Verify backend was marked as available
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props.backendAvailable).toBe(true);
    });

    test('should handle backend health check failure', async () => {
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue('http://localhost:8123'),
      };

      // Mock failed health check
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 503,
      });

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify backend was marked as unavailable
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        backendAvailable: false,
        backendError: 'Backend returned status 503',
      });
    });

    test('should handle network errors during health check', async () => {
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue('http://localhost:8123'),
      };

      // Mock network error
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify backend was marked as unavailable
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        backendAvailable: false,
        backendError: 'Network error',
      });
    });
  });

  describe('Error Handling', () => {
    test('should render error state when initialization fails', async () => {
      // Mock initialization failure
      window.electronAPI = {
        getBackendUrl: jest.fn().mockImplementation(() => {
          throw new Error('Critical initialization error');
        }),
      };

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      
      // Import should not throw
      await expect(import('./index.js')).resolves.toBeDefined();

      // Wait for error state to be rendered
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify error state was rendered (second render call)
      expect(mockRoot.render).toHaveBeenCalledTimes(1);
    });
  });

  describe('Backend Unavailable State', () => {
    test('should pass backendAvailable=false when backend is down', async () => {
      delete window.electronAPI;

      // Mock failed health check
      global.fetch = jest.fn().mockRejectedValue(new Error('Connection refused'));

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify App was rendered with unavailable state
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props).toMatchObject({
        backendAvailable: false,
        backendError: 'Connection refused',
      });
    });

    test('should pass backendError message to App component', async () => {
      window.electronAPI = {
        getBackendUrl: jest.fn().mockResolvedValue('http://localhost:8123'),
      };

      // Mock health check with specific error
      global.fetch = jest.fn().mockRejectedValue(new Error('Timeout'));

      // Import and run initialization
      const { default: ReactDOM } = require('react-dom/client');
      const mockRoot = { render: jest.fn() };
      ReactDOM.createRoot.mockReturnValue(mockRoot);

      // Clear module cache and re-import
      jest.resetModules();
      await import('./index.js');

      // Wait for async initialization
      await waitFor(() => {
        expect(mockRoot.render).toHaveBeenCalled();
      });

      // Verify error message was passed
      const renderCall = mockRoot.render.mock.calls[0][0];
      expect(renderCall.props.children.props.children.props.backendError).toBe('Timeout');
    });
  });
});
