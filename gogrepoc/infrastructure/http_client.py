"""HTTP client wrapper with retry logic and connection pooling.

This module provides an HTTPClient class that wraps httpx with:
- Automatic retry logic with exponential backoff
- Connection pooling for efficient resource usage
- Timeout handling
- Progress tracking for downloads

Requirements: 1.1, 2.3, 6.3
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from gogrepoc.core.exceptions import NetworkError

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with retry logic and connection pooling.

    This class wraps httpx.AsyncClient to provide:
    - Automatic retry with exponential backoff for transient errors
    - Connection pooling for efficient resource usage
    - Configurable timeouts
    - Streaming downloads with progress callbacks

    Attributes:
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests
    """

    def __init__(self, timeout: int = 60, max_retries: int = 4) -> None:
        """Initialize HTTP client with timeout and retry settings.

        Args:
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum number of retry attempts (default: 4)
        """
        self.timeout = timeout
        self.max_retries = max_retries

        # Create httpx client with connection pooling
        # limits parameter controls connection pool size
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0
            ),
            follow_redirects=True,
        )

    async def __aenter__(self) -> "HTTPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - close the client."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()

    async def _retry_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Execute HTTP request with retry logic.

        Implements exponential backoff for transient errors:
        - Network timeouts
        - 5xx server errors
        - Connection errors

        Args:
            method: HTTP method (GET, POST, HEAD, etc.)
            url: Request URL
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            httpx.Response object

        Raises:
            NetworkError: If all retry attempts fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)

                # Check for server errors that should trigger retry
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"Server error {response.status_code} for {url}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise NetworkError(
                            f"Server error {response.status_code} after {self.max_retries} retries: {url}"
                        )

                # Success - return response
                response.raise_for_status()
                return response

            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Network error for {url}: {type(e).__name__}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(
                        f"Network error after {self.max_retries} retries: {url}"
                    ) from e

            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx)
                raise NetworkError(f"HTTP error {e.response.status_code}: {url}") from e

        # Should not reach here, but just in case
        raise NetworkError(
            f"Request failed after {self.max_retries} retries: {url}"
        ) from last_error

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute GET request with retry logic.

        Args:
            url: Request URL
            **kwargs: Additional arguments (headers, params, etc.)

        Returns:
            httpx.Response object

        Raises:
            NetworkError: If request fails after all retries
        """
        return await self._retry_request("GET", url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute HEAD request with retry logic.

        Args:
            url: Request URL
            **kwargs: Additional arguments (headers, params, etc.)

        Returns:
            httpx.Response object

        Raises:
            NetworkError: If request fails after all retries
        """
        return await self._retry_request("HEAD", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute POST request with retry logic.

        Args:
            url: Request URL
            **kwargs: Additional arguments (headers, data, json, etc.)

        Returns:
            httpx.Response object

        Raises:
            NetworkError: If request fails after all retries
        """
        return await self._retry_request("POST", url, **kwargs)

    async def download_stream(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        resume: bool = True,
    ) -> None:
        """Download file with streaming and optional progress tracking.

        Downloads a file in chunks to avoid loading entire file into memory.
        Supports resume from partial downloads.

        Args:
            url: Download URL
            dest: Destination file path
            progress_callback: Optional callback function(bytes_downloaded, total_bytes)
            resume: Whether to resume partial downloads (default: True)

        Raises:
            NetworkError: If download fails after all retries
        """
        # Check for existing partial download
        start_byte = 0
        if resume and dest.exists():
            start_byte = dest.stat().st_size
            logger.info(f"Resuming download from byte {start_byte}")

        # Setup headers for resume
        headers = {}
        if start_byte > 0:
            headers["Range"] = f"bytes={start_byte}-"

        # Open file in append mode if resuming, write mode otherwise
        mode = "ab" if start_byte > 0 else "wb"

        try:
            async with self._client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                # Get total file size
                content_length = response.headers.get("content-length")
                if content_length:
                    total_size = int(content_length)
                    if start_byte > 0:
                        # For resumed downloads, add the existing bytes
                        total_size += start_byte
                else:
                    total_size = 0

                bytes_downloaded = start_byte

                # Download in chunks
                with open(dest, mode) as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(bytes_downloaded, total_size)

                logger.info(f"Download complete: {dest}")

        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            raise NetworkError(f"Download failed: {url}") from e
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP error {e.response.status_code} during download: {url}") from e
        except OSError as e:
            raise NetworkError(f"File write error: {dest}") from e
