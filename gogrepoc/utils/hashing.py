"""MD5 hashing utilities for file verification."""

import hashlib
from pathlib import Path


def calculate_md5(file_path: Path | str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash of a file using chunked reading for memory efficiency.
    
    Args:
        file_path: Path to the file to hash
        chunk_size: Size of chunks to read (default 8KB)
        
    Returns:
        Hex digest string of the MD5 hash
        
    Raises:
        FileNotFoundError: If the file does not exist
        IOError: If there's an error reading the file
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    md5_hash = hashlib.md5()
    
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
    
    return md5_hash.hexdigest()
