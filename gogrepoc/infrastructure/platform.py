"""Platform-specific utilities for cross-platform compatibility."""

import sys
import platform
import subprocess
import logging
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)


def get_platform() -> Literal['windows', 'macos', 'linux']:
    """
    Detect the current operating system platform.
    
    Returns:
        'windows', 'macos', or 'linux' based on the current platform
        
    Raises:
        RuntimeError: If the platform is not supported
    """
    system = platform.system().lower()
    
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def get_filesystem_type(directory: Path | str | None = None) -> str:
    """
    Detect the filesystem type for the given directory.
    
    Args:
        directory: Path to check. If None, uses current directory.
        
    Returns:
        Filesystem type as a string (e.g., 'ntfs', 'ext4', 'apfs', 'hfs+')
        Returns 'unknown' if detection fails
    """
    if directory is None:
        directory = Path.cwd()
    else:
        directory = Path(directory)
    
    # Ensure directory exists
    if not directory.exists():
        directory = directory.parent
    
    current_platform = get_platform()
    
    try:
        if current_platform == 'windows':
            return _get_windows_filesystem_type(directory)
        elif current_platform == 'macos':
            return _get_macos_filesystem_type(directory)
        elif current_platform == 'linux':
            return _get_linux_filesystem_type(directory)
    except Exception:
        return 'unknown'
    
    return 'unknown'


def _get_windows_filesystem_type(directory: Path) -> str:
    """Get filesystem type on Windows using ctypes."""
    try:
        import ctypes
        
        # Get the drive letter
        drive = str(directory.resolve().drive)
        if not drive:
            return 'unknown'
        
        # Ensure drive ends with backslash
        if not drive.endswith('\\'):
            drive += '\\'
        
        # Buffer for filesystem name
        fs_name_buffer = ctypes.create_unicode_buffer(256)
        
        # Call GetVolumeInformation
        result = ctypes.windll.kernel32.GetVolumeInformationW(
            drive,
            None, 0,  # Volume name buffer
            None,  # Volume serial number
            None,  # Maximum component length
            None,  # File system flags
            fs_name_buffer,
            256
        )
        
        if result:
            return fs_name_buffer.value.lower()
    except Exception:
        pass
    
    return 'unknown'


def _get_macos_filesystem_type(directory: Path) -> str:
    """Get filesystem type on macOS using diskutil."""
    try:
        import subprocess
        
        result = subprocess.run(
            ['diskutil', 'info', str(directory.resolve())],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if 'File System Personality' in line or 'Type (Bundle)' in line:
                    fs_type = line.split(':', 1)[1].strip().lower()
                    return fs_type
    except Exception:
        pass
    
    return 'unknown'


def _get_linux_filesystem_type(directory: Path) -> str:
    """Get filesystem type on Linux by reading /proc/mounts."""
    try:
        directory = directory.resolve()
        
        # Read /proc/mounts to find the filesystem
        with open('/proc/mounts', 'r') as f:
            mounts = f.readlines()
        
        # Find the longest matching mount point
        best_match = None
        best_match_len = 0
        
        for line in mounts:
            parts = line.split()
            if len(parts) < 3:
                continue
            
            mount_point = Path(parts[1])
            fs_type = parts[2]
            
            try:
                # Check if directory is under this mount point
                directory.relative_to(mount_point)
                mount_point_len = len(str(mount_point))
                
                if mount_point_len > best_match_len:
                    best_match = fs_type
                    best_match_len = mount_point_len
            except ValueError:
                # Not a subdirectory of this mount point
                continue
        
        if best_match:
            return best_match.lower()
    except Exception:
        pass
    
    return 'unknown'



class Wakelock:
    """
    Context manager to prevent system sleep during long-running operations.
    
    Supports Windows, macOS, and Linux platforms. Gracefully handles
    platforms without wakelock support.
    
    Usage:
        with Wakelock():
            # Long-running operation
            download_files()
    """
    
    def __init__(self):
        self.platform = get_platform()
        self._process: Optional[subprocess.Popen] = None
        self._previous_state: Optional[int] = None
    
    def __enter__(self):
        """Acquire wakelock to prevent system sleep."""
        try:
            if self.platform == 'windows':
                self._acquire_windows_wakelock()
            elif self.platform == 'macos':
                self._acquire_macos_wakelock()
            elif self.platform == 'linux':
                self._acquire_linux_wakelock()
        except Exception as e:
            logger.warning(f"Failed to acquire wakelock: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release wakelock to allow system sleep."""
        try:
            if self.platform == 'windows':
                self._release_windows_wakelock()
            elif self.platform == 'macos':
                self._release_macos_wakelock()
            elif self.platform == 'linux':
                self._release_linux_wakelock()
        except Exception as e:
            logger.warning(f"Failed to release wakelock: {e}")
        
        return False
    
    def _acquire_windows_wakelock(self):
        """Prevent sleep on Windows using SetThreadExecutionState."""
        import ctypes
        
        # Constants for SetThreadExecutionState
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        
        # Prevent system sleep and display sleep
        self._previous_state = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        
        if self._previous_state == 0:
            raise RuntimeError("Failed to set thread execution state")
        
        logger.debug("Windows wakelock acquired")
    
    def _release_windows_wakelock(self):
        """Allow sleep on Windows by resetting execution state."""
        import ctypes
        
        ES_CONTINUOUS = 0x80000000
        
        # Reset to normal state
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        logger.debug("Windows wakelock released")
    
    def _acquire_macos_wakelock(self):
        """Prevent sleep on macOS using caffeinate."""
        try:
            # Start caffeinate process
            # -d: prevent display sleep
            # -i: prevent idle sleep
            self._process = subprocess.Popen(
                ['caffeinate', '-d', '-i'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.debug("macOS wakelock acquired via caffeinate")
        except FileNotFoundError:
            logger.warning("caffeinate not found, wakelock not available")
            raise
    
    def _release_macos_wakelock(self):
        """Allow sleep on macOS by terminating caffeinate."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            logger.debug("macOS wakelock released")
    
    def _acquire_linux_wakelock(self):
        """Prevent sleep on Linux using systemd-inhibit."""
        try:
            # Try systemd-inhibit first
            self._process = subprocess.Popen(
                [
                    'systemd-inhibit',
                    '--what=idle:sleep',
                    '--who=gogrepoc',
                    '--why=Downloading files',
                    '--mode=block',
                    'cat'  # Keep process running
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.debug("Linux wakelock acquired via systemd-inhibit")
        except FileNotFoundError:
            # Try caffeine as fallback
            try:
                self._process = subprocess.Popen(
                    ['caffeine'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.debug("Linux wakelock acquired via caffeine")
            except FileNotFoundError:
                logger.warning("Neither systemd-inhibit nor caffeine found, wakelock not available")
                raise
    
    def _release_linux_wakelock(self):
        """Allow sleep on Linux by terminating inhibit process."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            logger.debug("Linux wakelock released")
