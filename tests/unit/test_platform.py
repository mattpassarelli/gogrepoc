"""Unit tests for platform-specific utilities.

Tests platform detection, filesystem type detection, and wakelock functionality.
"""

import sys
import platform
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from gogrepoc.infrastructure.platform import (
    get_platform,
    get_filesystem_type,
    Wakelock,
)


class TestPlatformDetection:
    """Tests for platform detection functionality."""

    def test_get_platform_returns_valid_value(self) -> None:
        """Test that get_platform returns one of the expected values."""
        result = get_platform()
        
        assert result in ['windows', 'macos', 'linux']

    def test_get_platform_matches_current_system(self) -> None:
        """Test that get_platform correctly identifies the current system."""
        result = get_platform()
        system = platform.system().lower()
        
        if system == 'windows':
            assert result == 'windows'
        elif system == 'darwin':
            assert result == 'macos'
        elif system == 'linux':
            assert result == 'linux'

    def test_get_platform_windows(self) -> None:
        """Test get_platform returns 'windows' on Windows."""
        with patch('platform.system', return_value='Windows'):
            result = get_platform()
            assert result == 'windows'

    def test_get_platform_macos(self) -> None:
        """Test get_platform returns 'macos' on macOS."""
        with patch('platform.system', return_value='Darwin'):
            result = get_platform()
            assert result == 'macos'

    def test_get_platform_linux(self) -> None:
        """Test get_platform returns 'linux' on Linux."""
        with patch('platform.system', return_value='Linux'):
            result = get_platform()
            assert result == 'linux'

    def test_get_platform_unsupported_raises_error(self) -> None:
        """Test that get_platform raises RuntimeError for unsupported platforms."""
        with patch('platform.system', return_value='FreeBSD'):
            with pytest.raises(RuntimeError, match="Unsupported platform: freebsd"):
                get_platform()


class TestFilesystemTypeDetection:
    """Tests for filesystem type detection."""

    def test_get_filesystem_type_returns_string(self, tmp_path: Path) -> None:
        """Test that get_filesystem_type returns a string."""
        result = get_filesystem_type(tmp_path)
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_filesystem_type_current_directory(self) -> None:
        """Test get_filesystem_type with no arguments uses current directory."""
        result = get_filesystem_type()
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_filesystem_type_with_path_object(self, tmp_path: Path) -> None:
        """Test get_filesystem_type accepts Path object."""
        result = get_filesystem_type(tmp_path)
        
        assert isinstance(result, str)

    def test_get_filesystem_type_with_string_path(self, tmp_path: Path) -> None:
        """Test get_filesystem_type accepts string path."""
        result = get_filesystem_type(str(tmp_path))
        
        assert isinstance(result, str)

    def test_get_filesystem_type_nonexistent_uses_parent(self, tmp_path: Path) -> None:
        """Test that nonexistent path uses parent directory."""
        nonexistent = tmp_path / "nonexistent" / "path"
        
        result = get_filesystem_type(nonexistent)
        
        # Should not raise error, returns filesystem type or 'unknown'
        assert isinstance(result, str)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_get_filesystem_type_windows(self, tmp_path: Path) -> None:
        """Test filesystem type detection on Windows."""
        result = get_filesystem_type(tmp_path)
        
        # Common Windows filesystems
        assert result in ['ntfs', 'fat32', 'exfat', 'refs', 'unknown']

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_get_filesystem_type_macos(self, tmp_path: Path) -> None:
        """Test filesystem type detection on macOS."""
        result = get_filesystem_type(tmp_path)
        
        # Common macOS filesystems (case-insensitive check)
        result_lower = result.lower()
        assert any(fs in result_lower for fs in ['apfs', 'hfs', 'unknown'])

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-specific test")
    def test_get_filesystem_type_linux(self, tmp_path: Path) -> None:
        """Test filesystem type detection on Linux."""
        result = get_filesystem_type(tmp_path)
        
        # Common Linux filesystems
        assert result in ['ext4', 'ext3', 'ext2', 'xfs', 'btrfs', 'tmpfs', 'unknown']

    def test_get_filesystem_type_handles_errors(self, tmp_path: Path) -> None:
        """Test that filesystem detection handles errors gracefully."""
        # Patch the platform-specific method to raise an exception
        current_platform = get_platform()
        
        if current_platform == 'windows':
            method_name = '_get_windows_filesystem_type'
        elif current_platform == 'macos':
            method_name = '_get_macos_filesystem_type'
        else:
            method_name = '_get_linux_filesystem_type'
        
        with patch(f'gogrepoc.infrastructure.platform.{method_name}', side_effect=Exception("Error")):
            result = get_filesystem_type(tmp_path)
            
            assert result == 'unknown'


class TestWakelock:
    """Tests for Wakelock context manager."""

    def test_wakelock_context_manager(self) -> None:
        """Test that Wakelock can be used as a context manager."""
        wakelock = Wakelock()
        
        # Should not raise any errors
        with wakelock:
            pass

    def test_wakelock_initializes_platform(self) -> None:
        """Test that Wakelock initializes with correct platform."""
        wakelock = Wakelock()
        
        assert wakelock.platform in ['windows', 'macos', 'linux']

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_wakelock_windows_acquire_release(self) -> None:
        """Test Windows wakelock acquire and release."""
        with patch('ctypes.windll.kernel32.SetThreadExecutionState') as mock_set_state:
            mock_set_state.return_value = 1  # Success
            
            wakelock = Wakelock()
            
            with wakelock:
                # Should call SetThreadExecutionState on enter
                assert mock_set_state.call_count >= 1
            
            # Should call SetThreadExecutionState on exit
            assert mock_set_state.call_count >= 2

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_wakelock_windows_failure_handled(self) -> None:
        """Test that Windows wakelock handles failures gracefully."""
        with patch('ctypes.windll.kernel32.SetThreadExecutionState', return_value=0):
            wakelock = Wakelock()
            
            # Should not raise error, just log warning
            with wakelock:
                pass

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_wakelock_macos_acquire_release(self) -> None:
        """Test macOS wakelock acquire and release using caffeinate."""
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
            wakelock = Wakelock()
            
            with wakelock:
                # Should start caffeinate process
                mock_popen.assert_called_once()
                args = mock_popen.call_args[0][0]
                assert 'caffeinate' in args
            
            # Should terminate process on exit
            mock_process.terminate.assert_called_once()

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_wakelock_macos_caffeinate_not_found(self) -> None:
        """Test macOS wakelock when caffeinate is not available."""
        with patch('subprocess.Popen', side_effect=FileNotFoundError("caffeinate not found")):
            wakelock = Wakelock()
            
            # Should not raise error, just log warning
            with wakelock:
                pass

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-specific test")
    def test_wakelock_linux_systemd_inhibit(self) -> None:
        """Test Linux wakelock using systemd-inhibit."""
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
            wakelock = Wakelock()
            
            with wakelock:
                # Should start systemd-inhibit process
                mock_popen.assert_called_once()
                args = mock_popen.call_args[0][0]
                assert 'systemd-inhibit' in args
            
            # Should terminate process on exit
            mock_process.terminate.assert_called_once()

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-specific test")
    def test_wakelock_linux_fallback_to_caffeine(self) -> None:
        """Test Linux wakelock falls back to caffeine if systemd-inhibit unavailable."""
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        
        def popen_side_effect(args, **kwargs):
            if 'systemd-inhibit' in args:
                raise FileNotFoundError("systemd-inhibit not found")
            return mock_process
        
        with patch('subprocess.Popen', side_effect=popen_side_effect) as mock_popen:
            wakelock = Wakelock()
            
            with wakelock:
                # Should try systemd-inhibit first, then caffeine
                assert mock_popen.call_count == 2
                second_call_args = mock_popen.call_args_list[1][0][0]
                assert 'caffeine' in second_call_args

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-specific test")
    def test_wakelock_linux_no_tools_available(self) -> None:
        """Test Linux wakelock when neither systemd-inhibit nor caffeine available."""
        with patch('subprocess.Popen', side_effect=FileNotFoundError("Not found")):
            wakelock = Wakelock()
            
            # Should not raise error, just log warning
            with wakelock:
                pass

    def test_wakelock_process_cleanup_on_timeout(self) -> None:
        """Test that wakelock kills process if termination times out."""
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock(side_effect=subprocess.TimeoutExpired('cmd', 5))
        mock_process.kill = MagicMock()
        
        # Mock platform to use subprocess-based wakelock
        with patch('gogrepoc.infrastructure.platform.get_platform', return_value='macos'):
            with patch('subprocess.Popen', return_value=mock_process):
                wakelock = Wakelock()
                
                with wakelock:
                    pass
                
                # Should call kill after timeout
                mock_process.kill.assert_called_once()

    def test_wakelock_handles_exception_in_context(self) -> None:
        """Test that wakelock releases properly even if exception occurs."""
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        
        with patch('gogrepoc.infrastructure.platform.get_platform', return_value='macos'):
            with patch('subprocess.Popen', return_value=mock_process):
                wakelock = Wakelock()
                
                try:
                    with wakelock:
                        raise ValueError("Test exception")
                except ValueError:
                    pass
                
                # Should still terminate process
                mock_process.terminate.assert_called_once()

    def test_wakelock_multiple_uses(self) -> None:
        """Test that Wakelock can be used multiple times."""
        wakelock = Wakelock()
        
        # First use
        with wakelock:
            pass
        
        # Second use
        with wakelock:
            pass

    def test_wakelock_nested_not_recommended_but_works(self) -> None:
        """Test that nested wakelock usage doesn't crash (though not recommended)."""
        wakelock1 = Wakelock()
        wakelock2 = Wakelock()
        
        with wakelock1:
            with wakelock2:
                pass
