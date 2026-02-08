"""Unit tests for backend entry point script.

Tests CLI argument parsing, server startup configuration, and
graceful shutdown handling for the Electron backend.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from backend.main import parse_args, setup_logging, main


class TestCLIArgumentParsing:
    """Tests for command-line argument parsing."""
    
    def test_default_arguments(self):
        """Test that default values are used when no arguments provided."""
        with patch.object(sys, 'argv', ['main.py']):
            args = parse_args()
            assert args.port == 8000
            assert args.host == "127.0.0.1"
    
    def test_custom_port(self):
        """Test parsing custom port argument."""
        with patch.object(sys, 'argv', ['main.py', '--port', '9000']):
            args = parse_args()
            assert args.port == 9000
            assert args.host == "127.0.0.1"
    
    def test_custom_host(self):
        """Test parsing custom host argument."""
        with patch.object(sys, 'argv', ['main.py', '--host', '0.0.0.0']):
            args = parse_args()
            assert args.port == 8000
            assert args.host == "0.0.0.0"
    
    def test_custom_host_and_port(self):
        """Test parsing both custom host and port arguments."""
        with patch.object(sys, 'argv', ['main.py', '--host', '192.168.1.1', '--port', '8080']):
            args = parse_args()
            assert args.port == 8080
            assert args.host == "192.168.1.1"
    
    def test_port_type_validation(self):
        """Test that port argument must be an integer."""
        with patch.object(sys, 'argv', ['main.py', '--port', 'invalid']):
            with pytest.raises(SystemExit):
                parse_args()


class TestLoggingConfiguration:
    """Tests for logging setup."""
    
    @patch('backend.main.logging.basicConfig')
    def test_logging_setup_called(self, mock_basic_config):
        """Test that logging is configured correctly."""
        setup_logging()
        
        # Verify basicConfig was called
        mock_basic_config.assert_called_once()
        
        # Verify logging configuration
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs['level'] == 20  # logging.INFO
        assert 'format' in call_kwargs
        assert 'handlers' in call_kwargs
        assert len(call_kwargs['handlers']) == 1


class TestServerStartup:
    """Tests for server startup with different configurations."""
    
    @patch('backend.main.uvicorn.run')
    @patch('backend.main.parse_args')
    @patch('backend.main.setup_logging')
    def test_server_starts_with_default_config(self, mock_setup_logging, mock_parse_args, mock_uvicorn_run):
        """Test server starts with default host and port."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_parse_args.return_value = mock_args
        
        # Run main
        main()
        
        # Verify logging was setup
        mock_setup_logging.assert_called_once()
        
        # Verify uvicorn.run was called with correct parameters
        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs['host'] == "127.0.0.1"
        assert call_kwargs['port'] == 8000
        assert call_kwargs['log_level'] == "info"
        assert call_kwargs['access_log'] is False
    
    @patch('backend.main.uvicorn.run')
    @patch('backend.main.parse_args')
    @patch('backend.main.setup_logging')
    def test_server_starts_with_custom_port(self, mock_setup_logging, mock_parse_args, mock_uvicorn_run):
        """Test server starts with custom port."""
        # Mock arguments with custom port
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 9000
        mock_parse_args.return_value = mock_args
        
        # Run main
        main()
        
        # Verify uvicorn.run was called with custom port
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs['port'] == 9000
    
    @patch('backend.main.uvicorn.run')
    @patch('backend.main.parse_args')
    @patch('backend.main.setup_logging')
    def test_server_starts_with_custom_host(self, mock_setup_logging, mock_parse_args, mock_uvicorn_run):
        """Test server starts with custom host."""
        # Mock arguments with custom host
        mock_args = MagicMock()
        mock_args.host = "0.0.0.0"
        mock_args.port = 8000
        mock_parse_args.return_value = mock_args
        
        # Run main
        main()
        
        # Verify uvicorn.run was called with custom host
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs['host'] == "0.0.0.0"
    
    @patch('backend.main.uvicorn.run')
    @patch('backend.main.parse_args')
    @patch('backend.main.setup_logging')
    def test_access_log_disabled(self, mock_setup_logging, mock_parse_args, mock_uvicorn_run):
        """Test that access logging is disabled to reduce noise."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_parse_args.return_value = mock_args
        
        # Run main
        main()
        
        # Verify access_log is False
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs['access_log'] is False


class TestGracefulShutdown:
    """Tests for graceful shutdown handling."""
    
    @patch('backend.main.uvicorn.run')
    @patch('backend.main.parse_args')
    @patch('backend.main.setup_logging')
    @patch('backend.main.sys.exit')
    def test_server_exits_on_exception(self, mock_exit, mock_setup_logging, mock_parse_args, mock_uvicorn_run):
        """Test that server exits gracefully when exception occurs."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_parse_args.return_value = mock_args
        
        # Make uvicorn.run raise an exception
        mock_uvicorn_run.side_effect = Exception("Server startup failed")
        
        # Run main
        main()
        
        # Verify sys.exit was called with error code
        mock_exit.assert_called_once_with(1)
    
    @patch('backend.main.uvicorn.run')
    @patch('backend.main.parse_args')
    @patch('backend.main.setup_logging')
    @patch('backend.main.sys.exit')
    def test_keyboard_interrupt_handled(self, mock_exit, mock_setup_logging, mock_parse_args, mock_uvicorn_run):
        """Test that KeyboardInterrupt is handled gracefully."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_parse_args.return_value = mock_args
        
        # Make uvicorn.run raise a generic exception (KeyboardInterrupt is special)
        mock_uvicorn_run.side_effect = RuntimeError("Server interrupted")
        
        # Run main
        main()
        
        # Verify sys.exit was called with error code
        mock_exit.assert_called_once_with(1)
