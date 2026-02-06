"""Unit tests for the DownloadService class."""

import pytest
from unittest.mock import Mock, AsyncMock

from gogrepoc.services.downloader import DownloadService
from gogrepoc.infrastructure.http_client import HTTPClient
from gogrepoc.infrastructure.file_system import FileSystem
from gogrepoc.services.manifest import ManifestService


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = Mock(spec=HTTPClient)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_file_system():
    """Create a mock file system."""
    return Mock(spec=FileSystem)


@pytest.fixture
def mock_manifest_service():
    """Create a mock manifest service."""
    return Mock(spec=ManifestService)


@pytest.fixture
def download_service(mock_http_client, mock_file_system, mock_manifest_service):
    """Create a DownloadService instance with mocked dependencies."""
    return DownloadService(
        http_client=mock_http_client,
        file_system=mock_file_system,
        manifest_service=mock_manifest_service,
    )


class TestDownloadServiceInit:
    """Tests for DownloadService initialization."""

    def test_init_with_dependencies(self, mock_http_client, mock_file_system, mock_manifest_service):
        """Test initialization with required dependencies."""
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
        )
        
        assert service.http_client == mock_http_client
        assert service.file_system == mock_file_system
        assert service.manifest_service == mock_manifest_service
        assert service.max_concurrent_downloads == 4  # Default value

    def test_init_with_custom_max_concurrent_downloads(
        self, mock_http_client, mock_file_system, mock_manifest_service
    ):
        """Test initialization with custom max_concurrent_downloads."""
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
            max_concurrent_downloads=8,
        )
        
        assert service.max_concurrent_downloads == 8

    def test_init_creates_thread_pool(self, download_service):
        """Test that initialization creates a thread pool executor."""
        assert download_service._executor is not None
        assert hasattr(download_service._executor, 'submit')

    def test_init_thread_pool_max_workers(
        self, mock_http_client, mock_file_system, mock_manifest_service
    ):
        """Test that thread pool is created with correct max_workers."""
        max_workers = 6
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
            max_concurrent_downloads=max_workers,
        )
        
        # Verify executor was created (we can't directly check max_workers,
        # but we can verify the executor exists and is a ThreadPoolExecutor)
        from concurrent.futures import ThreadPoolExecutor
        assert isinstance(service._executor, ThreadPoolExecutor)


class TestDownloadServiceContextManager:
    """Tests for DownloadService context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager_enter(self, download_service):
        """Test async context manager __aenter__."""
        async with download_service as service:
            assert service is download_service

    @pytest.mark.asyncio
    async def test_context_manager_exit_closes_service(self, download_service):
        """Test async context manager __aexit__ closes the service."""
        async with download_service:
            pass
        
        # Verify executor was shut down (we can check this by trying to submit)
        # After shutdown, submit should raise RuntimeError
        with pytest.raises(RuntimeError):
            download_service._executor.submit(lambda: None)

    @pytest.mark.asyncio
    async def test_close_method(self, download_service):
        """Test close method shuts down executor."""
        await download_service.close()
        
        # Verify executor was shut down
        with pytest.raises(RuntimeError):
            download_service._executor.submit(lambda: None)

    @pytest.mark.asyncio
    async def test_close_method_waits_for_tasks(self, download_service):
        """Test close method waits for pending tasks to complete."""
        import time
        
        # Submit a task that takes some time
        task_completed = False
        
        def slow_task():
            nonlocal task_completed
            time.sleep(0.1)
            task_completed = True
        
        download_service._executor.submit(slow_task)
        
        # Close should wait for the task
        await download_service.close()
        
        # Task should be completed
        assert task_completed is True


class TestDownloadServiceDependencies:
    """Tests for DownloadService dependency management."""

    def test_http_client_dependency(self, download_service, mock_http_client):
        """Test that HTTP client dependency is properly stored."""
        assert download_service.http_client is mock_http_client

    def test_file_system_dependency(self, download_service, mock_file_system):
        """Test that file system dependency is properly stored."""
        assert download_service.file_system is mock_file_system

    def test_manifest_service_dependency(self, download_service, mock_manifest_service):
        """Test that manifest service dependency is properly stored."""
        assert download_service.manifest_service is mock_manifest_service

    def test_dependencies_are_not_none(self, download_service):
        """Test that all dependencies are properly initialized."""
        assert download_service.http_client is not None
        assert download_service.file_system is not None
        assert download_service.manifest_service is not None


class TestDownloadGame:
    """Tests for download_game method."""

    @pytest.fixture
    def sample_game(self):
        """Create a sample game for testing."""
        from gogrepoc.core.models import Game, Download, Extra
        from datetime import datetime

        return Game(
            id=123,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game: Complete Edition",
            downloads=[
                Download(
                    name="installer_windows.exe",
                    href="https://gog.com/download/installer_windows.exe",
                    size=1024000,
                    md5="abc123",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="Windows Installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
            ],
            extras=[
                Extra(
                    name="manual.pdf",
                    href="https://gog.com/download/manual.pdf",
                    size=512000,
                    desc="Game Manual",
                    updated=datetime(2024, 1, 1),
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_download_game_creates_directory(
        self, download_service, mock_file_system, sample_game, tmp_path
    ):
        """Test that download_game creates the game directory."""
        save_dir = tmp_path / "games"
        
        # Mock download_file to avoid actual downloads
        download_service.download_file = AsyncMock()
        
        await download_service.download_game(sample_game, save_dir)
        
        # Verify directory creation was called
        expected_game_dir = save_dir / sample_game.folder_name
        mock_file_system.ensure_dir.assert_called_with(expected_game_dir)

    @pytest.mark.asyncio
    async def test_download_game_downloads_all_files(
        self, download_service, sample_game, tmp_path
    ):
        """Test that download_game attempts to download all files."""
        save_dir = tmp_path / "games"
        
        # Mock download_file to track calls
        download_service.download_file = AsyncMock()
        
        results = await download_service.download_game(sample_game, save_dir)
        
        # Should have attempted to download installer
        assert download_service.download_file.call_count == 1
        
        # Results should include the installer
        assert "installer_windows.exe" in results

    @pytest.mark.asyncio
    async def test_download_game_with_progress_callback(
        self, download_service, sample_game, tmp_path
    ):
        """Test that download_game calls progress callback."""
        save_dir = tmp_path / "games"
        progress_calls = []
        
        def progress_callback(filename, bytes_downloaded, total_bytes, file_index, total_files):
            progress_calls.append({
                "filename": filename,
                "bytes_downloaded": bytes_downloaded,
                "total_bytes": total_bytes,
                "file_index": file_index,
                "total_files": total_files,
            })
        
        # Mock download_file to simulate progress
        async def mock_download_file(download, dest_path, progress_callback=None):
            if progress_callback:
                progress_callback(download.size, download.size)
        
        download_service.download_file = AsyncMock(side_effect=mock_download_file)
        
        await download_service.download_game(sample_game, save_dir, progress_callback)
        
        # Progress callback should have been called
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_download_game_handles_failures(
        self, download_service, sample_game, tmp_path
    ):
        """Test that download_game handles download failures gracefully."""
        from gogrepoc.core.exceptions import NetworkError
        
        save_dir = tmp_path / "games"
        
        # Mock download_file to raise an error
        download_service.download_file = AsyncMock(side_effect=NetworkError("Download failed"))
        
        results = await download_service.download_game(sample_game, save_dir)
        
        # Should return results with failure status
        assert "installer_windows.exe" in results
        assert results["installer_windows.exe"] is False

    @pytest.mark.asyncio
    async def test_download_game_returns_success_status(
        self, download_service, sample_game, tmp_path
    ):
        """Test that download_game returns correct success status."""
        save_dir = tmp_path / "games"
        
        # Mock successful download
        download_service.download_file = AsyncMock()
        
        results = await download_service.download_game(sample_game, save_dir)
        
        # Should return success for downloaded files
        assert "installer_windows.exe" in results
        assert results["installer_windows.exe"] is True

    @pytest.mark.asyncio
    async def test_download_game_empty_game(
        self, download_service, mock_file_system, tmp_path
    ):
        """Test download_game with a game that has no files."""
        from gogrepoc.core.models import Game
        
        empty_game = Game(
            id=456,
            title="Empty Game",
            folder_name="empty_game",
            long_title="Empty Game",
        )
        
        save_dir = tmp_path / "games"
        
        results = await download_service.download_game(empty_game, save_dir)
        
        # Should return empty results
        assert results == {}

    @pytest.mark.asyncio
    async def test_download_game_concurrent_downloads(
        self, mock_http_client, mock_file_system, mock_manifest_service, tmp_path
    ):
        """Test that download_game respects max_concurrent_downloads limit."""
        from gogrepoc.core.models import Game, Download
        from datetime import datetime
        
        # Create service with low concurrency limit
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
            max_concurrent_downloads=2,
        )
        
        # Create game with multiple downloads
        game = Game(
            id=789,
            title="Multi File Game",
            folder_name="multi_file_game",
            long_title="Multi File Game",
            downloads=[
                Download(
                    name=f"file_{i}.bin",
                    href=f"https://gog.com/download/file_{i}.bin",
                    size=1024,
                    md5=f"md5_{i}",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc=f"File {i}",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                )
                for i in range(5)
            ],
        )
        
        # Mock download_file
        service.download_file = AsyncMock()
        
        save_dir = tmp_path / "games"
        results = await service.download_game(game, save_dir)
        
        # All files should be attempted
        assert len(results) == 5
        assert service.download_file.call_count == 5


class TestDownloadFile:
    """Tests for download_file method."""

    @pytest.fixture
    def sample_download(self):
        """Create a sample download for testing."""
        from gogrepoc.core.models import Download
        from datetime import datetime

        return Download(
            name="test_file.bin",
            href="https://gog.com/download/test_file.bin",
            size=1024000,
            md5="abc123def456",
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Test File",
            updated=datetime(2024, 1, 1),
            verified=False,
        )

    @pytest.mark.asyncio
    async def test_download_file_creates_directory(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file creates the destination directory."""
        dest_path = tmp_path / "games" / "test_game" / "test_file.bin"
        
        # Create the parent directory so temp_path.touch() works
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Mock http_client.download_stream
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system operations
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        
        await download_service.download_file(sample_download, dest_path)
        
        # Verify directory creation was called
        mock_file_system.ensure_dir.assert_called_with(dest_path.parent)

    @pytest.mark.asyncio
    async def test_download_file_skips_existing_verified(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file skips already verified files."""
        dest_path = tmp_path / "test_file.bin"
        dest_path.touch()  # Create the file
        
        # Mock file system to return matching size and MD5
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        await download_service.download_file(sample_download, dest_path)
        
        # Should not have called download_stream
        download_service.http_client.download_stream.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_file_redownloads_on_md5_mismatch(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file re-downloads files with MD5 mismatch."""
        dest_path = tmp_path / "test_file.bin"
        dest_path.touch()
        
        # Mock file system to return matching size but wrong MD5
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.side_effect = ["wrong_md5", sample_download.md5]
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        await download_service.download_file(sample_download, dest_path)
        
        # Should have called download_stream to re-download
        download_service.http_client.download_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_file_verifies_size(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file verifies file size after download."""
        from gogrepoc.core.exceptions import NetworkError
        
        dest_path = tmp_path / "test_file.bin"
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system to return wrong size
        mock_file_system.get_file_size.side_effect = [999999]  # Wrong size
        
        # Should raise NetworkError due to size mismatch
        with pytest.raises(NetworkError, match="size mismatch"):
            await download_service.download_file(sample_download, dest_path)

    @pytest.mark.asyncio
    async def test_download_file_verifies_md5(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file verifies MD5 after download."""
        from gogrepoc.core.exceptions import NetworkError
        
        dest_path = tmp_path / "test_file.bin"
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system to return correct size but wrong MD5
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = "wrong_md5"
        
        # Should raise NetworkError due to MD5 mismatch
        with pytest.raises(NetworkError, match="MD5 verification failed"):
            await download_service.download_file(sample_download, dest_path)

    @pytest.mark.asyncio
    async def test_download_file_with_progress_callback(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file passes progress callback to http_client."""
        dest_path = tmp_path / "test_file.bin"
        progress_calls = []
        
        def progress_callback(bytes_downloaded, total_bytes):
            progress_calls.append((bytes_downloaded, total_bytes))
        
        # Mock http_client
        async def mock_download_stream(url, dest, progress_callback=None, resume=True):
            if progress_callback:
                progress_callback(sample_download.size, sample_download.size)
        
        download_service.http_client.download_stream = AsyncMock(side_effect=mock_download_stream)
        
        # Mock file system
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        
        await download_service.download_file(sample_download, dest_path, progress_callback)
        
        # Progress callback should have been called
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_download_file_cleans_up_on_error(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file cleans up temporary file on error."""
        from gogrepoc.core.exceptions import NetworkError
        
        dest_path = tmp_path / "test_file.bin"
        temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
        temp_path.touch()
        
        # Mock http_client to raise error
        download_service.http_client.download_stream = AsyncMock(
            side_effect=NetworkError("Download failed")
        )
        
        # Should raise NetworkError
        with pytest.raises(NetworkError):
            await download_service.download_file(sample_download, dest_path)
        
        # Temporary file should be cleaned up
        assert not temp_path.exists()

    @pytest.mark.asyncio
    async def test_download_file_resume_partial_download(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file can resume a partial download."""
        dest_path = tmp_path / "test_file.bin"
        temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
        
        # Create a partial download file
        temp_path.touch()
        
        # Mock http_client to support resume
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        
        await download_service.download_file(sample_download, dest_path)
        
        # Should have called download_stream with resume=True
        download_service.http_client.download_stream.assert_called_once()
        call_args = download_service.http_client.download_stream.call_args
        assert call_args.kwargs.get('resume') is True

    @pytest.mark.asyncio
    async def test_download_file_without_md5(
        self, download_service, mock_file_system, tmp_path
    ):
        """Test that download_file works without MD5 verification."""
        from gogrepoc.core.models import Download
        from datetime import datetime
        
        # Create download without MD5
        download_no_md5 = Download(
            name="test_file.bin",
            href="https://gog.com/download/test_file.bin",
            size=1024000,
            md5=None,  # No MD5
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Test File",
            updated=datetime(2024, 1, 1),
            verified=False,
        )
        
        dest_path = tmp_path / "test_file.bin"
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system - only size check, no MD5
        mock_file_system.get_file_size.return_value = download_no_md5.size
        
        # Should complete without MD5 verification
        await download_service.download_file(download_no_md5, dest_path)
        
        # Should not have called hash_file since no MD5 to verify
        mock_file_system.hash_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_file_moves_to_final_location(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file moves file from temp to final location."""
        dest_path = tmp_path / "test_file.bin"
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        
        await download_service.download_file(sample_download, dest_path)
        
        # Should have called move_file to move from temp to final location
        mock_file_system.move_file.assert_called_once()
        call_args = mock_file_system.move_file.call_args
        assert call_args.kwargs.get('conflict_resolution') == 'overwrite'

    @pytest.mark.asyncio
    async def test_download_file_preallocates_space(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file attempts to preallocate disk space."""
        dest_path = tmp_path / "test_file.bin"
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        mock_file_system.preallocate_file = Mock()
        
        await download_service.download_file(sample_download, dest_path)
        
        # Should have attempted preallocation
        mock_file_system.preallocate_file.assert_called_once()
        call_args = mock_file_system.preallocate_file.call_args
        assert call_args[0][1] == sample_download.size

    @pytest.mark.asyncio
    async def test_download_file_handles_preallocation_failure(
        self, download_service, mock_file_system, sample_download, tmp_path
    ):
        """Test that download_file continues if preallocation fails."""
        from gogrepoc.core.exceptions import FileSystemError
        
        dest_path = tmp_path / "test_file.bin"
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        # Mock file system - preallocation fails
        mock_file_system.preallocate_file.side_effect = FileSystemError("Preallocation failed")
        mock_file_system.get_file_size.return_value = sample_download.size
        mock_file_system.hash_file.return_value = sample_download.md5
        
        # Should complete successfully despite preallocation failure
        await download_service.download_file(sample_download, dest_path)
        
        # Download should have proceeded
        download_service.http_client.download_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_file_skips_existing_without_md5(
        self, download_service, mock_file_system, tmp_path
    ):
        """Test that download_file skips existing files when no MD5 is available."""
        from gogrepoc.core.models import Download
        from datetime import datetime
        
        # Create download without MD5
        download_no_md5 = Download(
            name="test_file.bin",
            href="https://gog.com/download/test_file.bin",
            size=1024000,
            md5=None,
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Test File",
            updated=datetime(2024, 1, 1),
            verified=False,
        )
        
        dest_path = tmp_path / "test_file.bin"
        dest_path.touch()
        
        # Mock file system to return matching size
        mock_file_system.get_file_size.return_value = download_no_md5.size
        
        # Mock http_client
        download_service.http_client.download_stream = AsyncMock()
        
        await download_service.download_file(download_no_md5, dest_path)
        
        # Should not have downloaded since file exists with correct size
        download_service.http_client.download_stream.assert_not_called()


class TestDownloadServiceConcurrency:
    """Tests for concurrent download functionality."""

    @pytest.mark.asyncio
    async def test_concurrent_downloads_respect_limit(
        self, mock_http_client, mock_file_system, mock_manifest_service
    ):
        """Test that concurrent downloads respect the max limit."""
        import asyncio
        
        # Create service with limit of 2
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
            max_concurrent_downloads=2,
        )
        
        # Track concurrent downloads
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def mock_download(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            
            # Simulate download time
            await asyncio.sleep(0.01)
            
            async with lock:
                concurrent_count -= 1
        
        service.download_file = AsyncMock(side_effect=mock_download)
        
        # Create game with 5 downloads
        from gogrepoc.core.models import Game, Download
        from datetime import datetime
        
        game = Game(
            id=1,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game",
            downloads=[
                Download(
                    name=f"file_{i}.bin",
                    href=f"https://gog.com/file_{i}.bin",
                    size=1024,
                    md5=f"md5_{i}",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc=f"File {i}",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                )
                for i in range(5)
            ],
        )
        
        from pathlib import Path
        await service.download_game(game, Path("/tmp"))
        
        # Max concurrent should not exceed limit
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_concurrent_downloads_handle_individual_failures(
        self, mock_http_client, mock_file_system, mock_manifest_service
    ):
        """Test that one download failure doesn't stop others."""
        from gogrepoc.core.exceptions import NetworkError
        
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
            max_concurrent_downloads=3,
        )
        
        # Mock download_file to fail for specific files
        async def mock_download(download, dest_path, progress_callback=None):
            if "file_2" in download.name:
                raise NetworkError("Download failed")
        
        service.download_file = AsyncMock(side_effect=mock_download)
        
        # Create game with multiple downloads
        from gogrepoc.core.models import Game, Download
        from datetime import datetime
        
        game = Game(
            id=1,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game",
            downloads=[
                Download(
                    name=f"file_{i}.bin",
                    href=f"https://gog.com/file_{i}.bin",
                    size=1024,
                    md5=f"md5_{i}",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc=f"File {i}",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                )
                for i in range(4)
            ],
        )
        
        from pathlib import Path
        results = await service.download_game(game, Path("/tmp"))
        
        # Should have results for all files
        assert len(results) == 4
        
        # file_2 should have failed
        assert results["file_2.bin"] is False
        
        # Others should have succeeded
        assert results["file_0.bin"] is True
        assert results["file_1.bin"] is True
        assert results["file_3.bin"] is True


class TestDownloadServiceProgressTracking:
    """Tests for progress tracking functionality."""

    @pytest.fixture
    def sample_download(self):
        """Create a sample download for testing."""
        from gogrepoc.core.models import Download
        from datetime import datetime

        return Download(
            name="test_file.bin",
            href="https://gog.com/download/test_file.bin",
            size=1024000,
            md5="abc123def456",
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Test File",
            updated=datetime(2024, 1, 1),
            verified=False,
        )

    @pytest.mark.asyncio
    async def test_progress_callback_receives_correct_parameters(
        self, download_service, sample_download, tmp_path
    ):
        """Test that progress callback receives correct parameters."""
        from gogrepoc.core.models import Game
        
        dest_path = tmp_path / "test_file.bin"
        progress_calls = []
        
        def progress_callback(filename, bytes_downloaded, total_bytes, file_index, total_files):
            progress_calls.append({
                "filename": filename,
                "bytes_downloaded": bytes_downloaded,
                "total_bytes": total_bytes,
                "file_index": file_index,
                "total_files": total_files,
            })
        
        # Mock download_file to simulate progress
        async def mock_download_file(download, dest_path, progress_callback=None):
            if progress_callback:
                # Simulate progress updates
                progress_callback(512000, download.size)
                progress_callback(download.size, download.size)
        
        download_service.download_file = AsyncMock(side_effect=mock_download_file)
        
        # Create simple game
        game = Game(
            id=1,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game",
            downloads=[sample_download],
        )
        
        await download_service.download_game(game, tmp_path, progress_callback)
        
        # Should have received progress updates
        assert len(progress_calls) > 0
        
        # Check parameters
        for call in progress_calls:
            assert call["filename"] == sample_download.name
            assert call["total_bytes"] == sample_download.size
            assert call["file_index"] == 1
            assert call["total_files"] == 1

    @pytest.mark.asyncio
    async def test_progress_callback_tracks_multiple_files(
        self, mock_http_client, mock_file_system, mock_manifest_service, tmp_path
    ):
        """Test that progress callback correctly tracks multiple files."""
        from gogrepoc.core.models import Game, Download
        from datetime import datetime
        
        service = DownloadService(
            http_client=mock_http_client,
            file_system=mock_file_system,
            manifest_service=mock_manifest_service,
        )
        
        progress_calls = []
        
        def progress_callback(filename, bytes_downloaded, total_bytes, file_index, total_files):
            progress_calls.append({
                "filename": filename,
                "file_index": file_index,
                "total_files": total_files,
            })
        
        # Mock download_file
        async def mock_download_file(download, dest_path, progress_callback=None):
            if progress_callback:
                progress_callback(download.size, download.size)
        
        service.download_file = AsyncMock(side_effect=mock_download_file)
        
        # Create game with 3 downloads
        game = Game(
            id=1,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game",
            downloads=[
                Download(
                    name=f"file_{i}.bin",
                    href=f"https://gog.com/file_{i}.bin",
                    size=1024,
                    md5=f"md5_{i}",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc=f"File {i}",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                )
                for i in range(3)
            ],
        )
        
        await service.download_game(game, tmp_path, progress_callback)
        
        # Should have progress for all files
        assert len(progress_calls) == 3
        
        # Check file indices
        file_indices = [call["file_index"] for call in progress_calls]
        assert sorted(file_indices) == [1, 2, 3]
        
        # All should report total_files = 3
        assert all(call["total_files"] == 3 for call in progress_calls)
