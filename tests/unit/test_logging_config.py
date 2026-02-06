"""Unit tests for logging configuration utilities."""

import pytest
import logging
from pathlib import Path
from gogrepoc.utils.logging_config import setup_logging, SensitiveDataFilter


def test_setup_logging_default_level():
    """Test logging setup with default INFO level."""
    setup_logging()
    
    root_logger = logging.getLogger()
    
    # Verify INFO level is set
    assert root_logger.level == logging.INFO
    
    # Verify handlers are configured
    assert len(root_logger.handlers) > 0


def test_setup_logging_debug_level():
    """Test logging setup with DEBUG level."""
    setup_logging(level="DEBUG")
    
    root_logger = logging.getLogger()
    
    # Verify DEBUG level is set
    assert root_logger.level == logging.DEBUG


def test_setup_logging_with_file(tmp_path):
    """Test logging setup with file output."""
    log_file = tmp_path / "test.log"
    
    setup_logging(level="INFO", log_file=log_file)
    
    logger = logging.getLogger("test")
    logger.info("Test file message")
    
    # Verify log file was created and contains message
    assert log_file.exists()
    log_content = log_file.read_text()
    assert "Test file message" in log_content


def test_setup_logging_creates_log_directory(tmp_path):
    """Test logging setup creates parent directories for log file."""
    log_file = tmp_path / "logs" / "nested" / "test.log"
    
    setup_logging(level="INFO", log_file=log_file)
    
    logger = logging.getLogger("test")
    logger.info("Test message")
    
    # Verify nested directories were created
    assert log_file.exists()
    assert log_file.parent.exists()


def test_setup_logging_custom_format():
    """Test logging setup with custom format string."""
    custom_format = "%(levelname)s - %(message)s"
    
    setup_logging(level="INFO", format_string=custom_format)
    
    root_logger = logging.getLogger()
    
    # Verify handler has custom formatter
    assert len(root_logger.handlers) > 0
    handler = root_logger.handlers[0]
    assert handler.formatter is not None


def test_setup_logging_no_console(tmp_path):
    """Test logging setup without console output."""
    log_file = tmp_path / "test.log"
    
    setup_logging(level="INFO", log_file=log_file, include_console=False)
    
    logger = logging.getLogger("test")
    
    # Verify only file handler is present
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], logging.FileHandler)


def test_setup_logging_removes_existing_handlers():
    """Test that setup_logging removes existing handlers."""
    # Add a handler
    logger = logging.getLogger()
    initial_handler = logging.StreamHandler()
    logger.addHandler(initial_handler)
    
    initial_count = len(logger.handlers)
    
    # Setup logging should clear handlers
    setup_logging(level="INFO")
    
    # Should have new handlers, not the old one
    assert initial_handler not in logger.handlers


def test_setup_logging_integer_level():
    """Test logging setup with integer level."""
    setup_logging(level=logging.WARNING)
    
    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING


def test_sensitive_data_filter_blocks_password():
    """Test that sensitive data filter sanitizes password mentions."""
    filter_obj = SensitiveDataFilter()
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="User password is secret123",
        args=(),
        exc_info=None
    )
    
    result = filter_obj.filter(record)
    
    # Filter should return True but sanitize message
    assert result is True
    assert "[REDACTED]" in record.msg


def test_sensitive_data_filter_blocks_token():
    """Test that sensitive data filter sanitizes token mentions."""
    filter_obj = SensitiveDataFilter()
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Auth token: abc123",
        args=(),
        exc_info=None
    )
    
    result = filter_obj.filter(record)
    
    assert result is True
    assert "[REDACTED]" in record.msg


def test_sensitive_data_filter_allows_normal_messages():
    """Test that sensitive data filter allows normal messages."""
    filter_obj = SensitiveDataFilter()
    
    original_msg = "Downloading file game.zip"
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=original_msg,
        args=(),
        exc_info=None
    )
    
    result = filter_obj.filter(record)
    
    assert result is True
    assert record.msg == original_msg


def test_setup_logging_applies_sensitive_filter():
    """Test that setup_logging applies sensitive data filter."""
    setup_logging(level="INFO")
    
    root_logger = logging.getLogger()
    
    # Verify sensitive filter is applied
    filters = root_logger.filters
    assert len(filters) > 0
    assert any(isinstance(f, SensitiveDataFilter) for f in filters)


def test_setup_logging_with_path_object(tmp_path):
    """Test logging setup accepts Path object for log file."""
    log_file = tmp_path / "test.log"
    
    setup_logging(level="INFO", log_file=log_file)
    
    logger = logging.getLogger("test")
    logger.info("Path object test")
    
    assert log_file.exists()
