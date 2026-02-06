import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import App from './App';

// Mock axios
jest.mock('axios');

describe('App Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    
    // Mock localStorage
    Storage.prototype.getItem = jest.fn();
    Storage.prototype.setItem = jest.fn();
    
    // Mock axios defaults
    axios.defaults = { baseURL: '', withCredentials: true };
  });

  describe('Authentication', () => {
    test('renders login form when not authenticated', async () => {
      axios.get.mockRejectedValue({ response: { data: { detail: 'Not authenticated' } } });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/GOG Email/i)).toBeInTheDocument();
        expect(screen.getByText(/Password/i)).toBeInTheDocument();
      });
    });

    test('handles successful login', async () => {
      axios.get.mockResolvedValueOnce({ data: { authenticated: false } });
      axios.post.mockResolvedValueOnce({ 
        data: { success: true, message: 'Login successful', authenticated: true } 
      });
      axios.get.mockResolvedValueOnce({ data: { authenticated: true } });
      axios.get.mockResolvedValueOnce({ data: { games: [], total_count: 0 } });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/GOG Email/i)).toBeInTheDocument();
      });
      
      fireEvent.change(screen.getByLabelText(/GOG Email/i), { 
        target: { value: 'test@example.com' } 
      });
      fireEvent.change(screen.getByLabelText(/Password/i), { 
        target: { value: 'password123' } 
      });
      fireEvent.click(screen.getByRole('button', { name: /Login/i }));
      
      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/api/login', {
          username: 'test@example.com',
          password: 'password123'
        });
      });
    });

    test('displays error message on failed login', async () => {
      axios.get.mockRejectedValue({ response: { data: { detail: 'Not authenticated' } } });
      axios.post.mockRejectedValue({ 
        response: { data: { detail: 'Invalid credentials' } } 
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/GOG Email/i)).toBeInTheDocument();
      });
      
      fireEvent.change(screen.getByLabelText(/GOG Email/i), { 
        target: { value: 'test@example.com' } 
      });
      fireEvent.change(screen.getByLabelText(/Password/i), { 
        target: { value: 'wrongpassword' } 
      });
      fireEvent.click(screen.getByRole('button', { name: /Login/i }));
      
      await waitFor(() => {
        expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
      });
    });
  });

  describe('Game List', () => {
    beforeEach(() => {
      // Mock authenticated state
      axios.get.mockImplementation((url) => {
        if (url === '/api/check-auth') {
          return Promise.resolve({ data: { authenticated: true } });
        }
        if (url === '/api/manifest') {
          return Promise.resolve({
            data: {
              games: [
                { id: 1, title: 'Test Game 1', downloads: [], extras: [], serials: {} },
                { id: 2, title: 'Test Game 2', downloads: [], extras: [], serials: {} },
              ],
              total_count: 2
            }
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    test('displays games list when authenticated', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game 1')).toBeInTheDocument();
        expect(screen.getByText('Test Game 2')).toBeInTheDocument();
      });
    });

    test('filters games by search term', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game 1')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText(/Search by title/i);
      fireEvent.change(searchInput, { target: { value: 'Game 1' } });
      
      await waitFor(() => {
        expect(screen.getByText('Test Game 1')).toBeInTheDocument();
        expect(screen.queryByText('Test Game 2')).not.toBeInTheDocument();
      });
    });

    test('moves games to download queue', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game 1')).toBeInTheDocument();
      });
      
      // Select a game
      fireEvent.click(screen.getByText('Test Game 1'));
      
      // Move to download queue
      const moveButton = screen.getAllByRole('button').find(btn => btn.textContent === '>>');
      fireEvent.click(moveButton);
      
      // Check game is in download queue
      await waitFor(() => {
        const downloadQueue = screen.getByText(/Games Queue/i).parentElement;
        expect(downloadQueue).toHaveTextContent('Test Game 1');
      });
    });
  });

  describe('Download Operations', () => {
    beforeEach(() => {
      axios.get.mockImplementation((url) => {
        if (url === '/api/check-auth') {
          return Promise.resolve({ data: { authenticated: true } });
        }
        if (url === '/api/manifest') {
          return Promise.resolve({
            data: {
              games: [
                { 
                  id: 1, 
                  title: 'Test Game', 
                  downloads: [{ size: 1000000, os_type: 'windows', lang: 'en' }], 
                  extras: [], 
                  serials: {} 
                },
              ],
              total_count: 1
            }
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    test('starts download with progress tracking', async () => {
      axios.post.mockResolvedValue({
        data: { success: true, task_id: 'test-task-123' }
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });
      
      // Select and move game to download queue
      fireEvent.click(screen.getByText('Test Game'));
      const moveButton = screen.getAllByRole('button').find(btn => btn.textContent === '>>');
      fireEvent.click(moveButton);
      
      // Click download button
      const downloadButton = screen.getByRole('button', { name: /Download Games/i });
      fireEvent.click(downloadButton);
      
      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/api/download', expect.objectContaining({
          game_ids: [1]
        }));
      });
    });

    test('displays download size and time estimate', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });
      
      // Select and move game to download queue
      fireEvent.click(screen.getByText('Test Game'));
      const moveButton = screen.getAllByRole('button').find(btn => btn.textContent === '>>');
      fireEvent.click(moveButton);
      
      // Check for size and time estimate
      await waitFor(() => {
        expect(screen.getByText(/Total Size:/i)).toBeInTheDocument();
        expect(screen.getByText(/Est\. Time:/i)).toBeInTheDocument();
      });
    });
  });

  describe('Update Operations', () => {
    beforeEach(() => {
      axios.get.mockImplementation((url) => {
        if (url === '/api/check-auth') {
          return Promise.resolve({ data: { authenticated: true } });
        }
        if (url === '/api/manifest') {
          return Promise.resolve({
            data: { games: [], total_count: 0 }
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    test('updates game list', async () => {
      axios.post.mockResolvedValue({
        data: { success: true, message: 'Updated 5 games' }
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Update List/i })).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByRole('button', { name: /Update List/i }));
      
      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/api/update', expect.any(Object));
        expect(screen.getByText(/Updated 5 games/i)).toBeInTheDocument();
      });
    });

    test('shows loading state during update', async () => {
      axios.post.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)));
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Update List/i })).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByRole('button', { name: /Update List/i }));
      
      await waitFor(() => {
        expect(screen.getByText(/Updating\.\.\./i)).toBeInTheDocument();
      });
    });
  });

  describe('Settings Persistence', () => {
    test('loads settings from localStorage on mount', () => {
      Storage.prototype.getItem = jest.fn((key) => {
        if (key === 'savedir') return '/custom/path';
        if (key === 'compressDownloads') return 'true';
        return null;
      });
      
      axios.get.mockRejectedValue({ response: { data: { detail: 'Not authenticated' } } });
      
      render(<App />);
      
      expect(localStorage.getItem).toHaveBeenCalledWith('savedir');
      expect(localStorage.getItem).toHaveBeenCalledWith('compressDownloads');
    });

    test('saves settings to localStorage on change', async () => {
      axios.get.mockImplementation((url) => {
        if (url === '/api/check-auth') {
          return Promise.resolve({ data: { authenticated: true } });
        }
        if (url === '/api/manifest') {
          return Promise.resolve({ data: { games: [], total_count: 0 } });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Enter download path/i)).toBeInTheDocument();
      });
      
      const pathInput = screen.getByPlaceholderText(/Enter download path/i);
      fireEvent.change(pathInput, { target: { value: '/new/path' } });
      
      await waitFor(() => {
        expect(localStorage.setItem).toHaveBeenCalledWith('savedir', '/new/path');
      });
    });
  });

  describe('Game Details Modal', () => {
    beforeEach(() => {
      axios.get.mockImplementation((url) => {
        if (url === '/api/check-auth') {
          return Promise.resolve({ data: { authenticated: true } });
        }
        if (url === '/api/manifest') {
          return Promise.resolve({
            data: {
              games: [
                { 
                  id: 1, 
                  title: 'Test Game',
                  long_title: 'Test Game Full Title',
                  image_url: 'http://example.com/image.jpg',
                  store_url: 'http://gog.com/game/test',
                  changelog: 'Version 1.0 - Initial release',
                  downloads: [
                    { name: 'Installer', size: 1000000, os_type: 'windows', lang: 'en' }
                  ],
                  extras: [
                    { name: 'Manual', size: 50000, desc: 'PDF Manual' }
                  ],
                  serials: { 'Serial': 'XXXX-XXXX-XXXX' }
                },
              ],
              total_count: 1
            }
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    test('opens game details modal on double-click', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });
      
      fireEvent.doubleClick(screen.getByText('Test Game'));
      
      await waitFor(() => {
        expect(screen.getByText('Test Game Full Title')).toBeInTheDocument();
        expect(screen.getByText(/Changelog:/i)).toBeInTheDocument();
        expect(screen.getByText(/Available Downloads/i)).toBeInTheDocument();
      });
    });

    test('closes game details modal', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });
      
      fireEvent.doubleClick(screen.getByText('Test Game'));
      
      await waitFor(() => {
        expect(screen.getByText('Test Game Full Title')).toBeInTheDocument();
      });
      
      const closeButton = screen.getByRole('button', { name: /Close/i });
      fireEvent.click(closeButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Test Game Full Title')).not.toBeInTheDocument();
      });
    });
  });
});
