"""Logging configuration utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent logging of sensitive information."""
    
    SENSITIVE_KEYWORDS = [
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "auth",
        "credential",
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records that may contain sensitive data.
        
        Args:
            record: Log record to filter
            
        Returns:
            True if record should be logged, False otherwise
        """
        message = record.getMessage().lower()
        
        # Check if any sensitive keyword appears in the message
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in message:
                # Allow the log but sanitize the message
                record.msg = self._sanitize_message(str(record.msg))
                record.args = ()
                break
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Replace sensitive data patterns with [REDACTED]."""
        # This is a simple implementation - could be enhanced with regex patterns
        return message.replace("password", "[REDACTED]").replace("token", "[REDACTED]")


def setup_logging(
    level: str | int = logging.INFO,
    log_file: Optional[Path | str] = None,
    format_string: Optional[str] = None,
    include_console: bool = True
) -> None:
    """
    Configure Python logging with console and optional file output.
    
    Args:
        level: Logging level (e.g., logging.INFO, "INFO", "DEBUG")
        log_file: Optional path to log file for file output
        format_string: Optional custom format string
        include_console: Whether to include console output (default True)
        
    Example:
        >>> setup_logging(level="DEBUG", log_file="app.log")
        >>> setup_logging(level=logging.WARNING)
    """
    # Convert string level to logging constant if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Default format with timestamp, level, module, and message
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add sensitive data filter to root logger
    sensitive_filter = SensitiveDataFilter()
    root_logger.addFilter(sensitive_filter)
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file = Path(log_file)
        
        # Create parent directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log initial message
    root_logger.info(f"Logging configured at level {logging.getLevelName(level)}")
    if log_file:
        root_logger.info(f"Logging to file: {log_file}")
