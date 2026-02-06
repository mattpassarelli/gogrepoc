"""Unit tests for FileSystem class.

Tests the file system abstraction with directory creation and file size queries.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gogrepoc.core.exceptions import FileSystemError
from gogrepoc.infrastructure.file_system import FileSystem


@pytest.fixture
def file_system() -> FileSystem:
    """Create FileSystem instance for testing."""
    return FileSystem()


def test_ensure_dir_creates_new_directory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that ensure_dir creates a new directory."""
    test_dir = tmp_path / "new_directory"

    assert not test_dir.exists()

    file_system.ensure_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()


def test_ensure_dir_creates_nested_directories(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that ensure_dir creates nested directories (parents=True)."""
    test_dir = tmp_path / "level1" / "level2" / "level3"

    assert not test_dir.exists()

    file_system.ensure_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()
    assert (tmp_path / "level1").exists()
    assert (tmp_path / "level1" / "level2").exists()


def test_ensure_dir_existing_directory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that ensure_dir doesn't raise error for existing directory."""
    test_dir = tmp_path / "existing_directory"
    test_dir.mkdir()

    assert test_dir.exists()

    # Should not raise any error
    file_system.ensure_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()


def test_ensure_dir_permission_error(file_system: FileSystem) -> None:
    """Test that ensure_dir raises FileSystemError on permission denied."""
    test_path = Path("/root/restricted_directory")

    with patch.object(Path, "mkdir", side_effect=PermissionError("Permission denied")):
        with pytest.raises(FileSystemError, match="Permission denied when creating directory"):
            file_system.ensure_dir(test_path)


def test_ensure_dir_os_error(file_system: FileSystem) -> None:
    """Test that ensure_dir raises FileSystemError on OS errors."""
    test_path = Path("/invalid/path")

    with patch.object(Path, "mkdir", side_effect=OSError("Disk full")):
        with pytest.raises(FileSystemError, match="Failed to create directory"):
            file_system.ensure_dir(test_path)


def test_get_file_size_returns_correct_size(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size returns the correct file size."""
    test_file = tmp_path / "test_file.txt"
    test_data = b"Hello, World!" * 100  # 1300 bytes
    test_file.write_bytes(test_data)

    size = file_system.get_file_size(test_file)

    assert size == len(test_data)
    assert size == 1300


def test_get_file_size_empty_file(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size returns 0 for empty file."""
    test_file = tmp_path / "empty_file.txt"
    test_file.touch()

    size = file_system.get_file_size(test_file)

    assert size == 0


def test_get_file_size_large_file(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size works with large files."""
    test_file = tmp_path / "large_file.bin"
    # Create a 10MB file
    large_data = b"X" * (10 * 1024 * 1024)
    test_file.write_bytes(large_data)

    size = file_system.get_file_size(test_file)

    assert size == len(large_data)
    assert size == 10 * 1024 * 1024


def test_get_file_size_file_not_exists(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size raises FileSystemError when file doesn't exist."""
    test_file = tmp_path / "nonexistent_file.txt"

    with pytest.raises(FileSystemError, match="File does not exist"):
        file_system.get_file_size(test_file)


def test_get_file_size_path_is_directory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size raises FileSystemError when path is a directory."""
    test_dir = tmp_path / "test_directory"
    test_dir.mkdir()

    with pytest.raises(FileSystemError, match="Path is not a file"):
        file_system.get_file_size(test_dir)


def test_get_file_size_permission_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size raises FileSystemError on permission denied."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_bytes(b"test data")

    with patch.object(Path, "stat", side_effect=PermissionError("Permission denied")):
        with pytest.raises(FileSystemError, match="Permission denied when accessing file"):
            file_system.get_file_size(test_file)


def test_get_file_size_os_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that get_file_size raises FileSystemError on OS errors."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_bytes(b"test data")

    with patch.object(Path, "stat", side_effect=OSError("I/O error")):
        with pytest.raises(FileSystemError, match="Failed to get file size"):
            file_system.get_file_size(test_file)


def test_ensure_dir_with_file_path(file_system: FileSystem, tmp_path: Path) -> None:
    """Test ensure_dir behavior when path points to an existing file."""
    # Create a file
    test_file = tmp_path / "test_file.txt"
    test_file.write_bytes(b"test data")

    # Trying to create a directory with the same name should fail
    with pytest.raises(FileSystemError):
        file_system.ensure_dir(test_file)


def test_get_file_size_with_special_characters(file_system: FileSystem, tmp_path: Path) -> None:
    """Test get_file_size with filenames containing special characters."""
    test_file = tmp_path / "test file with spaces & special-chars.txt"
    test_data = b"Special file content"
    test_file.write_bytes(test_data)

    size = file_system.get_file_size(test_file)

    assert size == len(test_data)


def test_ensure_dir_with_special_characters(file_system: FileSystem, tmp_path: Path) -> None:
    """Test ensure_dir with directory names containing special characters."""
    test_dir = tmp_path / "dir with spaces" / "sub-dir_123"

    file_system.ensure_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()


def test_get_file_size_symlink(file_system: FileSystem, tmp_path: Path) -> None:
    """Test get_file_size follows symlinks and returns target file size."""
    # Create a real file
    real_file = tmp_path / "real_file.txt"
    test_data = b"Real file content"
    real_file.write_bytes(test_data)

    # Create a symlink
    symlink = tmp_path / "symlink.txt"
    try:
        symlink.symlink_to(real_file)
    except OSError:
        # Skip test if symlinks are not supported (e.g., Windows without admin)
        pytest.skip("Symlinks not supported on this system")

    size = file_system.get_file_size(symlink)

    assert size == len(test_data)


def test_ensure_dir_absolute_path(file_system: FileSystem, tmp_path: Path) -> None:
    """Test ensure_dir with absolute path."""
    test_dir = tmp_path / "absolute" / "path" / "test"
    absolute_path = test_dir.resolve()

    file_system.ensure_dir(absolute_path)

    assert absolute_path.exists()
    assert absolute_path.is_dir()


def test_get_file_size_absolute_path(file_system: FileSystem, tmp_path: Path) -> None:
    """Test get_file_size with absolute path."""
    test_file = tmp_path / "test_file.txt"
    test_data = b"Test data"
    test_file.write_bytes(test_data)
    absolute_path = test_file.resolve()

    size = file_system.get_file_size(absolute_path)

    assert size == len(test_data)


# Tests for move_file


def test_move_file_basic(file_system: FileSystem, tmp_path: Path) -> None:
    """Test basic file move operation."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    test_data = b"Test content"
    src.write_bytes(test_data)

    result = file_system.move_file(src, dest)

    assert result == dest
    assert not src.exists()
    assert dest.exists()
    assert dest.read_bytes() == test_data


def test_move_file_to_subdirectory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test moving file to a subdirectory that doesn't exist yet."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "subdir" / "nested" / "dest.txt"
    test_data = b"Test content"
    src.write_bytes(test_data)

    result = file_system.move_file(src, dest)

    assert result == dest
    assert not src.exists()
    assert dest.exists()
    assert dest.read_bytes() == test_data


def test_move_file_conflict_overwrite(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file with overwrite conflict resolution."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"New content")
    dest.write_bytes(b"Old content")

    result = file_system.move_file(src, dest, conflict_resolution="overwrite")

    assert result == dest
    assert not src.exists()
    assert dest.exists()
    assert dest.read_bytes() == b"New content"


def test_move_file_conflict_skip(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file with skip conflict resolution."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"New content")
    dest.write_bytes(b"Old content")

    result = file_system.move_file(src, dest, conflict_resolution="skip")

    assert result == dest
    assert src.exists()  # Source still exists
    assert dest.exists()
    assert dest.read_bytes() == b"Old content"  # Destination unchanged


def test_move_file_conflict_rename(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file with rename conflict resolution."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"New content")
    dest.write_bytes(b"Old content")

    result = file_system.move_file(src, dest, conflict_resolution="rename")

    assert result == tmp_path / "dest_1.txt"
    assert not src.exists()
    assert dest.exists()
    assert dest.read_bytes() == b"Old content"  # Original unchanged
    assert result.read_bytes() == b"New content"  # Renamed file has new content


def test_move_file_conflict_rename_multiple(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file rename with multiple existing files."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    dest_1 = tmp_path / "dest_1.txt"
    dest_2 = tmp_path / "dest_2.txt"

    src.write_bytes(b"New content")
    dest.write_bytes(b"Content 0")
    dest_1.write_bytes(b"Content 1")
    dest_2.write_bytes(b"Content 2")

    result = file_system.move_file(src, dest, conflict_resolution="rename")

    assert result == tmp_path / "dest_3.txt"
    assert not src.exists()
    assert result.read_bytes() == b"New content"


def test_move_file_source_not_exists(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file raises error when source doesn't exist."""
    src = tmp_path / "nonexistent.txt"
    dest = tmp_path / "dest.txt"

    with pytest.raises(FileSystemError, match="Source file does not exist"):
        file_system.move_file(src, dest)


def test_move_file_source_is_directory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file raises error when source is a directory."""
    src = tmp_path / "source_dir"
    dest = tmp_path / "dest.txt"
    src.mkdir()

    with pytest.raises(FileSystemError, match="Source path is not a file"):
        file_system.move_file(src, dest)


def test_move_file_permission_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file raises FileSystemError on permission denied."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"Test content")

    with patch("shutil.move", side_effect=PermissionError("Permission denied")):
        with pytest.raises(FileSystemError, match="Permission denied when moving file"):
            file_system.move_file(src, dest)


def test_move_file_os_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test move_file raises FileSystemError on OS errors."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"Test content")

    with patch("shutil.move", side_effect=OSError("Disk full")):
        with pytest.raises(FileSystemError, match="Failed to move file"):
            file_system.move_file(src, dest)


# Tests for copy_file


def test_copy_file_basic(file_system: FileSystem, tmp_path: Path) -> None:
    """Test basic file copy operation."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    test_data = b"Test content"
    src.write_bytes(test_data)

    file_system.copy_file(src, dest)

    assert src.exists()  # Source still exists
    assert dest.exists()
    assert src.read_bytes() == test_data
    assert dest.read_bytes() == test_data


def test_copy_file_to_subdirectory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copying file to a subdirectory that doesn't exist yet."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "backup" / "nested" / "dest.txt"
    test_data = b"Test content"
    src.write_bytes(test_data)

    file_system.copy_file(src, dest)

    assert src.exists()
    assert dest.exists()
    assert dest.read_bytes() == test_data


def test_copy_file_preserves_metadata(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that copy_file preserves file metadata (using copy2)."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    test_data = b"Test content"
    src.write_bytes(test_data)

    # Get original modification time
    original_mtime = src.stat().st_mtime

    file_system.copy_file(src, dest)

    # Check that modification time is preserved (within 1 second tolerance)
    dest_mtime = dest.stat().st_mtime
    assert abs(dest_mtime - original_mtime) < 1.0


def test_copy_file_overwrite_false_existing_dest(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copy_file raises error when destination exists and overwrite=False."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"New content")
    dest.write_bytes(b"Old content")

    with pytest.raises(FileSystemError, match="Destination file already exists"):
        file_system.copy_file(src, dest, overwrite=False)

    # Destination should be unchanged
    assert dest.read_bytes() == b"Old content"


def test_copy_file_overwrite_true(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copy_file overwrites when overwrite=True."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"New content")
    dest.write_bytes(b"Old content")

    file_system.copy_file(src, dest, overwrite=True)

    assert src.exists()
    assert dest.exists()
    assert dest.read_bytes() == b"New content"


def test_copy_file_source_not_exists(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copy_file raises error when source doesn't exist."""
    src = tmp_path / "nonexistent.txt"
    dest = tmp_path / "dest.txt"

    with pytest.raises(FileSystemError, match="Source file does not exist"):
        file_system.copy_file(src, dest)


def test_copy_file_source_is_directory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copy_file raises error when source is a directory."""
    src = tmp_path / "source_dir"
    dest = tmp_path / "dest.txt"
    src.mkdir()

    with pytest.raises(FileSystemError, match="Source path is not a file"):
        file_system.copy_file(src, dest)


def test_copy_file_permission_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copy_file raises FileSystemError on permission denied."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"Test content")

    with patch("shutil.copy2", side_effect=PermissionError("Permission denied")):
        with pytest.raises(FileSystemError, match="Permission denied when copying file"):
            file_system.copy_file(src, dest)


def test_copy_file_os_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test copy_file raises FileSystemError on OS errors."""
    src = tmp_path / "source.txt"
    dest = tmp_path / "dest.txt"
    src.write_bytes(b"Test content")

    with patch("shutil.copy2", side_effect=OSError("Disk full")):
        with pytest.raises(FileSystemError, match="Failed to copy file"):
            file_system.copy_file(src, dest)


# Tests for hash_file


def test_hash_file_basic(file_system: FileSystem, tmp_path: Path) -> None:
    """Test basic MD5 hash calculation."""
    test_file = tmp_path / "test.txt"
    test_data = b"Hello, World!"
    test_file.write_bytes(test_data)

    # Known MD5 hash for "Hello, World!"
    expected_hash = "65a8e27d8879283831b664bd8b7f0ad4"

    hash_value = file_system.hash_file(test_file)

    assert hash_value == expected_hash
    assert len(hash_value) == 32  # MD5 is 32 hex characters


def test_hash_file_empty_file(file_system: FileSystem, tmp_path: Path) -> None:
    """Test MD5 hash of empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.touch()

    # Known MD5 hash for empty file
    expected_hash = "d41d8cd98f00b204e9800998ecf8427e"

    hash_value = file_system.hash_file(test_file)

    assert hash_value == expected_hash


def test_hash_file_large_file(file_system: FileSystem, tmp_path: Path) -> None:
    """Test MD5 hash calculation for large file using chunked reading."""
    test_file = tmp_path / "large.bin"
    # Create a 1MB file with repeating pattern
    test_data = b"X" * (1024 * 1024)
    test_file.write_bytes(test_data)

    hash_value = file_system.hash_file(test_file)

    # Verify it's a valid MD5 hash
    assert len(hash_value) == 32
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_hash_file_custom_chunk_size(file_system: FileSystem, tmp_path: Path) -> None:
    """Test hash_file with custom chunk size."""
    test_file = tmp_path / "test.txt"
    test_data = b"Hello, World!"
    test_file.write_bytes(test_data)

    expected_hash = "65a8e27d8879283831b664bd8b7f0ad4"

    # Test with different chunk sizes
    hash_value_small = file_system.hash_file(test_file, chunk_size=4)
    hash_value_large = file_system.hash_file(test_file, chunk_size=16384)

    assert hash_value_small == expected_hash
    assert hash_value_large == expected_hash


def test_hash_file_binary_content(file_system: FileSystem, tmp_path: Path) -> None:
    """Test MD5 hash calculation for binary file."""
    test_file = tmp_path / "binary.bin"
    # Create binary content with various byte values
    test_data = bytes(range(256))
    test_file.write_bytes(test_data)

    hash_value = file_system.hash_file(test_file)

    # Verify it's a valid MD5 hash
    assert len(hash_value) == 32
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_hash_file_not_exists(file_system: FileSystem, tmp_path: Path) -> None:
    """Test hash_file raises error when file doesn't exist."""
    test_file = tmp_path / "nonexistent.txt"

    with pytest.raises(FileSystemError, match="File does not exist"):
        file_system.hash_file(test_file)


def test_hash_file_is_directory(file_system: FileSystem, tmp_path: Path) -> None:
    """Test hash_file raises error when path is a directory."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    with pytest.raises(FileSystemError, match="Path is not a file"):
        file_system.hash_file(test_dir)


def test_hash_file_permission_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test hash_file raises FileSystemError on permission denied."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"Test content")

    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(FileSystemError, match="Permission denied when reading file"):
            file_system.hash_file(test_file)


def test_hash_file_os_error(file_system: FileSystem, tmp_path: Path) -> None:
    """Test hash_file raises FileSystemError on OS errors."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"Test content")

    with patch("builtins.open", side_effect=OSError("I/O error")):
        with pytest.raises(FileSystemError, match="Failed to read file for hashing"):
            file_system.hash_file(test_file)


def test_hash_file_consistent_results(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that hash_file produces consistent results for the same file."""
    test_file = tmp_path / "test.txt"
    test_data = b"Consistent content"
    test_file.write_bytes(test_data)

    hash1 = file_system.hash_file(test_file)
    hash2 = file_system.hash_file(test_file)
    hash3 = file_system.hash_file(test_file)

    assert hash1 == hash2 == hash3


def test_hash_file_different_content_different_hash(
    file_system: FileSystem, tmp_path: Path
) -> None:
    """Test that different file contents produce different hashes."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_bytes(b"Content A")
    file2.write_bytes(b"Content B")

    hash1 = file_system.hash_file(file1)
    hash2 = file_system.hash_file(file2)

    assert hash1 != hash2


# Tests for preallocate_file


def test_preallocate_file_basic(file_system: FileSystem, tmp_path: Path) -> None:
    """Test basic file preallocation."""
    test_file = tmp_path / "preallocated.bin"
    test_file.touch()  # Create empty file
    size = 1024 * 1024  # 1 MB

    # Should not raise an error
    file_system.preallocate_file(test_file, size)

    # File should exist
    assert test_file.exists()


def test_preallocate_file_nonexistent_file(file_system: FileSystem, tmp_path: Path) -> None:
    """Test that preallocate_file raises error for non-existent file."""
    test_file = tmp_path / "nonexistent.bin"
    size = 1024 * 1024

    with pytest.raises(FileSystemError, match="Cannot preallocate space for non-existent file"):
        file_system.preallocate_file(test_file, size)


def test_preallocate_file_zero_size(file_system: FileSystem, tmp_path: Path) -> None:
    """Test preallocation with zero size."""
    test_file = tmp_path / "zero.bin"
    test_file.touch()

    # Should not raise an error
    file_system.preallocate_file(test_file, 0)

    assert test_file.exists()


def test_preallocate_file_large_size(file_system: FileSystem, tmp_path: Path) -> None:
    """Test preallocation with large size (10 MB)."""
    test_file = tmp_path / "large.bin"
    test_file.touch()
    size = 10 * 1024 * 1024  # 10 MB

    # Should not raise an error (may log warning if not supported)
    file_system.preallocate_file(test_file, size)

    assert test_file.exists()


def test_preallocate_file_existing_content(file_system: FileSystem, tmp_path: Path) -> None:
    """Test preallocation on file with existing content."""
    test_file = tmp_path / "existing.bin"
    test_file.write_bytes(b"Existing content")
    size = 1024 * 1024  # 1 MB

    # Should not raise an error
    file_system.preallocate_file(test_file, size)

    assert test_file.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_preallocate_windows_supported_fs(file_system: FileSystem, tmp_path: Path) -> None:
    """Test Windows preallocation on supported filesystem."""
    test_file = tmp_path / "windows.bin"
    test_file.touch()
    size = 1024 * 1024

    # Mock filesystem type to be NTFS
    with patch.object(file_system, "_get_fs_type", return_value="NTFS"):
        file_system.preallocate_file(test_file, size)

    assert test_file.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_preallocate_windows_unsupported_fs(file_system: FileSystem, tmp_path: Path) -> None:
    """Test Windows preallocation on unsupported filesystem."""
    test_file = tmp_path / "windows.bin"
    test_file.touch()
    size = 1024 * 1024

    # Mock filesystem type to be unsupported
    with patch.object(file_system, "_get_fs_type", return_value="ReFS"):
        # Should not raise error, just skip preallocation
        file_system.preallocate_file(test_file, size)

    assert test_file.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-specific test")
def test_preallocate_linux_supported_fs(file_system: FileSystem, tmp_path: Path) -> None:
    """Test Linux preallocation on supported filesystem."""
    test_file = tmp_path / "linux.bin"
    test_file.touch()
    size = 1024 * 1024

    # Mock filesystem type to be ext4
    with patch.object(file_system, "_get_fs_type", return_value="ext4"):
        file_system.preallocate_file(test_file, size)

    assert test_file.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-specific test")
def test_preallocate_linux_unsupported_fs(file_system: FileSystem, tmp_path: Path) -> None:
    """Test Linux preallocation on unsupported filesystem."""
    test_file = tmp_path / "linux.bin"
    test_file.touch()
    size = 1024 * 1024

    # Mock filesystem type to be unsupported
    with patch.object(file_system, "_get_fs_type", return_value="tmpfs"):
        # Should not raise error, just skip preallocation
        file_system.preallocate_file(test_file, size)

    assert test_file.exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
def test_preallocate_macos(file_system: FileSystem, tmp_path: Path) -> None:
    """Test macOS preallocation."""
    test_file = tmp_path / "macos.bin"
    test_file.touch()
    size = 1024 * 1024

    # Should not raise error
    file_system.preallocate_file(test_file, size)

    assert test_file.exists()


def test_get_fs_type_basic(file_system: FileSystem, tmp_path: Path) -> None:
    """Test _get_fs_type returns a filesystem type."""
    fs_type = file_system._get_fs_type(tmp_path)

    # Should return a non-empty string
    assert isinstance(fs_type, str)
    assert len(fs_type) > 0


def test_get_fs_type_nonexistent_path(file_system: FileSystem, tmp_path: Path) -> None:
    """Test _get_fs_type with non-existent path."""
    nonexistent = tmp_path / "nonexistent" / "path"

    # Should return "unknown" or a valid filesystem type for parent
    fs_type = file_system._get_fs_type(nonexistent)

    assert isinstance(fs_type, str)


def test_get_fs_type_file_path(file_system: FileSystem, tmp_path: Path) -> None:
    """Test _get_fs_type with file path (should return filesystem of parent)."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    fs_type = file_system._get_fs_type(test_file)

    # Should return a non-empty string
    assert isinstance(fs_type, str)
    assert len(fs_type) > 0


def test_preallocate_file_handles_errors_gracefully(
    file_system: FileSystem, tmp_path: Path
) -> None:
    """Test that preallocation errors are handled gracefully (logged, not raised)."""
    test_file = tmp_path / "test.bin"
    test_file.touch()
    size = 1024 * 1024

    # Mock platform-specific method to raise an exception
    if sys.platform == "win32":
        method_name = "_preallocate_windows"
    elif sys.platform == "darwin":
        method_name = "_preallocate_macos"
    else:
        method_name = "_preallocate_linux"

    with patch.object(
        file_system, method_name, side_effect=Exception("Preallocation failed")
    ):
        # Should not raise, just log warning
        file_system.preallocate_file(test_file, size)

    assert test_file.exists()
