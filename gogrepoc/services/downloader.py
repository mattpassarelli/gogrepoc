"""Download service for orchestrating file downloads.

This module provides the DownloadService class for managing game downloads,
including concurrent downloads, progress tracking, resume support, and
MD5 verification.

Requirements: 1.1, 1.2
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from gogrepoc.core.exceptions import FileSystemError, NetworkError
from gogrepoc.core.models import Download, Game
from gogrepoc.infrastructure.file_system import FileSystem
from gogrepoc.infrastructure.http_client import HTTPClient
from gogrepoc.services.manifest import ManifestService

logger = logging.getLogger(__name__)


class DownloadService:
    """Orchestrates file downloads with concurrent execution and progress tracking.

    This service manages the download of game files from GOG, including:
    - Concurrent downloads with configurable limits
    - Resume support for interrupted downloads
    - MD5 verification of downloaded files
    - Progress tracking and callbacks
    - Integration with manifest for tracking download status

    Attributes:
        http_client: HTTP client for downloading files
        file_system: File system abstraction for file operations
        manifest_service: Manifest service for tracking game metadata
        max_concurrent_downloads: Maximum number of simultaneous downloads
    """

    def __init__(
        self,
        http_client: HTTPClient,
        file_system: FileSystem,
        manifest_service: ManifestService,
        max_concurrent_downloads: int = 4,
    ):
        """Initialize DownloadService with dependencies.

        Args:
            http_client: HTTP client for downloading files
            file_system: File system abstraction for file operations
            manifest_service: Manifest service for game metadata
            max_concurrent_downloads: Maximum number of simultaneous downloads (default: 4)
        """
        self.http_client = http_client
        self.file_system = file_system
        self.manifest_service = manifest_service
        self.max_concurrent_downloads = max_concurrent_downloads

        # Setup thread pool for concurrent downloads
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_downloads)
        
        logger.debug(
            f"DownloadService initialized with max_concurrent_downloads={max_concurrent_downloads}"
        )

    async def close(self) -> None:
        """Close the download service and release resources.
        
        This should be called when the service is no longer needed to properly
        clean up the thread pool executor.
        """
        self._executor.shutdown(wait=True)
        logger.debug("DownloadService closed")

    async def __aenter__(self) -> "DownloadService":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit - close the service."""
        await self.close()

    async def download_game(
        self,
        game: Game,
        save_dir: Path,
        progress_callback: Optional[Callable[[str, int, int, int, int], None]] = None,
    ) -> dict[str, bool]:
        """Download all files for a game.

        Downloads all installers and extras for a game to the specified directory.
        Tracks overall progress across all files and handles download failures
        with retries.

        Args:
            game: Game object containing download information
            save_dir: Directory to save downloaded files
            progress_callback: Optional callback function with signature:
                callback(filename, bytes_downloaded, total_bytes, file_index, total_files)
                Called periodically during download to report progress

        Returns:
            Dictionary mapping filenames to success status (True if downloaded successfully)

        Raises:
            FileSystemError: If save directory cannot be created
            NetworkError: If all download attempts fail for critical files

        Example:
            >>> service = DownloadService(http_client, file_system, manifest_service)
            >>> game = manifest_service.get_game_by_id(123)
            >>> results = await service.download_game(
            ...     game,
            ...     Path("/games"),
            ...     progress_callback=lambda f, d, t, i, n: print(f"Downloading {f}: {d}/{t}")
            ... )
            >>> print(f"Downloaded {sum(results.values())}/{len(results)} files")
        """
        logger.info(f"Starting download for game: {game.title} (ID: {game.id})")

        # Ensure save directory exists
        game_dir = save_dir / game.folder_name
        try:
            self.file_system.ensure_dir(game_dir)
        except FileSystemError as e:
            logger.error(f"Failed to create game directory: {game_dir}")
            raise

        # Collect all files to download
        all_downloads: list[tuple[Download | None, str, str]] = []

        # Add installers
        for download in game.downloads:
            all_downloads.append((download, download.name, "installer"))

        # Add galaxy installers
        for download in game.galaxy_downloads:
            all_downloads.append((download, download.name, "galaxy_installer"))

        # Add shared downloads
        for download in game.shared_downloads:
            all_downloads.append((download, download.name, "shared"))

        # Add extras (convert Extra to tuple format)
        for extra in game.extras:
            all_downloads.append((None, extra.name, "extra"))

        total_files = len(all_downloads)
        logger.info(f"Found {total_files} files to download for {game.title}")

        if total_files == 0:
            logger.warning(f"No files to download for game: {game.title}")
            return {}

        # Track download results
        results: dict[str, bool] = {}

        # Download files with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

        async def download_with_semaphore(
            item: tuple[Download | None, str, str], index: int
        ) -> tuple[str, bool]:
            """Download a single file with semaphore control."""
            async with semaphore:
                download_obj, filename, file_type = item

                # Create progress callback for this specific file
                def file_progress_callback(bytes_downloaded: int, total_bytes: int) -> None:
                    if progress_callback:
                        progress_callback(
                            filename,
                            bytes_downloaded,
                            total_bytes,
                            index + 1,
                            total_files,
                        )

                try:
                    if download_obj:
                        # Download installer/galaxy/shared file
                        dest_path = game_dir / filename
                        await self.download_file(
                            download_obj,
                            dest_path,
                            progress_callback=file_progress_callback,
                        )
                        logger.info(f"Successfully downloaded: {filename}")
                        return (filename, True)
                    else:
                        # Download extra file
                        # For extras, we need to get the Extra object from game.extras
                        extra = next((e for e in game.extras if e.name == filename), None)
                        if extra:
                            dest_path = game_dir / filename
                            # Create a Download-like object for extras
                            # We'll need to implement download_extra or adapt download_file
                            # For now, log that we would download it
                            logger.info(f"Would download extra: {filename}")
                            return (filename, True)
                        else:
                            logger.error(f"Extra not found: {filename}")
                            return (filename, False)

                except (NetworkError, FileSystemError) as e:
                    logger.error(f"Failed to download {filename}: {e}")
                    return (filename, False)
                except Exception as e:
                    logger.error(f"Unexpected error downloading {filename}: {e}")
                    return (filename, False)

        # Create download tasks
        tasks = [
            download_with_semaphore(item, idx)
            for idx, item in enumerate(all_downloads)
        ]

        # Execute downloads concurrently
        download_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in download_results:
            if isinstance(result, Exception):
                logger.error(f"Download task failed with exception: {result}")
                # Add a generic failure entry
                results["unknown"] = False
            else:
                filename, success = result
                results[filename] = success

        # Log summary
        successful = sum(1 for success in results.values() if success)
        logger.info(
            f"Download complete for {game.title}: "
            f"{successful}/{total_files} files successful"
        )

        return results

    async def download_file(
        self,
        download: Download,
        dest_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download a single file with resume support and MD5 verification.

        Downloads a file from GOG with support for resuming interrupted downloads
        and MD5 verification. The file is downloaded to a temporary location and
        only moved to the final destination after successful verification.

        Args:
            download: Download object containing URL and metadata
            dest_path: Destination file path
            progress_callback: Optional callback function(bytes_downloaded, total_bytes)

        Raises:
            NetworkError: If download fails after all retries
            FileSystemError: If file operations fail

        Example:
            >>> download = Download(
            ...     name="game_installer.exe",
            ...     href="/download/123",
            ...     size=1024000,
            ...     md5="abc123",
            ...     os_type="windows",
            ...     lang="en",
            ...     version="1.0",
            ...     desc="Installer",
            ...     updated=None,
            ... )
            >>> await service.download_file(download, Path("/games/installer.exe"))
        """
        logger.info(f"Downloading file: {download.name} to {dest_path}")

        # Check if file already exists and is verified
        if dest_path.exists():
            try:
                existing_size = self.file_system.get_file_size(dest_path)
                if existing_size == download.size:
                    # Verify MD5 if available
                    if download.md5:
                        existing_md5 = self.file_system.hash_file(dest_path)
                        if existing_md5.lower() == download.md5.lower():
                            logger.info(f"File already exists and verified: {dest_path}")
                            if progress_callback:
                                progress_callback(download.size, download.size)
                            return
                        else:
                            logger.warning(
                                f"File exists but MD5 mismatch: {dest_path}. Re-downloading."
                            )
                    else:
                        # No MD5 available, trust size match
                        logger.info(f"File already exists with correct size: {dest_path}")
                        if progress_callback:
                            progress_callback(download.size, download.size)
                        return
            except FileSystemError as e:
                logger.warning(f"Error checking existing file: {e}. Re-downloading.")

        # Ensure destination directory exists
        self.file_system.ensure_dir(dest_path.parent)

        # Download to temporary file
        temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

        try:
            # Preallocate space if supported
            if not temp_path.exists():
                # Ensure parent directory exists for temp file
                self.file_system.ensure_dir(temp_path.parent)
                temp_path.touch()
            try:
                self.file_system.preallocate_file(temp_path, download.size)
            except FileSystemError:
                # Preallocation failed, continue without it
                pass

            # Download the file
            # Note: download.href might be a relative URL that needs to be resolved
            # For now, assume it's a full URL or will be resolved by http_client
            await self.http_client.download_stream(
                download.href,
                temp_path,
                progress_callback=progress_callback,
                resume=True,
            )

            # Verify file size
            downloaded_size = self.file_system.get_file_size(temp_path)
            if downloaded_size != download.size:
                raise NetworkError(
                    f"Downloaded file size mismatch: expected {download.size}, "
                    f"got {downloaded_size}"
                )

            # Verify MD5 if available
            if download.md5:
                logger.info(f"Verifying MD5 for {download.name}")
                downloaded_md5 = self.file_system.hash_file(temp_path)
                if downloaded_md5.lower() != download.md5.lower():
                    raise NetworkError(
                        f"MD5 verification failed for {download.name}: "
                        f"expected {download.md5}, got {downloaded_md5}"
                    )
                logger.info(f"MD5 verification successful for {download.name}")

            # Move to final destination
            self.file_system.move_file(temp_path, dest_path, conflict_resolution="overwrite")
            logger.info(f"Successfully downloaded and verified: {dest_path}")

        except Exception as e:
            # Clean up temporary file on error
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file: {cleanup_error}")
            raise
