/**
 * Integration tests for App component with backend configuration
 * 
 * Tests the App component's handling of backend URL, Electron environment,
 * and backend unavailable states.
 * 
 * Requirements: 7.2, 7.3, 7.5
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import App from './App';

// Mock axios
jest.mock('axios');

describe('App Component - Backend Integration', () => {
  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Reset axios defaults
    axios.defaults = {};
    
    // Mock localStorage
    Storage.prototype.getItem = jest.fn();
    Storage.prototype.setItem = jest.fn();
  });

  describe('Backend URL Configuration', () => {
    test('should configure axios with provided backend URL', () => {
      const backendUrl = 'http://localhost:8456';
      
      render(
        <App 
          backendUrl={backendUrl}
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify axios was configured with the backend URL
      expect(axios.defaults.baseURL).toBe(backendUrl);
      expect(axios.defaults.withCredentials).toBe(true);
    });

    test('should update axios configuration when backend URL changes', () => {
      const { rerender } = render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      expect(axios.defaults.baseURL).toBe('http://localhost:8000');

      // Update backend URL
      rerender(
        <App 
          backendUrl="http://localhost:9000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      expect(axios.defaults.baseURL).toBe('http://localhost:9000');
    });

    test('should not configure axios when backend URL is not provided', () => {
      render(
        <App 
          backendUrl={null}
          isElectron={false}
          backendAvailable={false}
          backendError="Backend not available"
        />
      );

      // Verify axios was not configured
      expect(axios.defaults.baseURL).toBeUndefined();
    });
  });

  describe('Backend Unavailable State', () => {
    test('should display warning when backend is unavailable in Electron mode', () => {
      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Connection refused"
        />
      );

      // Verify warning is displayed
      expect(screen.getByText(/Backend Connection Issue/i)).toBeInTheDocument();
      expect(screen.getByText(/The application backend is starting up or unavailable/i)).toBeInTheDocument();
      expect(screen.getByText(/Connection refused/i)).toBeInTheDocument();
    });

    test('should display warning when backend is unavailable in web mode', () => {
      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={false}
          backendAvailable={false}
          backendError="Network error"
        />
      );

      // Verify warning is displayed with web-specific message
      expect(screen.getByText(/Backend Connection Issue/i)).toBeInTheDocument();
      expect(screen.getByText(/Cannot connect to the backend server/i)).toBeInTheDocument();
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    });

    test('should show retry button when backend is unavailable', () => {
      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Timeout"
        />
      );

      // Verify retry button is present
      const retryButton = screen.getByText(/Retry Connection/i);
      expect(retryButton).toBeInTheDocument();
    });

    test('should hide login form when backend is unavailable', () => {
      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Backend down"
        />
      );

      // Verify login form is not displayed
      expect(screen.queryByLabelText(/GOG Email/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/Password/i)).not.toBeInTheDocument();
    });

    test('should not check auth when backend is unavailable', () => {
      axios.get = jest.fn();

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Backend unavailable"
        />
      );

      // Verify auth check was not called
      expect(axios.get).not.toHaveBeenCalledWith('/api/check-auth');
    });

    test('should display backend error in error state', () => {
      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Port 8000 already in use"
        />
      );

      // Verify error message is displayed
      expect(screen.getByText(/Backend unavailable: Port 8000 already in use/i)).toBeInTheDocument();
    });
  });

  describe('Backend Available State', () => {
    test('should check auth when backend is available', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Wait for auth check
      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith('/api/check-auth');
      });
    });

    test('should show login form when backend is available and not authenticated', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

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
        expect(screen.getByLabelText(/GOG Email/i)).toBeInTheDocument();
      });

      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Login/i })).toBeInTheDocument();
    });

    test('should not display backend warning when backend is available', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify warning is not displayed
      expect(screen.queryByText(/Backend Connection Issue/i)).not.toBeInTheDocument();
    });
  });

  describe('Electron vs Web Mode', () => {
    test('should work correctly in Electron mode', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      render(
        <App 
          backendUrl="http://localhost:8123"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify axios is configured
      expect(axios.defaults.baseURL).toBe('http://localhost:8123');

      // Verify auth check is called
      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith('/api/check-auth');
      });
    });

    test('should work correctly in web mode', async () => {
      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={false}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify axios is configured
      expect(axios.defaults.baseURL).toBe('http://localhost:8000');

      // Verify auth check is called
      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith('/api/check-auth');
      });
    });
  });

  describe('Settings Persistence', () => {
    test('should load settings from localStorage on mount', () => {
      Storage.prototype.getItem = jest.fn((key) => {
        const settings = {
          'savedir': '/custom/path',
          'compressDownloads': 'true',
          'filterOS': 'windows',
          'filterLang': 'en'
        };
        return settings[key];
      });

      axios.get = jest.fn().mockResolvedValue({
        data: { authenticated: false }
      });

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={true}
          backendError={null}
        />
      );

      // Verify settings were loaded
      expect(localStorage.getItem).toHaveBeenCalledWith('savedir');
      expect(localStorage.getItem).toHaveBeenCalledWith('compressDownloads');
      expect(localStorage.getItem).toHaveBeenCalledWith('filterOS');
      expect(localStorage.getItem).toHaveBeenCalledWith('filterLang');
    });

    test('should load settings even when backend is unavailable', () => {
      Storage.prototype.getItem = jest.fn((key) => {
        const settings = {
          'savedir': '/custom/path',
        };
        return settings[key];
      });

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Backend down"
        />
      );

      // Verify settings were loaded
      expect(localStorage.getItem).toHaveBeenCalledWith('savedir');
    });
  });

  describe('Error Display', () => {
    test('should display backend error alongside other errors', async () => {
      axios.get = jest.fn().mockRejectedValue({
        response: { data: { detail: 'Auth check failed' } }
      });

      render(
        <App 
          backendUrl="http://localhost:8000"
          isElectron={true}
          backendAvailable={false}
          backendError="Connection timeout"
        />
      );

      // Verify both errors are displayed
      expect(screen.getByText(/Backend unavailable: Connection timeout/i)).toBeInTheDocument();
      expect(screen.getByText(/Backend Connection Issue/i)).toBeInTheDocument();
    });
  });
});
