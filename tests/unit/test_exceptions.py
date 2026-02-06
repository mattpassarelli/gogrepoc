"""Unit tests for custom exception classes."""

import pytest
from gogrepoc.core.exceptions import (
    GOGRepocError,
    AuthError,
    NetworkError,
    FileSystemError,
    VerificationError,
)


class TestGOGRepocError:
    """Tests for the base GOGRepocError exception."""
    
    def test_base_exception_inheritance(self):
        """Test that GOGRepocError inherits from Exception."""
        assert issubclass(GOGRepocError, Exception)
    
    def test_base_exception_can_be_raised(self):
        """Test that GOGRepocError can be raised and caught."""
        with pytest.raises(GOGRepocError):
            raise GOGRepocError("Test error")
    
    def test_base_exception_message(self):
        """Test that GOGRepocError preserves error message."""
        error = GOGRepocError("Test error message")
        assert str(error) == "Test error message"


class TestAuthError:
    """Tests for the AuthError exception."""
    
    def test_auth_error_inheritance(self):
        """Test that AuthError inherits from GOGRepocError."""
        assert issubclass(AuthError, GOGRepocError)
    
    def test_auth_error_without_username(self):
        """Test AuthError with only a message."""
        error = AuthError("Invalid credentials")
        assert error.message == "Invalid credentials"
        assert error.username is None
        assert str(error) == "Authentication failed: Invalid credentials"
    
    def test_auth_error_with_username(self):
        """Test AuthError with message and username."""
        error = AuthError("Invalid credentials", username="testuser")
        assert error.message == "Invalid credentials"
        assert error.username == "testuser"
        assert str(error) == "Authentication failed for user 'testuser': Invalid credentials"
    
    def test_auth_error_can_be_caught_as_gogrepoc_error(self):
        """Test that AuthError can be caught as GOGRepocError."""
        with pytest.raises(GOGRepocError):
            raise AuthError("Test error")
    
    def test_auth_error_attributes_accessible(self):
        """Test that AuthError attributes are accessible after raising."""
        try:
            raise AuthError("Token expired", username="user123")
        except AuthError as e:
            assert e.message == "Token expired"
            assert e.username == "user123"


class TestNetworkError:
    """Tests for the NetworkError exception."""
    
    def test_network_error_inheritance(self):
        """Test that NetworkError inherits from GOGRepocError."""
        assert issubclass(NetworkError, GOGRepocError)
    
    def test_network_error_minimal(self):
        """Test NetworkError with only a message."""
        error = NetworkError("Connection timeout")
        assert error.message == "Connection timeout"
        assert error.url is None
        assert error.status_code is None
        assert error.retry_count is None
        assert str(error) == "Network error: Connection timeout"
    
    def test_network_error_with_url(self):
        """Test NetworkError with message and URL."""
        error = NetworkError("Connection timeout", url="https://api.gog.com/games")
        assert error.message == "Connection timeout"
        assert error.url == "https://api.gog.com/games"
        assert "URL: https://api.gog.com/games" in str(error)
    
    def test_network_error_with_status_code(self):
        """Test NetworkError with message and status code."""
        error = NetworkError("Server error", status_code=500)
        assert error.message == "Server error"
        assert error.status_code == 500
        assert "Status code: 500" in str(error)
    
    def test_network_error_with_retry_count(self):
        """Test NetworkError with message and retry count."""
        error = NetworkError("Connection failed", retry_count=3)
        assert error.message == "Connection failed"
        assert error.retry_count == 3
        assert "Retries attempted: 3" in str(error)
    
    def test_network_error_with_all_parameters(self):
        """Test NetworkError with all parameters."""
        error = NetworkError(
            "Request failed",
            url="https://api.gog.com/download",
            status_code=503,
            retry_count=4
        )
        assert error.message == "Request failed"
        assert error.url == "https://api.gog.com/download"
        assert error.status_code == 503
        assert error.retry_count == 4
        
        error_str = str(error)
        assert "Network error: Request failed" in error_str
        assert "URL: https://api.gog.com/download" in error_str
        assert "Status code: 503" in error_str
        assert "Retries attempted: 4" in error_str
    
    def test_network_error_with_zero_retry_count(self):
        """Test NetworkError with retry_count of 0."""
        error = NetworkError("Connection failed", retry_count=0)
        assert error.retry_count == 0
        assert "Retries attempted: 0" in str(error)


class TestFileSystemError:
    """Tests for the FileSystemError exception."""
    
    def test_filesystem_error_inheritance(self):
        """Test that FileSystemError inherits from GOGRepocError."""
        assert issubclass(FileSystemError, GOGRepocError)
    
    def test_filesystem_error_minimal(self):
        """Test FileSystemError with only a message."""
        error = FileSystemError("Permission denied")
        assert error.message == "Permission denied"
        assert error.path is None
        assert error.operation is None
        assert str(error) == "File system error: Permission denied"
    
    def test_filesystem_error_with_path(self):
        """Test FileSystemError with message and path."""
        error = FileSystemError("File not found", path="/path/to/file.txt")
        assert error.message == "File not found"
        assert error.path == "/path/to/file.txt"
        assert "Path: /path/to/file.txt" in str(error)
    
    def test_filesystem_error_with_operation(self):
        """Test FileSystemError with message and operation."""
        error = FileSystemError("Operation failed", operation="write")
        assert error.message == "Operation failed"
        assert error.operation == "write"
        assert "Operation: write" in str(error)
    
    def test_filesystem_error_with_all_parameters(self):
        """Test FileSystemError with all parameters."""
        error = FileSystemError(
            "Disk full",
            path="/mnt/storage/game.bin",
            operation="write"
        )
        assert error.message == "Disk full"
        assert error.path == "/mnt/storage/game.bin"
        assert error.operation == "write"
        
        error_str = str(error)
        assert "File system error: Disk full" in error_str
        assert "Operation: write" in error_str
        assert "Path: /mnt/storage/game.bin" in error_str
    
    def test_filesystem_error_operation_ordering(self):
        """Test that operation appears before path in error message."""
        error = FileSystemError("Error", path="/test/path", operation="delete")
        error_str = str(error)
        operation_pos = error_str.find("Operation: delete")
        path_pos = error_str.find("Path: /test/path")
        assert operation_pos < path_pos


class TestVerificationError:
    """Tests for the VerificationError exception."""
    
    def test_verification_error_inheritance(self):
        """Test that VerificationError inherits from GOGRepocError."""
        assert issubclass(VerificationError, GOGRepocError)
    
    def test_verification_error_minimal(self):
        """Test VerificationError with only a message."""
        error = VerificationError("Checksum mismatch")
        assert error.message == "Checksum mismatch"
        assert error.path is None
        assert error.expected is None
        assert error.actual is None
        assert str(error) == "Verification failed: Checksum mismatch"
    
    def test_verification_error_with_path(self):
        """Test VerificationError with message and path."""
        error = VerificationError("MD5 mismatch", path="/games/installer.exe")
        assert error.message == "MD5 mismatch"
        assert error.path == "/games/installer.exe"
        assert "File: /games/installer.exe" in str(error)
    
    def test_verification_error_with_expected_only(self):
        """Test VerificationError with expected value only."""
        error = VerificationError("Missing checksum", expected="abc123")
        assert error.message == "Missing checksum"
        assert error.expected == "abc123"
        assert error.actual is None
        assert "Expected: abc123" in str(error)
    
    def test_verification_error_with_expected_and_actual(self):
        """Test VerificationError with both expected and actual values."""
        error = VerificationError(
            "MD5 mismatch",
            expected="abc123",
            actual="def456"
        )
        assert error.message == "MD5 mismatch"
        assert error.expected == "abc123"
        assert error.actual == "def456"
        assert "Expected: abc123, Actual: def456" in str(error)
    
    def test_verification_error_with_all_parameters(self):
        """Test VerificationError with all parameters."""
        error = VerificationError(
            "File size mismatch",
            path="/downloads/game.bin",
            expected="1048576",
            actual="1048500"
        )
        assert error.message == "File size mismatch"
        assert error.path == "/downloads/game.bin"
        assert error.expected == "1048576"
        assert error.actual == "1048500"
        
        error_str = str(error)
        assert "Verification failed: File size mismatch" in error_str
        assert "File: /downloads/game.bin" in error_str
        assert "Expected: 1048576, Actual: 1048500" in error_str
    
    def test_verification_error_md5_example(self):
        """Test VerificationError with realistic MD5 values."""
        error = VerificationError(
            "MD5 checksum mismatch",
            path="/games/witcher3.exe",
            expected="d41d8cd98f00b204e9800998ecf8427e",
            actual="098f6bcd4621d373cade4e832627b4f6"
        )
        error_str = str(error)
        assert "d41d8cd98f00b204e9800998ecf8427e" in error_str
        assert "098f6bcd4621d373cade4e832627b4f6" in error_str


class TestExceptionHierarchy:
    """Tests for exception hierarchy and catching behavior."""
    
    def test_all_custom_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from GOGRepocError."""
        custom_exceptions = [AuthError, NetworkError, FileSystemError, VerificationError]
        for exc_class in custom_exceptions:
            assert issubclass(exc_class, GOGRepocError)
    
    def test_catch_all_custom_exceptions_as_base(self):
        """Test that all custom exceptions can be caught as GOGRepocError."""
        exceptions_to_test = [
            AuthError("test"),
            NetworkError("test"),
            FileSystemError("test"),
            VerificationError("test"),
        ]
        
        for exc in exceptions_to_test:
            with pytest.raises(GOGRepocError):
                raise exc
    
    def test_specific_exception_catching(self):
        """Test that specific exceptions can be caught individually."""
        # Test AuthError
        with pytest.raises(AuthError) as exc_info:
            raise AuthError("auth failed")
        assert "auth failed" in str(exc_info.value)
        
        # Test NetworkError
        with pytest.raises(NetworkError) as exc_info:
            raise NetworkError("network failed")
        assert "network failed" in str(exc_info.value)
        
        # Test FileSystemError
        with pytest.raises(FileSystemError) as exc_info:
            raise FileSystemError("fs failed")
        assert "fs failed" in str(exc_info.value)
        
        # Test VerificationError
        with pytest.raises(VerificationError) as exc_info:
            raise VerificationError("verify failed")
        assert "verify failed" in str(exc_info.value)
    
    def test_exception_type_differentiation(self):
        """Test that different exception types can be distinguished."""
        try:
            raise NetworkError("network issue")
        except AuthError:
            pytest.fail("NetworkError should not be caught as AuthError")
        except NetworkError:
            pass  # Expected
        
        try:
            raise FileSystemError("fs issue")
        except VerificationError:
            pytest.fail("FileSystemError should not be caught as VerificationError")
        except FileSystemError:
            pass  # Expected
