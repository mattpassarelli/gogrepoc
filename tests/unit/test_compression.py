"""Unit tests for compression utilities."""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from gogrepoc.utils.compression import (
    compress_file,
    decompress_file,
    CompressionError,
    _find_7zip
)


def test_find_7zip_when_available():
    """Test finding 7zip when it's available in PATH."""
    with patch('shutil.which') as mock_which:
        mock_which.side_effect = lambda cmd: cmd if cmd == '7z' else None
        
        result = _find_7zip()
        
        assert result == '7z'


def test_find_7zip_when_not_available():
    """Test finding 7zip when it's not available."""
    with patch('shutil.which', return_value=None):
        result = _find_7zip()
        
        assert result is None


def test_compress_file_success(tmp_path):
    """Test successful file compression."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    archive_path = tmp_path / "test.7z"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr='')
            
            compress_file(test_file, archive_path)
            
            # Verify subprocess was called with correct arguments
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == '7z'
            assert args[1] == 'a'
            assert '-mx=5' in args


def test_compress_file_7zip_not_installed(tmp_path):
    """Test compression fails gracefully when 7zip is not installed."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    archive_path = tmp_path / "test.7z"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value=None):
        with pytest.raises(CompressionError, match="7zip is not installed"):
            compress_file(test_file, archive_path)


def test_compress_file_not_found():
    """Test compression fails when input file doesn't exist."""
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with pytest.raises(FileNotFoundError):
            compress_file(Path("/nonexistent/file.txt"), Path("/tmp/archive.7z"))


def test_compress_file_custom_compression_level(tmp_path):
    """Test compression with custom compression level."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    archive_path = tmp_path / "test.7z"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr='')
            
            compress_file(test_file, archive_path, compression_level=9)
            
            args = mock_run.call_args[0][0]
            assert '-mx=9' in args


def test_compress_file_subprocess_error(tmp_path):
    """Test compression handles subprocess errors."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    archive_path = tmp_path / "test.7z"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with patch('subprocess.run') as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.CalledProcessError(1, '7z', stderr='Error')
            
            with pytest.raises(CompressionError, match="Compression failed"):
                compress_file(test_file, archive_path)


def test_decompress_file_success(tmp_path):
    """Test successful file decompression."""
    archive_path = tmp_path / "test.7z"
    archive_path.write_bytes(b"fake archive")
    dest_dir = tmp_path / "extracted"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr='')
            
            decompress_file(archive_path, dest_dir)
            
            # Verify subprocess was called with correct arguments
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == '7z'
            assert args[1] == 'x'
            assert str(archive_path) in args


def test_decompress_file_7zip_not_installed(tmp_path):
    """Test decompression fails gracefully when 7zip is not installed."""
    archive_path = tmp_path / "test.7z"
    archive_path.write_bytes(b"fake archive")
    dest_dir = tmp_path / "extracted"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value=None):
        with pytest.raises(CompressionError, match="7zip is not installed"):
            decompress_file(archive_path, dest_dir)


def test_decompress_file_archive_not_found():
    """Test decompression fails when archive doesn't exist."""
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with pytest.raises(FileNotFoundError):
            decompress_file(Path("/nonexistent/archive.7z"), Path("/tmp/dest"))


def test_decompress_file_creates_dest_dir(tmp_path):
    """Test decompression creates destination directory if it doesn't exist."""
    archive_path = tmp_path / "test.7z"
    archive_path.write_bytes(b"fake archive")
    dest_dir = tmp_path / "new" / "nested" / "dir"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr='')
            
            decompress_file(archive_path, dest_dir)
            
            # Verify directory was created
            assert dest_dir.exists()
            assert dest_dir.is_dir()


def test_decompress_file_subprocess_error(tmp_path):
    """Test decompression handles subprocess errors."""
    archive_path = tmp_path / "test.7z"
    archive_path.write_bytes(b"fake archive")
    dest_dir = tmp_path / "extracted"
    
    with patch('gogrepoc.utils.compression._find_7zip', return_value='7z'):
        with patch('subprocess.run') as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.CalledProcessError(1, '7z', stderr='Error')
            
            with pytest.raises(CompressionError, match="Decompression failed"):
                decompress_file(archive_path, dest_dir)
