"""Unit tests for HTTPClient class.

Tests the HTTP client wrapper with retry logic, connection pooling,
and streaming downloads.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from gogrepoc.core.exceptions import NetworkError
from gogrepoc.infrastructure.http_client import HTTPClient


@pytest.fixture
async def http_client() -> HTTPClient:
    """Create HTTPClient instance for testing."""
    client = HTTPClient(timeout=10, max_retries=3)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_http_client_initialization() -> None:
    """Test HTTPClient initialization with custom parameters."""
    client = HTTPClient(timeout=30, max_retries=5)

    assert client.timeout == 30
    assert client.max_retries == 5
    assert client._client is not None

    await client.close()


@pytest.mark.asyncio
async def test_http_client_context_manager() -> None:
    """Test HTTPClient as async context manager."""
    async with HTTPClient() as client:
        assert client._client is not None

    # Client should be closed after context exit
    # We can't easily test this without accessing internals


@pytest.mark.asyncio
async def test_get_request_success(http_client: HTTPClient) -> None:
    """Test successful GET request."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await http_client.get("https://example.com/test")

        assert response == mock_response
        mock_request.assert_called_once_with("GET", "https://example.com/test")
        mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_head_request_success(http_client: HTTPClient) -> None:
    """Test successful HEAD request."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await http_client.head("https://example.com/test")

        assert response == mock_response
        mock_request.assert_called_once_with("HEAD", "https://example.com/test")


@pytest.mark.asyncio
async def test_post_request_success(http_client: HTTPClient) -> None:
    """Test successful POST request."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await http_client.post("https://example.com/test", json={"key": "value"})

        assert response == mock_response
        mock_request.assert_called_once_with(
            "POST", "https://example.com/test", json={"key": "value"}
        )


@pytest.mark.asyncio
async def test_retry_on_timeout(http_client: HTTPClient) -> None:
    """Test retry logic on timeout errors."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        # First two attempts timeout, third succeeds
        mock_request.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            mock_response,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            response = await http_client.get("https://example.com/test")

        assert response == mock_response
        assert mock_request.call_count == 3


@pytest.mark.asyncio
async def test_retry_on_server_error(http_client: HTTPClient) -> None:
    """Test retry logic on 5xx server errors."""
    error_response = Mock(spec=httpx.Response)
    error_response.status_code = 503

    success_response = Mock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        # First two attempts return 503, third succeeds
        mock_request.side_effect = [error_response, error_response, success_response]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            response = await http_client.get("https://example.com/test")

        assert response == success_response
        assert mock_request.call_count == 3


@pytest.mark.asyncio
async def test_max_retries_exceeded(http_client: HTTPClient) -> None:
    """Test that NetworkError is raised after max retries."""
    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = httpx.TimeoutException("Timeout")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(NetworkError, match="Network error after .* retries"):
                await http_client.get("https://example.com/test")

        # Should try max_retries + 1 times (initial + retries)
        assert mock_request.call_count == http_client.max_retries + 1


@pytest.mark.asyncio
async def test_client_error_no_retry(http_client: HTTPClient) -> None:
    """Test that 4xx errors are not retried."""
    error_response = Mock(spec=httpx.Response)
    error_response.status_code = 404

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = error_response
        mock_request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=error_response
        )

        with pytest.raises(NetworkError, match="HTTP error 404"):
            await http_client.get("https://example.com/test")

        # Should only try once (no retries for client errors)
        assert mock_request.call_count == 1


@pytest.mark.asyncio
async def test_exponential_backoff(http_client: HTTPClient) -> None:
    """Test that exponential backoff is used for retries."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    sleep_times = []

    async def mock_sleep(seconds: float) -> None:
        sleep_times.append(seconds)

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        # First three attempts timeout, fourth succeeds
        mock_request.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            mock_response,
        ]

        with patch("asyncio.sleep", side_effect=mock_sleep):
            response = await http_client.get("https://example.com/test")

        assert response == mock_response
        # Check exponential backoff: 2^0=1, 2^1=2, 2^2=4
        assert sleep_times == [1, 2, 4]


@pytest.mark.asyncio
async def test_download_stream_new_file(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test streaming download to new file."""
    dest_file = tmp_path / "test_download.bin"
    test_data = b"Hello, World!" * 1000  # 13KB of data

    # Mock streaming response
    mock_response = AsyncMock()
    mock_response.headers = {"content-length": str(len(test_data))}
    mock_response.raise_for_status = Mock()

    # Simulate chunked data
    chunk_size = 8192
    chunks = [test_data[i : i + chunk_size] for i in range(0, len(test_data), chunk_size)]

    async def aiter_bytes(chunk_size: int) -> bytes:
        for chunk in chunks:
            yield chunk

    mock_response.aiter_bytes = aiter_bytes

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        await http_client.download_stream("https://example.com/file.bin", dest_file)

    # Verify file was created and contains correct data
    assert dest_file.exists()
    assert dest_file.read_bytes() == test_data


@pytest.mark.asyncio
async def test_download_stream_with_progress(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test streaming download with progress callback."""
    dest_file = tmp_path / "test_download.bin"
    test_data = b"X" * 10000

    progress_calls = []

    def progress_callback(downloaded: int, total: int) -> None:
        progress_calls.append((downloaded, total))

    # Mock streaming response
    mock_response = AsyncMock()
    mock_response.headers = {"content-length": str(len(test_data))}
    mock_response.raise_for_status = Mock()

    # Simulate chunked data
    chunk_size = 8192
    chunks = [test_data[i : i + chunk_size] for i in range(0, len(test_data), chunk_size)]

    async def aiter_bytes(chunk_size: int) -> bytes:
        for chunk in chunks:
            yield chunk

    mock_response.aiter_bytes = aiter_bytes

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        await http_client.download_stream(
            "https://example.com/file.bin", dest_file, progress_callback=progress_callback
        )

    # Verify progress callback was called
    assert len(progress_calls) > 0
    # Last call should have total bytes downloaded
    assert progress_calls[-1][0] == len(test_data)


@pytest.mark.asyncio
async def test_download_stream_resume(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test resuming partial download."""
    dest_file = tmp_path / "test_download.bin"

    # Create partial file
    partial_data = b"Partial"
    dest_file.write_bytes(partial_data)
    partial_size = len(partial_data)

    # Remaining data
    remaining_data = b" Download"
    total_data = partial_data + remaining_data

    # Mock streaming response
    mock_response = AsyncMock()
    mock_response.headers = {"content-length": str(len(remaining_data))}
    mock_response.raise_for_status = Mock()

    async def aiter_bytes(chunk_size: int) -> bytes:
        yield remaining_data

    mock_response.aiter_bytes = aiter_bytes

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        await http_client.download_stream("https://example.com/file.bin", dest_file, resume=True)

    # Verify file contains both partial and new data
    assert dest_file.read_bytes() == total_data

    # Verify Range header was used
    call_args = mock_stream.call_args
    assert call_args[1]["headers"]["Range"] == f"bytes={partial_size}-"


@pytest.mark.asyncio
async def test_download_stream_no_resume(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test download without resume overwrites existing file."""
    dest_file = tmp_path / "test_download.bin"

    # Create existing file
    dest_file.write_bytes(b"Old data")

    # New data
    new_data = b"New data"

    # Mock streaming response
    mock_response = AsyncMock()
    mock_response.headers = {"content-length": str(len(new_data))}
    mock_response.raise_for_status = Mock()

    async def aiter_bytes(chunk_size: int) -> bytes:
        yield new_data

    mock_response.aiter_bytes = aiter_bytes

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        await http_client.download_stream("https://example.com/file.bin", dest_file, resume=False)

    # Verify file was overwritten
    assert dest_file.read_bytes() == new_data


@pytest.mark.asyncio
async def test_download_stream_network_error(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test that NetworkError is raised on download failure."""
    dest_file = tmp_path / "test_download.bin"

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(NetworkError, match="Download failed"):
            await http_client.download_stream("https://example.com/file.bin", dest_file)


@pytest.mark.asyncio
async def test_download_stream_without_content_length(
    http_client: HTTPClient, tmp_path: Path
) -> None:
    """Test streaming download when server doesn't provide content-length."""
    dest_file = tmp_path / "test_download.bin"
    test_data = b"Data without content-length"

    # Mock streaming response without content-length header
    mock_response = AsyncMock()
    mock_response.headers = {}  # No content-length
    mock_response.raise_for_status = Mock()

    async def aiter_bytes(chunk_size: int) -> bytes:
        yield test_data

    mock_response.aiter_bytes = aiter_bytes

    progress_calls = []

    def progress_callback(downloaded: int, total: int) -> None:
        progress_calls.append((downloaded, total))

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        await http_client.download_stream(
            "https://example.com/file.bin", dest_file, progress_callback=progress_callback
        )

    # Verify file was created
    assert dest_file.exists()
    assert dest_file.read_bytes() == test_data

    # Verify progress callback was called with total_size=0
    assert len(progress_calls) > 0
    assert progress_calls[-1][1] == 0  # total_size should be 0


@pytest.mark.asyncio
async def test_download_stream_http_error(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test that NetworkError is raised on HTTP error during download."""
    dest_file = tmp_path / "test_download.bin"

    error_response = Mock(spec=httpx.Response)
    error_response.status_code = 404

    mock_response = Mock()  # Use regular Mock, not AsyncMock
    mock_response.headers = {"content-length": "100"}
    mock_response.raise_for_status = Mock(
        side_effect=httpx.HTTPStatusError("Not found", request=Mock(), response=error_response)
    )

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        with pytest.raises(NetworkError, match="HTTP error 404 during download"):
            await http_client.download_stream("https://example.com/file.bin", dest_file)


@pytest.mark.asyncio
async def test_download_stream_file_write_error(http_client: HTTPClient, tmp_path: Path) -> None:
    """Test that NetworkError is raised on file write error."""
    # Use a directory as the destination to cause OSError
    dest_file = tmp_path / "directory"
    dest_file.mkdir()

    test_data = b"Test data"

    # Mock streaming response
    mock_response = AsyncMock()
    mock_response.headers = {"content-length": str(len(test_data))}
    mock_response.raise_for_status = Mock()

    async def aiter_bytes(chunk_size: int) -> bytes:
        yield test_data

    mock_response.aiter_bytes = aiter_bytes

    with patch.object(http_client._client, "stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        with pytest.raises(NetworkError, match="File write error"):
            await http_client.download_stream("https://example.com/file.bin", dest_file)


@pytest.mark.asyncio
async def test_retry_on_connect_error(http_client: HTTPClient) -> None:
    """Test retry logic on connection errors."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        # First attempt fails with connection error, second succeeds
        mock_request.side_effect = [httpx.ConnectError("Connection failed"), mock_response]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            response = await http_client.get("https://example.com/test")

        assert response == mock_response
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_retry_on_read_error(http_client: HTTPClient) -> None:
    """Test retry logic on read errors."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        # First attempt fails with read error, second succeeds
        mock_request.side_effect = [httpx.ReadError("Read failed"), mock_response]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            response = await http_client.get("https://example.com/test")

        assert response == mock_response
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_server_error_on_last_retry(http_client: HTTPClient) -> None:
    """Test that NetworkError is raised when server error persists through all retries."""
    error_response = Mock(spec=httpx.Response)
    error_response.status_code = 500

    with patch.object(http_client._client, "request", new_callable=AsyncMock) as mock_request:
        # All attempts return 500 error
        mock_request.return_value = error_response

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(NetworkError, match="Server error 500 after .* retries"):
                await http_client.get("https://example.com/test")

        # Should try max_retries + 1 times
        assert mock_request.call_count == http_client.max_retries + 1
