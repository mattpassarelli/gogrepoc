"""Unit tests for wakelock utilities."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from gogrepoc.utils.wakelock import Wakelock, _get_platform


def test_get_platform_windows():
    """Test platform detection for Windows."""
    with patch('platform.system', return_value='Windows'):
        assert _get_platform() == 'windows'


def test_get_platform_macos():
    """Test platform detection for macOS."""
    with patch('platform.system', return_value='Darwin'):
        assert _get_platform() == 'macos'


def test_get_platform_linux():
    """Test platform detection for Linux."""
    with patch('platform.system', return_value='Linux'):
        assert _get_platform() == 'linux'


def test_get_platform_unknown():
    """Test platform detection for unknown systems."""
    with patch('platform.system', return_value='FreeBSD'):
        assert _get_platform() == 'unknown'


def test_wakelock_context_manager():
    """Test that Wakelock works as a context manager."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='unknown'):
        wakelock = Wakelock()
        
        # Should be able to enter and exit context
        with wakelock:
            pass


@pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific test")
def test_wakelock_windows_acquire():
    """Test Windows wakelock acquisition."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='windows'):
        with patch('ctypes.windll.kernel32.SetThreadExecutionState') as mock_set:
            mock_set.return_value = 1  # Success
            
            wakelock = Wakelock()
            wakelock.__enter__()
            
            # Verify SetThreadExecutionState was called
            assert mock_set.called


@pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific test")
def test_wakelock_windows_release():
    """Test Windows wakelock release."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='windows'):
        with patch('ctypes.windll.kernel32.SetThreadExecutionState') as mock_set:
            mock_set.return_value = 1
            
            wakelock = Wakelock()
            wakelock.__enter__()
            wakelock.__exit__(None, None, None)
            
            # Should be called twice: acquire and release
            assert mock_set.call_count == 2


def test_wakelock_macos_acquire():
    """Test macOS wakelock acquisition."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='macos'):
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            wakelock = Wakelock()
            wakelock.__enter__()
            
            # Verify caffeinate was started
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert 'caffeinate' in args


def test_wakelock_macos_release():
    """Test macOS wakelock release."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='macos'):
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            wakelock = Wakelock()
            wakelock.__enter__()
            wakelock.__exit__(None, None, None)
            
            # Verify process was terminated
            mock_process.terminate.assert_called_once()


def test_wakelock_macos_caffeinate_not_found():
    """Test macOS wakelock handles missing caffeinate gracefully."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='macos'):
        with patch('subprocess.Popen', side_effect=FileNotFoundError):
            wakelock = Wakelock()
            
            # Should not raise exception, just log warning
            with wakelock:
                pass


def test_wakelock_linux_acquire():
    """Test Linux wakelock acquisition."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='linux'):
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            wakelock = Wakelock()
            wakelock.__enter__()
            
            # Verify systemd-inhibit was started
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert 'systemd-inhibit' in args


def test_wakelock_linux_release():
    """Test Linux wakelock release."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='linux'):
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            wakelock = Wakelock()
            wakelock.__enter__()
            wakelock.__exit__(None, None, None)
            
            # Verify process was terminated
            mock_process.terminate.assert_called_once()


def test_wakelock_linux_fallback_to_caffeine():
    """Test Linux wakelock falls back to caffeine if systemd-inhibit not found."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='linux'):
        with patch('subprocess.Popen') as mock_popen:
            # First call (systemd-inhibit) fails, second call (caffeine) succeeds
            mock_process = MagicMock()
            mock_popen.side_effect = [FileNotFoundError, mock_process]
            
            wakelock = Wakelock()
            wakelock.__enter__()
            
            # Should have tried both commands
            assert mock_popen.call_count == 2


def test_wakelock_linux_no_tools_available():
    """Test Linux wakelock handles missing tools gracefully."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='linux'):
        with patch('subprocess.Popen', side_effect=FileNotFoundError):
            wakelock = Wakelock()
            
            # Should not raise exception, just log warning
            with wakelock:
                pass


def test_wakelock_unknown_platform():
    """Test wakelock on unknown platform does nothing."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='unknown'):
        wakelock = Wakelock()
        
        # Should work without errors
        with wakelock:
            pass


def test_wakelock_exception_in_context():
    """Test wakelock properly releases even if exception occurs in context."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='macos'):
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            wakelock = Wakelock()
            
            try:
                with wakelock:
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # Verify process was still terminated
            mock_process.terminate.assert_called_once()


def test_wakelock_process_timeout_on_release():
    """Test wakelock handles process timeout during release."""
    with patch('gogrepoc.utils.wakelock._get_platform', return_value='macos'):
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            import subprocess
            mock_process.wait.side_effect = subprocess.TimeoutExpired('caffeinate', 5)
            mock_popen.return_value = mock_process
            
            wakelock = Wakelock()
            
            # Should handle timeout gracefully
            with wakelock:
                pass
            
            # Should have tried to kill after timeout
            mock_process.kill.assert_called_once()
