import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './ErrorBoundary';
import 'bootstrap/dist/css/bootstrap.min.css';

/**
 * Initialize the React application
 * 
 * Detects if running in Electron environment and gets the backend URL
 * from the main process. Falls back to environment variable or localhost
 * for standalone web mode.
 * 
 * Requirements: 7.2, 7.3, 7.5
 */
async function initializeApp() {
  let backendUrl;
  let isElectron = false;
  let backendAvailable = false;
  let backendError = null;

  // Detect Electron environment
  if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
    isElectron = true;
    try {
      // Get backend URL from Electron main process
      backendUrl = await window.electronAPI.getBackendUrl();
      
      // Verify backend is available
      const healthResponse = await fetch(`${backendUrl}/health`);
      if (healthResponse.ok) {
        backendAvailable = true;
      } else {
        backendError = `Backend returned status ${healthResponse.status}`;
      }
    } catch (error) {
      backendError = error.message || 'Failed to connect to backend';
    }
  } else {
    // Standalone web mode - use environment variable or default
    backendUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    
    // Try to verify backend is available (optional in web mode)
    try {
      const healthResponse = await fetch(`${backendUrl}/health`);
      backendAvailable = healthResponse.ok;
    } catch (error) {
      // In web mode, we'll still render but show connection error in UI
      backendError = error.message || 'Backend not available';
    }
  }

  const root = ReactDOM.createRoot(document.getElementById('root'));
  
  // Render app with backend configuration
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <App 
          backendUrl={backendUrl}
          isElectron={isElectron}
          backendAvailable={backendAvailable}
          backendError={backendError}
        />
      </ErrorBoundary>
    </React.StrictMode>
  );
}

// Start the application
initializeApp().catch(error => {
  console.error('Failed to initialize application:', error);
  
  // Render error state
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(
    <React.StrictMode>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: '#212529',
        color: '#e9ecef',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h1>Application Initialization Failed</h1>
        <p style={{ marginTop: '20px', maxWidth: '600px' }}>
          {error.message || 'An unexpected error occurred during initialization.'}
        </p>
        <button 
          onClick={() => window.location.reload()}
          style={{
            marginTop: '20px',
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#0d6efd',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    </React.StrictMode>
  );
});
