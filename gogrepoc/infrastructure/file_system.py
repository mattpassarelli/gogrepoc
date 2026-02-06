"""File system abstraction for cross-platform file operations.

This module provides a FileSystem class that abstracts file system operations
with cross-platform compatibility using pathlib.Path.

Requirements: 1.1, 5.1, 2.3, 1.3, 5.4, 5.2, 5.3
"""

import hashlib
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional

import psutil  # type: ignore[import-untyped]

from gogrepoc.core.constants import POSIX_PREALLOCATION_FS, WINDOWS_PREALLOCATION_FS
from gogrepoc.core.exceptions import FileSystemError

# Platform-specific imports
if sys.platform == "win32" or TYPE_CHECKING:
    import ctypes
    import ctypes.wintypes

if sys.platform == "darwin" or TYPE_CHECKING:
    import fcntl

logger = logging.getLogger(__name__)


class FileSystem:
    """Abstraction over file system operations for cross-platform compatibility.

    This class provides methods for common file system operations using pathlib.Path
    to ensure cross-platform compatibility. All path operations handle platform
    differences (case sensitivity, path separators) automatically.

    The class focuses on safe, reliable file operations with proper error handling
    and logging.
    """

    def ensure_dir(self, path: Path) -> None:
        """Create directory if it doesn't exist, including parent directories.

        This method creates the specified directory and all necessary parent
        directories. If the directory already exists, no error is raised.
        This is equivalent to 'mkdir -p' on Unix systems.

        Args:
            path: Path to the directory to create

        Raises:
            FileSystemError: If directory creation fails due to permissions,
                           disk space, or other file system errors

        Example:
            >>> fs = FileSystem()
            >>> fs.ensure_dir(Path("/path/to/nested/directory"))
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
        except PermissionError as e:
            raise FileSystemError(
                f"Permission denied when creating directory", path=str(path), operation="mkdir"
            ) from e
        except OSError as e:
            # Catch other OS errors like disk full, invalid path, etc.
            raise FileSystemError(
                f"Failed to create directory: {e}", path=str(path), operation="mkdir"
            ) from e

    def get_file_size(self, path: Path) -> int:
        """Get the size of a file in bytes.

        This method returns the size of the specified file. The file must exist
        and be accessible.

        Args:
            path: Path to the file

        Returns:
            File size in bytes

        Raises:
            FileSystemError: If the file doesn't exist, is not accessible,
                           or if there's an error reading file metadata

        Example:
            >>> fs = FileSystem()
            >>> size = fs.get_file_size(Path("/path/to/file.bin"))
            >>> print(f"File size: {size} bytes")
        """
        try:
            if not path.exists():
                raise FileSystemError("File does not exist", path=str(path), operation="stat")

            if not path.is_file():
                raise FileSystemError("Path is not a file", path=str(path), operation="stat")

            size = path.stat().st_size
            logger.debug(f"File size for {path}: {size} bytes")
            return size

        except PermissionError as e:
            raise FileSystemError(
                "Permission denied when accessing file", path=str(path), operation="stat"
            ) from e
        except OSError as e:
            raise FileSystemError(
                f"Failed to get file size: {e}", path=str(path), operation="stat"
            ) from e

    def move_file(
        self,
        src: Path,
        dest: Path,
        conflict_resolution: Literal["overwrite", "skip", "rename"] = "rename",
    ) -> Path:
        """Move a file from source to destination with conflict resolution.

        This method moves a file from the source path to the destination path.
        If the destination already exists, the behavior is controlled by the
        conflict_resolution parameter.

        Args:
            src: Source file path
            dest: Destination file path
            conflict_resolution: How to handle existing destination file:
                - "overwrite": Replace existing file
                - "skip": Keep existing file, don't move
                - "rename": Rename new file with suffix (e.g., file_1.txt)

        Returns:
            Path to the final destination (may differ from dest if renamed)

        Raises:
            FileSystemError: If source doesn't exist, is not a file,
                           or if the move operation fails

        Example:
            >>> fs = FileSystem()
            >>> final_path = fs.move_file(
            ...     Path("/tmp/source.txt"),
            ...     Path("/data/dest.txt"),
            ...     conflict_resolution="rename"
            ... )
        """
        try:
            # Validate source file
            if not src.exists():
                raise FileSystemError("Source file does not exist", path=str(src), operation="move")

            if not src.is_file():
                raise FileSystemError("Source path is not a file", path=str(src), operation="move")

            # Ensure destination directory exists
            self.ensure_dir(dest.parent)

            # Handle conflict resolution
            final_dest = dest
            if dest.exists():
                if conflict_resolution == "skip":
                    logger.info(f"Skipping move, destination already exists: {dest}")
                    return dest
                elif conflict_resolution == "overwrite":
                    logger.info(f"Overwriting existing file: {dest}")
                    dest.unlink()
                elif conflict_resolution == "rename":
                    # Find a unique name by appending _1, _2, etc.
                    counter = 1
                    stem = dest.stem
                    suffix = dest.suffix
                    parent = dest.parent
                    while final_dest.exists():
                        final_dest = parent / f"{stem}_{counter}{suffix}"
                        counter += 1
                    logger.info(f"Renaming to avoid conflict: {final_dest}")

            # Perform the move
            shutil.move(str(src), str(final_dest))
            logger.debug(f"Moved file from {src} to {final_dest}")
            return final_dest

        except PermissionError as e:
            raise FileSystemError(
                "Permission denied when moving file",
                path=f"{src} -> {dest}",
                operation="move",
            ) from e
        except OSError as e:
            raise FileSystemError(
                f"Failed to move file: {e}", path=f"{src} -> {dest}", operation="move"
            ) from e

    def copy_file(self, src: Path, dest: Path, overwrite: bool = False) -> None:
        """Copy a file from source to destination for backup operations.

        This method copies a file from the source path to the destination path.
        The source file is preserved. This is useful for backup operations.

        Args:
            src: Source file path
            dest: Destination file path
            overwrite: If True, overwrite existing destination file.
                      If False, raise error if destination exists.

        Raises:
            FileSystemError: If source doesn't exist, is not a file,
                           destination exists (when overwrite=False),
                           or if the copy operation fails

        Example:
            >>> fs = FileSystem()
            >>> fs.copy_file(
            ...     Path("/data/important.txt"),
            ...     Path("/backup/important.txt"),
            ...     overwrite=True
            ... )
        """
        try:
            # Validate source file
            if not src.exists():
                raise FileSystemError("Source file does not exist", path=str(src), operation="copy")

            if not src.is_file():
                raise FileSystemError("Source path is not a file", path=str(src), operation="copy")

            # Check destination
            if dest.exists() and not overwrite:
                raise FileSystemError(
                    "Destination file already exists", path=str(dest), operation="copy"
                )

            # Ensure destination directory exists
            self.ensure_dir(dest.parent)

            # Perform the copy
            shutil.copy2(str(src), str(dest))
            logger.debug(f"Copied file from {src} to {dest}")

        except PermissionError as e:
            raise FileSystemError(
                "Permission denied when copying file",
                path=f"{src} -> {dest}",
                operation="copy",
            ) from e
        except OSError as e:
            raise FileSystemError(
                f"Failed to copy file: {e}", path=f"{src} -> {dest}", operation="copy"
            ) from e

    def hash_file(self, path: Path, chunk_size: int = 8192) -> str:
        """Calculate MD5 hash of a file using chunked reading.

        This method calculates the MD5 hash of a file by reading it in chunks,
        which is memory-efficient for large files. The chunk size can be adjusted
        for performance tuning.

        Args:
            path: Path to the file to hash
            chunk_size: Size of chunks to read in bytes (default: 8192)

        Returns:
            MD5 hash as a hexadecimal string (32 characters)

        Raises:
            FileSystemError: If file doesn't exist, is not a file,
                           or if reading fails

        Example:
            >>> fs = FileSystem()
            >>> md5_hash = fs.hash_file(Path("/data/game.bin"))
            >>> print(f"MD5: {md5_hash}")
            MD5: 5d41402abc4b2a76b9719d911017c592
        """
        try:
            # Validate file
            if not path.exists():
                raise FileSystemError("File does not exist", path=str(path), operation="hash")

            if not path.is_file():
                raise FileSystemError("Path is not a file", path=str(path), operation="hash")

            # Calculate MD5 hash using chunked reading
            md5_hash = hashlib.md5()
            with open(path, "rb") as f:
                while chunk := f.read(chunk_size):
                    md5_hash.update(chunk)

            hash_value = md5_hash.hexdigest()
            logger.debug(f"Calculated MD5 hash for {path}: {hash_value}")
            return hash_value

        except PermissionError as e:
            raise FileSystemError(
                "Permission denied when reading file", path=str(path), operation="hash"
            ) from e
        except OSError as e:
            raise FileSystemError(
                f"Failed to read file for hashing: {e}", path=str(path), operation="hash"
            ) from e

    def _get_fs_type(self, path: Path) -> str:
        """Get the filesystem type for a given path.

        This method determines the filesystem type (e.g., NTFS, ext4, btrfs)
        for the partition containing the specified path. This is used to
        determine if file preallocation is supported.

        Args:
            path: Path to check filesystem type for

        Returns:
            Filesystem type as a string (e.g., "NTFS", "ext4", "btrfs")
            Returns "unknown" if filesystem type cannot be determined

        Example:
            >>> fs = FileSystem()
            >>> fs_type = fs._get_fs_type(Path("/data/games"))
            >>> print(f"Filesystem: {fs_type}")
        """
        try:
            # Get the real path (resolve symlinks)
            real_path = path.resolve()

            # Build a mapping of mount points to filesystem types
            partition_map: dict[str, str] = {}
            for part in psutil.disk_partitions(all=True):
                partition_map[part.mountpoint] = part.fstype

            # Check if the path exactly matches a mount point
            path_str = str(real_path)
            if path_str in partition_map:
                fs_type: str = partition_map[path_str]
                return fs_type

            # Walk up the directory tree to find the mount point
            # Split path and check each parent directory
            parts = real_path.parts
            for i in range(len(parts), 0, -1):
                if sys.platform == "win32":
                    # Windows paths need trailing separator
                    test_path = str(Path(*parts[:i])) + os.sep
                else:
                    test_path = str(Path(*parts[:i]))

                if test_path in partition_map:
                    fs_type = partition_map[test_path]
                    return fs_type

            return "unknown"

        except Exception as e:
            logger.warning(f"Failed to determine filesystem type for {path}: {e}")
            return "unknown"

    def preallocate_file(self, path: Path, size: int) -> None:
        """Preallocate disk space for a file on supported platforms.

        This method preallocates disk space for a file to improve download
        performance and reduce fragmentation. The implementation is platform-
        specific and only works on supported filesystems.

        Platform support:
        - Windows: Uses SetFilePointerEx and SetEndOfFile on NTFS, exFAT, FAT32
        - Linux: Uses posix_fallocate on ext4, btrfs, xfs, and other supported filesystems
        - macOS: Uses fcntl with F_PREALLOCATE on APFS and HFS+

        If preallocation is not supported on the current platform or filesystem,
        the method logs a warning and returns without error.

        Args:
            path: Path to the file to preallocate space for.
                 The file must already exist (can be empty or partially written).
            size: Total size in bytes to preallocate

        Raises:
            FileSystemError: If the file doesn't exist or if there's a critical
                           error during preallocation (e.g., disk full)

        Example:
            >>> fs = FileSystem()
            >>> file_path = Path("/data/game.bin")
            >>> file_path.touch()  # Create empty file
            >>> fs.preallocate_file(file_path, 1024 * 1024 * 100)  # 100 MB
        """
        try:
            # Validate file exists
            if not path.exists():
                raise FileSystemError(
                    "Cannot preallocate space for non-existent file",
                    path=str(path),
                    operation="preallocate",
                )

            # Get filesystem type
            fs_type = self._get_fs_type(path)
            logger.debug(f"Filesystem type for {path}: {fs_type}")

            # Platform-specific preallocation
            if sys.platform == "win32":
                self._preallocate_windows(path, size, fs_type)
            elif sys.platform == "darwin":
                self._preallocate_macos(path, size)
            elif sys.platform.startswith("linux"):
                self._preallocate_linux(path, size, fs_type)
            else:
                logger.debug(f"File preallocation not supported on platform: {sys.platform}")

        except FileSystemError:
            # Re-raise FileSystemError as-is
            raise
        except Exception as e:
            # Log other errors but don't fail - preallocation is an optimization
            logger.warning(f"File preallocation failed for {path}: {e}")

    def _preallocate_windows(self, path: Path, size: int, fs_type: str) -> None:
        """Preallocate file space on Windows using Win32 API.

        Args:
            path: Path to the file
            size: Size in bytes to preallocate
            fs_type: Filesystem type
        """
        if sys.platform != "win32":
            return

        # Check if filesystem supports preallocation
        if fs_type not in WINDOWS_PREALLOCATION_FS:
            logger.debug(
                f"Filesystem {fs_type} does not support preallocation on Windows, skipping"
            )
            return

        try:
            # Windows API constants
            GENERIC_READ = 0x80000000
            GENERIC_WRITE = 0x40000000
            OPEN_EXISTING = 3
            FILE_BEGIN = 0

            logger.info(f"Preallocating {size} bytes for '{path}' on Windows")

            # Open file handle
            file_handle = ctypes.windll.kernel32.CreateFileW(
                str(path),
                GENERIC_READ | GENERIC_WRITE,
                0,  # No sharing
                None,  # Default security
                OPEN_EXISTING,
                0,  # Normal attributes
                None,  # No template
            )

            if file_handle == -1 or file_handle == 0xFFFFFFFF:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise FileSystemError(
                    f"Failed to open file for preallocation (error code: {error_code})",
                    path=str(path),
                    operation="preallocate",
                )

            try:
                # Set file pointer to desired size
                distance_to_move = ctypes.c_longlong(size)
                new_file_pointer = ctypes.c_longlong(0)

                result = ctypes.windll.kernel32.SetFilePointerEx(
                    file_handle,
                    distance_to_move,
                    ctypes.byref(new_file_pointer),
                    FILE_BEGIN,
                )

                if not result:
                    error_code = ctypes.windll.kernel32.GetLastError()
                    raise FileSystemError(
                        f"Failed to set file pointer (error code: {error_code})",
                        path=str(path),
                        operation="preallocate",
                    )

                # Set end of file to preallocate space
                result = ctypes.windll.kernel32.SetEndOfFile(file_handle)

                if not result:
                    error_code = ctypes.windll.kernel32.GetLastError()
                    raise FileSystemError(
                        f"Failed to set end of file (error code: {error_code})",
                        path=str(path),
                        operation="preallocate",
                    )

                logger.debug(f"Successfully preallocated {size} bytes for {path}")

            finally:
                # Always close the file handle
                ctypes.windll.kernel32.CloseHandle(file_handle)

        except FileSystemError:
            raise
        except Exception as e:
            logger.warning(f"Windows preallocation failed for {path}: {e}")

    def _preallocate_linux(self, path: Path, size: int, fs_type: str) -> None:
        """Preallocate file space on Linux using posix_fallocate.

        Args:
            path: Path to the file
            size: Size in bytes to preallocate
            fs_type: Filesystem type
        """
        if not sys.platform.startswith("linux"):
            return

        # Check if filesystem supports preallocation
        if fs_type.lower() not in POSIX_PREALLOCATION_FS:
            logger.debug(
                f"Filesystem {fs_type} does not support preallocation on Linux, skipping"
            )
            return

        try:
            logger.info(f"Preallocating {size} bytes for '{path}' using posix_fallocate")

            with open(path, "r+b") as f:
                # posix_fallocate(fd, offset, length)
                # Preallocate from offset 0 to size
                os.posix_fallocate(f.fileno(), 0, size)

            logger.debug(f"Successfully preallocated {size} bytes for {path}")

        except AttributeError:
            # posix_fallocate not available on this system
            logger.debug("posix_fallocate not available on this system")
        except OSError as e:
            # Handle specific errors
            if e.errno == 28:  # ENOSPC - No space left on device
                raise FileSystemError(
                    "No space left on device for preallocation",
                    path=str(path),
                    operation="preallocate",
                ) from e
            else:
                logger.warning(f"Linux preallocation failed for {path}: {e}")

    def _preallocate_macos(self, path: Path, size: int) -> None:
        """Preallocate file space on macOS using fcntl F_PREALLOCATE.

        Args:
            path: Path to the file
            size: Size in bytes to preallocate
        """
        if sys.platform != "darwin":
            return

        try:
            # macOS F_PREALLOCATE constant
            F_PREALLOCATE = 42  # From fcntl.h on macOS
            F_ALLOCATECONTIG = 0x02  # Allocate contiguous space
            F_ALLOCATEALL = 0x04  # Allocate all or nothing

            logger.info(f"Preallocating {size} bytes for '{path}' using fcntl F_PREALLOCATE")

            # fstore structure for F_PREALLOCATE
            # typedef struct fstore {
            #     u_int32_t fst_flags;
            #     int fst_posmode;
            #     off_t fst_offset;
            #     off_t fst_length;
            #     off_t fst_bytesalloc;
            # }
            import struct

            with open(path, "r+b") as f:
                # Try to allocate contiguous space first
                fstore = struct.pack("IiQQQ", F_ALLOCATECONTIG, 0, 0, size, 0)
                try:
                    fcntl.fcntl(f.fileno(), F_PREALLOCATE, fstore)
                except OSError:
                    # If contiguous allocation fails, try non-contiguous
                    fstore = struct.pack("IiQQQ", F_ALLOCATEALL, 0, 0, size, 0)
                    fcntl.fcntl(f.fileno(), F_PREALLOCATE, fstore)

                # Set the file size
                f.truncate(size)

            logger.debug(f"Successfully preallocated {size} bytes for {path}")

        except Exception as e:
            logger.warning(f"macOS preallocation failed for {path}: {e}")
