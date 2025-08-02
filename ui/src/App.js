import React, { useState, useEffect } from 'react';
import { Container, Form, Button, Alert, ListGroup } from 'react-bootstrap';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [games, setGames] = useState([]);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check authentication and load games list on component mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await axios.get('/check-auth');
      if (response.data.isAuthenticated) {
        setIsAuthenticated(true);
        fetchGames();
      }
    } catch (err) {
      setError('Not authenticated. Please login.');
      setIsAuthenticated(false);
    }
  };

  const fetchGames = async () => {
    try {
      const response = await axios.get('/manifest');
      setGames(response.data.games);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load games');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('/login', { username, password });
      setMessage(response.data.message);
      setError(null);
      // After successful login, check auth status and fetch games
      await checkAuth();
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  const handleUpdate = async () => {
    try {
      setMessage('Updating game list...');
      const response = await axios.post('/update', {
        os_list: ['windows'], // You might want to make this configurable
        lang_list: ['en'],
      });
      setMessage(response.data.message);
      fetchGames(); // Refresh the games list
    } catch (err) {
      setError(err.response?.data?.detail || 'Update failed');
    }
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const response = await axios.post('/download', {
        savedir: 'C:/Games/GOG', // You might want to make this configurable
        os_list: ['windows'],
        lang_list: ['en'],
      });
      setMessage(response.data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Container className="mt-5">
      <h1>GOG Repo Manager</h1>
      
      {error && <Alert variant="danger">{error}</Alert>}
      {message && <Alert variant="success">{message}</Alert>}

      {!isAuthenticated ? (
        <Form onSubmit={handleLogin} className="mb-4">
          <Form.Group className="mb-3">
            <Form.Label>Username</Form.Label>
            <Form.Control
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Password</Form.Label>
            <Form.Control
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Form.Group>

          <Button type="submit">Login</Button>
        </Form>
      ) : (
        <div className="d-flex gap-2 mb-4">
          <Button onClick={handleUpdate} variant="info">Update List</Button>
          <Button 
            onClick={handleDownload} 
            variant="success"
            disabled={downloading}
          >
            {downloading ? 'Downloading...' : 'Download Games'}
          </Button>
        </div>
      )}

      <h2>Games List</h2>
      <ListGroup style={{ maxHeight: '400px', overflow: 'auto' }}>
        {games.map((game) => (
          <ListGroup.Item key={game.id}>
            {game.title}
          </ListGroup.Item>
        ))}
      </ListGroup>
    </Container>
  );
}

export default App;
