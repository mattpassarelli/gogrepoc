"""Wakelock utilities to prevent system sleep during long operations."""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _get_platform() -> str:
    """Get current platform."""
    import platform
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    else:
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
        self.platform = _get_platform()
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
