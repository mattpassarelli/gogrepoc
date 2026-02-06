"""Custom exception classes for GOGRepoc.

This module defines custom exceptions for different error types that can occur
throughout the application, providing helpful error messages and context.
"""


class GOGRepocError(Exception):
    """Base exception class for all GOGRepoc errors.
    
    All custom exceptions in the application should inherit from this class
    to allow for easy catching of all application-specific errors.
    """
    pass


class AuthError(GOGRepocError):
    """Exception raised for authentication failures.
    
    This exception is raised when authentication with GOG fails, including:
    - Invalid credentials
    - Expired tokens
    - Two-factor authentication failures
    - Token refresh failures
    
    Attributes:
        message: Explanation of the authentication error
        username: Username that failed authentication (optional)
    """
    
    def __init__(self, message: str, username: str | None = None):
        """Initialize AuthError with message and optional username.
        
        Args:
            message: Explanation of the authentication error
            username: Username that failed authentication (optional)
        """
        self.message = message
        self.username = username
        
        if username:
            super().__init__(f"Authentication failed for user '{username}': {message}")
        else:
            super().__init__(f"Authentication failed: {message}")


class NetworkError(GOGRepocError):
    """Exception raised for network-related issues.
    
    This exception is raised when network operations fail, including:
    - Connection timeouts
    - DNS resolution failures
    - HTTP errors (4xx, 5xx)
    - Network unreachable
    - SSL/TLS errors
    
    Attributes:
        message: Explanation of the network error
        url: URL that caused the error (optional)
        status_code: HTTP status code if applicable (optional)
        retry_count: Number of retries attempted (optional)
    """
    
    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        retry_count: int | None = None
    ):
        """Initialize NetworkError with message and optional context.
        
        Args:
            message: Explanation of the network error
            url: URL that caused the error (optional)
            status_code: HTTP status code if applicable (optional)
            retry_count: Number of retries attempted (optional)
        """
        self.message = message
        self.url = url
        self.status_code = status_code
        self.retry_count = retry_count
        
        error_parts = [f"Network error: {message}"]
        
        if url:
            error_parts.append(f"URL: {url}")
        
        if status_code:
            error_parts.append(f"Status code: {status_code}")
        
        if retry_count is not None:
            error_parts.append(f"Retries attempted: {retry_count}")
        
        super().__init__(" | ".join(error_parts))


class FileSystemError(GOGRepocError):
    """Exception raised for file operation failures.
    
    This exception is raised when file system operations fail, including:
    - File not found
    - Permission denied
    - Disk full
    - Invalid path
    - File already exists
    - Directory creation failures
    
    Attributes:
        message: Explanation of the file system error
        path: Path that caused the error (optional)
        operation: Operation that failed (e.g., 'read', 'write', 'delete') (optional)
    """
    
    def __init__(
        self,
        message: str,
        path: str | None = None,
        operation: str | None = None
    ):
        """Initialize FileSystemError with message and optional context.
        
        Args:
            message: Explanation of the file system error
            path: Path that caused the error (optional)
            operation: Operation that failed (optional)
        """
        self.message = message
        self.path = path
        self.operation = operation
        
        error_parts = [f"File system error: {message}"]
        
        if operation:
            error_parts.append(f"Operation: {operation}")
        
        if path:
            error_parts.append(f"Path: {path}")
        
        super().__init__(" | ".join(error_parts))


class VerificationError(GOGRepocError):
    """Exception raised for file verification failures.
    
    This exception is raised when file verification fails, including:
    - MD5 checksum mismatch
    - File size mismatch
    - Corrupted file
    - Incomplete download
    - Invalid archive
    
    Attributes:
        message: Explanation of the verification error
        path: Path to the file that failed verification (optional)
        expected: Expected value (e.g., MD5 hash, file size) (optional)
        actual: Actual value found (optional)
    """
    
    def __init__(
        self,
        message: str,
        path: str | None = None,
        expected: str | None = None,
        actual: str | None = None
    ):
        """Initialize VerificationError with message and optional context.
        
        Args:
            message: Explanation of the verification error
            path: Path to the file that failed verification (optional)
            expected: Expected value (e.g., MD5 hash, file size) (optional)
            actual: Actual value found (optional)
        """
        self.message = message
        self.path = path
        self.expected = expected
        self.actual = actual
        
        error_parts = [f"Verification failed: {message}"]
        
        if path:
            error_parts.append(f"File: {path}")
        
        if expected and actual:
            error_parts.append(f"Expected: {expected}, Actual: {actual}")
        elif expected:
            error_parts.append(f"Expected: {expected}")
        
        super().__init__(" | ".join(error_parts))
