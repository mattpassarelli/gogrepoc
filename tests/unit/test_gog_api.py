"""Unit tests for the GOGAPIService class."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import xml.etree.ElementTree as ET

from gogrepoc.services.gog_api import GOGAPIService
from gogrepoc.services.auth import AuthService
from gogrepoc.core.models import Token
from gogrepoc.core.exceptions import NetworkError, AuthError
from gogrepoc.infrastructure.http_client import HTTPClient


@pytest.fixture
def mock_http_client():
    """Create a mock HTTPClient instance."""
    client = Mock(spec=HTTPClient)
    return client


@pytest.fixture
def mock_auth_service():
    """Create a mock AuthService instance."""
    service = Mock(spec=AuthService)
    return service


@pytest.fixture
def gog_api_service(mock_http_client, mock_auth_service):
    """Create a GOGAPIService instance with mocked dependencies."""
    return GOGAPIService(mock_http_client, mock_auth_service)


@pytest.fixture
def sample_token():
    """Create a sample token for testing."""
    return Token(
        access_token="test_access_token_123",
        refresh_token="test_refresh_token_456",
        expires_at=datetime.now() + timedelta(hours=1),
        user_id="test_user_123",
    )


class TestGOGAPIServiceInit:
    """Tests for GOGAPIService initialization."""

    def test_init_with_dependencies(self, mock_http_client, mock_auth_service):
        """Test initialization with HTTP client and auth service."""
        service = GOGAPIService(mock_http_client, mock_auth_service)
        
        assert service.http_client == mock_http_client
        assert service.auth_service == mock_auth_service


    def test_api_endpoints_defined(self, gog_api_service):
        """Test that GOG API endpoints are defined."""
        assert hasattr(GOGAPIService, "GOG_ACCOUNT_URL")
        assert hasattr(GOGAPIService, "GOG_GAMES_AJAX_URL")
        assert hasattr(GOGAPIService, "GOG_GAME_DETAILS_URL")
        assert hasattr(GOGAPIService, "GOG_CONTENT_SYSTEM_URL")
        
        assert "gog.com" in GOGAPIService.GOG_ACCOUNT_URL
        assert "getFilteredProducts" in GOGAPIService.GOG_GAMES_AJAX_URL
        assert "gameDetails" in GOGAPIService.GOG_GAME_DETAILS_URL

    def test_media_types_defined(self, gog_api_service):
        """Test that media type constants are defined."""
        assert hasattr(GOGAPIService, "MEDIA_TYPE_GAME")
        assert hasattr(GOGAPIService, "MEDIA_TYPE_MOVIE")
        assert GOGAPIService.MEDIA_TYPE_GAME == "1"
        assert GOGAPIService.MEDIA_TYPE_MOVIE == "2"


class TestGetGamesList:
    """Tests for get_games_list method."""

    @pytest.mark.asyncio
    async def test_get_games_list_first_page(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching first page of games list."""
        # Mock auth service to return valid token
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "products": [
                {"id": 1, "title": "Game 1"},
                {"id": 2, "title": "Game 2"},
            ],
            "page": 1,
            "totalPages": 5,
            "totalProducts": 42,
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        # Fetch games list
        result = await gog_api_service.get_games_list(page=1)
        
        # Verify result
        assert result["page"] == 1
        assert result["totalPages"] == 5
        assert result["totalProducts"] == 42
        assert len(result["products"]) == 2
        assert result["products"][0]["id"] == 1
        
        # Verify HTTP client was called correctly
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert GOGAPIService.GOG_GAMES_AJAX_URL in call_args[0]
        assert call_args[1]["params"]["page"] == "1"
        assert call_args[1]["params"]["mediaType"] == GOGAPIService.MEDIA_TYPE_GAME
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {sample_token.access_token}"

    @pytest.mark.asyncio
    async def test_get_games_list_specific_page(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching specific page of games list."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "products": [{"id": 10, "title": "Game 10"}],
            "page": 3,
            "totalPages": 5,
            "totalProducts": 42,
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_games_list(page=3)
        
        assert result["page"] == 3
        
        # Verify page parameter was passed correctly
        call_args = mock_http_client.get.call_args
        assert call_args[1]["params"]["page"] == "3"


    @pytest.mark.asyncio
    async def test_get_games_list_empty_page(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching empty page of games list."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "products": [],
            "page": 10,
            "totalPages": 5,
            "totalProducts": 42,
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_games_list(page=10)
        
        assert len(result["products"]) == 0
        assert result["page"] == 10

    @pytest.mark.asyncio
    async def test_get_games_list_auth_error(self, gog_api_service, mock_http_client, mock_auth_service):
        """Test games list fetch when authentication fails."""
        mock_auth_service.get_valid_token = AsyncMock(side_effect=AuthError("Token expired"))
        
        with pytest.raises(AuthError):
            await gog_api_service.get_games_list()

    @pytest.mark.asyncio
    async def test_get_games_list_network_error(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test games list fetch when network error occurs."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))
        
        with pytest.raises(Exception) as exc_info:
            await gog_api_service.get_games_list()
        
        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_games_list_pagination_info(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test that pagination information is correctly returned."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "products": [{"id": i, "title": f"Game {i}"} for i in range(1, 21)],
            "page": 2,
            "totalPages": 10,
            "totalProducts": 195,
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_games_list(page=2)
        
        assert result["page"] == 2
        assert result["totalPages"] == 10
        assert result["totalProducts"] == 195
        assert len(result["products"]) == 20


class TestGetGameDetails:
    """Tests for get_game_details method."""

    @pytest.mark.asyncio
    async def test_get_game_details_success(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching game details successfully."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "title": "Test Game",
            "backgroundImage": "https://example.com/bg.jpg",
            "cdKey": "XXXX-XXXX-XXXX",
            "textInformation": "Game information",
            "downloads": [
                {"name": "installer.exe", "size": 1024000},
            ],
            "extras": [
                {"name": "manual.pdf", "size": 5000},
            ],
            "dlcs": [],
            "tags": ["rpg", "adventure"],
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_game_details(game_id=123)
        
        assert result["title"] == "Test Game"
        assert result["cdKey"] == "XXXX-XXXX-XXXX"
        assert len(result["downloads"]) == 1
        assert len(result["extras"]) == 1
        assert "rpg" in result["tags"]
        
        # Verify HTTP client was called correctly
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert "123.json" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {sample_token.access_token}"


    @pytest.mark.asyncio
    async def test_get_game_details_with_multiple_downloads(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching game details with multiple downloads."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "title": "Multi-Platform Game",
            "downloads": [
                {"name": "installer_windows.exe", "os": "windows"},
                {"name": "installer_linux.sh", "os": "linux"},
                {"name": "installer_mac.dmg", "os": "mac"},
            ],
            "extras": [],
            "dlcs": [],
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_game_details(game_id=456)
        
        assert len(result["downloads"]) == 3
        assert result["downloads"][0]["os"] == "windows"
        assert result["downloads"][1]["os"] == "linux"
        assert result["downloads"][2]["os"] == "mac"

    @pytest.mark.asyncio
    async def test_get_game_details_with_dlcs(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching game details with DLCs."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "title": "Game with DLC",
            "downloads": [],
            "extras": [],
            "dlcs": [
                {"id": 1, "title": "DLC 1"},
                {"id": 2, "title": "DLC 2"},
            ],
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_game_details(game_id=789)
        
        assert len(result["dlcs"]) == 2
        assert result["dlcs"][0]["title"] == "DLC 1"

    @pytest.mark.asyncio
    async def test_get_game_details_auth_error(self, gog_api_service, mock_http_client, mock_auth_service):
        """Test game details fetch when authentication fails."""
        mock_auth_service.get_valid_token = AsyncMock(side_effect=AuthError("Invalid token"))
        
        with pytest.raises(AuthError):
            await gog_api_service.get_game_details(game_id=123)

    @pytest.mark.asyncio
    async def test_get_game_details_network_error(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test game details fetch when network error occurs."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        mock_http_client.get = AsyncMock(side_effect=Exception("Connection timeout"))
        
        with pytest.raises(Exception) as exc_info:
            await gog_api_service.get_game_details(game_id=123)
        
        assert "Connection timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_game_details_no_serial_key(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test fetching game details when no serial key is present."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "title": "Game Without Key",
            "downloads": [],
            "extras": [],
            "dlcs": [],
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_game_details(game_id=999)
        
        assert "cdKey" not in result or result.get("cdKey") is None


class TestGetDownloadLink:
    """Tests for get_download_link method."""

    @pytest.mark.asyncio
    async def test_get_download_link_with_downlink_key(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test resolving download link with 'downlink' key in response."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "downlink": "https://cdn.gog.com/downloads/game_installer.exe?token=abc123"
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_download_link("/downloads/game/123")
        
        assert result == "https://cdn.gog.com/downloads/game_installer.exe?token=abc123"
        
        # Verify HTTP client was called correctly
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert "/downloads/game/123" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {sample_token.access_token}"


    @pytest.mark.asyncio
    async def test_get_download_link_with_url_key(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test resolving download link with 'url' key in response."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "url": "https://cdn.gog.com/downloads/another_game.exe"
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_download_link("/downloads/game/456")
        
        assert result == "https://cdn.gog.com/downloads/another_game.exe"

    @pytest.mark.asyncio
    async def test_get_download_link_with_full_url_href(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test resolving download link when href is already a full URL."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "downlink": "https://cdn.gog.com/final_url.exe"
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_download_link("https://www.gog.com/downloads/game/789")
        
        assert result == "https://cdn.gog.com/final_url.exe"
        
        # Verify the full URL was used as-is
        call_args = mock_http_client.get.call_args
        assert call_args[0][0] == "https://www.gog.com/downloads/game/789"

    @pytest.mark.asyncio
    async def test_get_download_link_via_redirect(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test resolving download link via HTTP redirect."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        # Mock response that's not JSON but has a redirect URL
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.url = "https://cdn.gog.com/redirected_download.exe"
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_download_link("/downloads/game/redirect")
        
        assert result == "https://cdn.gog.com/redirected_download.exe"

    @pytest.mark.asyncio
    async def test_get_download_link_unknown_format(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test resolving download link with unknown response format."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "unknown_key": "some_value"
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(NetworkError) as exc_info:
            await gog_api_service.get_download_link("/downloads/game/unknown")
        
        assert "Could not find download URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_download_link_with_any_url_value(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test resolving download link by finding any URL-like value."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "some_key": "not a url",
            "another_key": "https://cdn.gog.com/found_url.exe",
            "third_key": 12345
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.get_download_link("/downloads/game/any")
        
        assert result == "https://cdn.gog.com/found_url.exe"

    @pytest.mark.asyncio
    async def test_get_download_link_auth_error(self, gog_api_service, mock_http_client, mock_auth_service):
        """Test download link resolution when authentication fails."""
        mock_auth_service.get_valid_token = AsyncMock(side_effect=AuthError("Token invalid"))
        
        with pytest.raises(AuthError):
            await gog_api_service.get_download_link("/downloads/game/123")

    @pytest.mark.asyncio
    async def test_get_download_link_network_error(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test download link resolution when network error occurs."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        mock_http_client.get = AsyncMock(side_effect=Exception("Network failure"))
        
        with pytest.raises(Exception) as exc_info:
            await gog_api_service.get_download_link("/downloads/game/123")
        
        assert "Network failure" in str(exc_info.value)


class TestFetchFileInfo:
    """Tests for fetch_file_info method."""

    @pytest.mark.asyncio
    async def test_fetch_file_info_success(self, gog_api_service, mock_http_client):
        """Test fetching file info successfully."""
        mock_response = Mock()
        mock_response.headers = {
            "content-length": "1048576",
            "content-type": "application/octet-stream",
            "last-modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            "etag": '"abc123"',
        }
        mock_http_client.head = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_file_info("https://cdn.gog.com/file.exe")
        
        assert result["size"] == 1048576
        assert result["content_type"] == "application/octet-stream"
        assert result["last_modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
        assert result["etag"] == '"abc123"'
        
        # Verify HEAD request was made
        mock_http_client.head.assert_called_once_with("https://cdn.gog.com/file.exe")


    @pytest.mark.asyncio
    async def test_fetch_file_info_missing_headers(self, gog_api_service, mock_http_client):
        """Test fetching file info when some headers are missing."""
        mock_response = Mock()
        mock_response.headers = {
            "content-length": "2048",
        }
        mock_http_client.head = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_file_info("https://cdn.gog.com/file.bin")
        
        assert result["size"] == 2048
        assert result["content_type"] == ""
        assert result["last_modified"] is None
        assert result["etag"] is None

    @pytest.mark.asyncio
    async def test_fetch_file_info_no_content_length(self, gog_api_service, mock_http_client):
        """Test fetching file info when content-length is missing."""
        mock_response = Mock()
        mock_response.headers = {
            "content-type": "text/plain",
        }
        mock_http_client.head = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_file_info("https://cdn.gog.com/file.txt")
        
        assert result["size"] == 0
        assert result["content_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_fetch_file_info_network_error(self, gog_api_service, mock_http_client):
        """Test fetching file info when network error occurs."""
        mock_http_client.head = AsyncMock(side_effect=Exception("Connection refused"))
        
        with pytest.raises(Exception) as exc_info:
            await gog_api_service.fetch_file_info("https://cdn.gog.com/file.exe")
        
        assert "Connection refused" in str(exc_info.value)


class TestFetchMD5XML:
    """Tests for fetch_md5_xml method."""

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_success(self, gog_api_service, mock_http_client):
        """Test fetching and parsing MD5 XML successfully."""
        xml_content = """<?xml version="1.0"?>
<files>
  <file name="setup_game.exe" md5="abc123def456" />
  <file name="setup_game-1.bin" md5="789ghi012jkl" />
  <file name="setup_game-2.bin" md5="345mno678pqr" />
</files>"""
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/game.xml")
        
        assert result is not None
        assert len(result) == 3
        assert result["setup_game.exe"] == "abc123def456"
        assert result["setup_game-1.bin"] == "789ghi012jkl"
        assert result["setup_game-2.bin"] == "345mno678pqr"
        
        # Verify GET request was made
        mock_http_client.get.assert_called_once_with("https://cdn.gog.com/game.xml")

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_single_file(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML with single file."""
        xml_content = """<?xml version="1.0"?>
<files>
  <file name="installer.exe" md5="singlefile123" />
</files>"""
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/single.xml")
        
        assert result is not None
        assert len(result) == 1
        assert result["installer.exe"] == "singlefile123"

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_empty(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML with no file entries."""
        xml_content = """<?xml version="1.0"?>
<files>
</files>"""
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/empty.xml")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_malformed(self, gog_api_service, mock_http_client):
        """Test fetching malformed MD5 XML."""
        xml_content = "This is not valid XML <unclosed tag"
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/malformed.xml")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_404_not_found(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML when file is not found (404)."""
        mock_http_client.get = AsyncMock(side_effect=NetworkError("404 Not Found"))
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/notfound.xml")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_network_error_non_404(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML when non-404 network error occurs."""
        mock_http_client.get = AsyncMock(side_effect=NetworkError("500 Internal Server Error"))
        
        with pytest.raises(NetworkError) as exc_info:
            await gog_api_service.fetch_md5_xml("https://cdn.gog.com/error.xml")
        
        assert "500" in str(exc_info.value)


    @pytest.mark.asyncio
    async def test_fetch_md5_xml_missing_attributes(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML with missing name or md5 attributes."""
        xml_content = """<?xml version="1.0"?>
<files>
  <file name="valid.exe" md5="validmd5" />
  <file name="no_md5.exe" />
  <file md5="no_name_md5" />
  <file />
</files>"""
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/partial.xml")
        
        # Only the valid entry should be included
        assert result is not None
        assert len(result) == 1
        assert result["valid.exe"] == "validmd5"

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_nested_structure(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML with nested file elements."""
        xml_content = """<?xml version="1.0"?>
<root>
  <files>
    <file name="nested1.exe" md5="nested1md5" />
  </files>
  <other>
    <file name="nested2.bin" md5="nested2md5" />
  </other>
</root>"""
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/nested.xml")
        
        # Should find all file elements regardless of nesting
        assert result is not None
        assert len(result) == 2
        assert result["nested1.exe"] == "nested1md5"
        assert result["nested2.bin"] == "nested2md5"

    @pytest.mark.asyncio
    async def test_fetch_md5_xml_unexpected_error(self, gog_api_service, mock_http_client):
        """Test fetching MD5 XML when unexpected error occurs."""
        mock_http_client.get = AsyncMock(side_effect=Exception("Unexpected error"))
        
        result = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/unexpected.xml")
        
        # Should return None for unexpected errors
        assert result is None


class TestGOGAPIServiceIntegration:
    """Integration tests for complete GOG API workflows."""

    @pytest.mark.asyncio
    async def test_complete_game_fetch_workflow(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test complete workflow of fetching games list and details."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        # Mock games list response
        games_list_response = Mock()
        games_list_response.json.return_value = {
            "products": [
                {"id": 1, "title": "Game 1"},
                {"id": 2, "title": "Game 2"},
            ],
            "page": 1,
            "totalPages": 1,
            "totalProducts": 2,
        }
        
        # Mock game details response
        game_details_response = Mock()
        game_details_response.json.return_value = {
            "title": "Game 1",
            "downloads": [{"name": "installer.exe"}],
            "extras": [],
            "dlcs": [],
        }
        
        # Setup mock to return different responses
        mock_http_client.get = AsyncMock(side_effect=[games_list_response, game_details_response])
        
        # Fetch games list
        games = await gog_api_service.get_games_list()
        assert len(games["products"]) == 2
        
        # Fetch details for first game
        details = await gog_api_service.get_game_details(games["products"][0]["id"])
        assert details["title"] == "Game 1"
        assert len(details["downloads"]) == 1

    @pytest.mark.asyncio
    async def test_download_workflow(self, gog_api_service, mock_http_client, mock_auth_service, sample_token):
        """Test complete download workflow: get link, fetch info, download."""
        mock_auth_service.get_valid_token = AsyncMock(return_value=sample_token)
        
        # Mock download link response
        link_response = Mock()
        link_response.json.return_value = {
            "downlink": "https://cdn.gog.com/installer.exe"
        }
        
        # Mock file info response
        info_response = Mock()
        info_response.headers = {
            "content-length": "1048576",
            "content-type": "application/octet-stream",
        }
        
        mock_http_client.get = AsyncMock(return_value=link_response)
        mock_http_client.head = AsyncMock(return_value=info_response)
        
        # Get download link
        download_url = await gog_api_service.get_download_link("/downloads/game/123")
        assert download_url == "https://cdn.gog.com/installer.exe"
        
        # Fetch file info
        file_info = await gog_api_service.fetch_file_info(download_url)
        assert file_info["size"] == 1048576
        assert file_info["content_type"] == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_md5_verification_workflow(self, gog_api_service, mock_http_client):
        """Test workflow of fetching MD5 checksums for verification."""
        xml_content = """<?xml version="1.0"?>
<files>
  <file name="installer.exe" md5="abc123" />
  <file name="installer-1.bin" md5="def456" />
</files>"""
        
        mock_response = Mock()
        mock_response.text = xml_content
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        # Fetch MD5 checksums
        md5_dict = await gog_api_service.fetch_md5_xml("https://cdn.gog.com/game.xml")
        
        assert md5_dict is not None
        assert "installer.exe" in md5_dict
        assert "installer-1.bin" in md5_dict
        assert md5_dict["installer.exe"] == "abc123"
        assert md5_dict["installer-1.bin"] == "def456"
