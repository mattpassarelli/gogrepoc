"""7zip compression utilities."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional


class CompressionError(Exception):
    """Raised when compression/decompression operations fail."""
    pass


def _find_7zip() -> Optional[str]:
    """
    Find 7zip executable in system PATH.
    
    Returns:
        Path to 7zip executable or None if not found
    """
    # Try common 7zip command names
    for cmd in ["7z", "7za", "7zz"]:
        if shutil.which(cmd):
            return cmd
    return None


def compress_file(file_path: Path | str, archive_path: Path | str, compression_level: int = 5) -> None:
    """
    Compress a file using 7zip.
    
    Args:
        file_path: Path to the file to compress
        archive_path: Path where the archive should be created
        compression_level: Compression level (0-9, default 5)
        
    Raises:
        CompressionError: If 7zip is not installed or compression fails
        FileNotFoundError: If the input file does not exist
    """
    file_path = Path(file_path)
    archive_path = Path(archive_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    seven_zip = _find_7zip()
    if not seven_zip:
        raise CompressionError(
            "7zip is not installed or not found in PATH. "
            "Please install 7zip to use compression features."
        )
    
    # Ensure compression level is valid
    compression_level = max(0, min(9, compression_level))
    
    try:
        result = subprocess.run(
            [seven_zip, "a", f"-mx={compression_level}", str(archive_path), str(file_path)],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise CompressionError(f"Compression failed: {e.stderr}") from e


def decompress_file(archive_path: Path | str, dest_dir: Path | str) -> None:
    """
    Decompress an archive using 7zip.
    
    Args:
        archive_path: Path to the archive to decompress
        dest_dir: Directory where files should be extracted
        
    Raises:
        CompressionError: If 7zip is not installed or decompression fails
        FileNotFoundError: If the archive does not exist
    """
    archive_path = Path(archive_path)
    dest_dir = Path(dest_dir)
    
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    
    seven_zip = _find_7zip()
    if not seven_zip:
        raise CompressionError(
            "7zip is not installed or not found in PATH. "
            "Please install 7zip to use decompression features."
        )
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run(
            [seven_zip, "x", str(archive_path), f"-o{dest_dir}", "-y"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise CompressionError(f"Decompression failed: {e.stderr}") from e
