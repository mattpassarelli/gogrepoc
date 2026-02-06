"""Unit tests for hashing utilities."""

import pytest
from pathlib import Path
from gogrepoc.utils.hashing import calculate_md5


def test_calculate_md5_with_known_value(tmp_path):
    """Test MD5 calculation with a known hash value."""
    # Create a test file with known content
    test_file = tmp_path / "test.txt"
    test_content = b"Hello, World!"
    test_file.write_bytes(test_content)
    
    # Known MD5 hash for "Hello, World!"
    expected_md5 = "65a8e27d8879283831b664bd8b7f0ad4"
    
    result = calculate_md5(test_file)
    
    assert result == expected_md5


def test_calculate_md5_empty_file(tmp_path):
    """Test MD5 calculation for an empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")
    
    # Known MD5 hash for empty file
    expected_md5 = "d41d8cd98f00b204e9800998ecf8427e"
    
    result = calculate_md5(test_file)
    
    assert result == expected_md5


def test_calculate_md5_large_file(tmp_path):
    """Test MD5 calculation with chunked reading for large file."""
    test_file = tmp_path / "large.bin"
    
    # Create a file larger than default chunk size (8KB)
    # Write 100KB of data
    data = b"x" * (100 * 1024)
    test_file.write_bytes(data)
    
    result = calculate_md5(test_file)
    
    # Verify it returns a valid MD5 hash (32 hex characters)
    assert len(result) == 32
    assert all(c in "0123456789abcdef" for c in result)


def test_calculate_md5_with_string_path(tmp_path):
    """Test MD5 calculation accepts string path."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content")
    
    # Pass string path instead of Path object
    result = calculate_md5(str(test_file))
    
    assert len(result) == 32


def test_calculate_md5_file_not_found():
    """Test MD5 calculation raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        calculate_md5(Path("/nonexistent/file.txt"))


def test_calculate_md5_custom_chunk_size(tmp_path):
    """Test MD5 calculation with custom chunk size."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test data")
    
    # Use very small chunk size
    result = calculate_md5(test_file, chunk_size=2)
    
    # Should still produce correct hash
    assert len(result) == 32
