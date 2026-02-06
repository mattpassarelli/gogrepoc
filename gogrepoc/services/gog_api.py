"""GOG API service for interacting with GOG's web services.

This module provides the GOGAPIService class for handling all interactions
with the GOG API, including fetching game lists, game details, download links,
and file metadata.
"""

import logging
from typing import Optional

from gogrepoc.core.exceptions import NetworkError
from gogrepoc.infrastructure.http_client import HTTPClient
from gogrepoc.services.auth import AuthService

logger = logging.getLogger(__name__)


class GOGAPIService:
    """Handles all interactions with GOG API.

    This service provides methods for:
    - Fetching paginated game lists
    - Retrieving detailed game information
    - Resolving download URLs
    - Fetching file metadata
    - Retrieving MD5 checksums

    Attributes:
        http_client: HTTP client for API requests
        auth_service: Authentication service for token management
    """

    # GOG API Endpoints
    GOG_ACCOUNT_URL = "https://www.gog.com/account"
    GOG_GAMES_AJAX_URL = f"{GOG_ACCOUNT_URL}/getFilteredProducts"
    GOG_GAME_DETAILS_URL = "https://www.gog.com/account/gameDetails"
    GOG_CONTENT_SYSTEM_URL = "https://content-system.gog.com"
    
    # Media types
    MEDIA_TYPE_GAME = "1"
    MEDIA_TYPE_MOVIE = "2"

    def __init__(self, http_client: HTTPClient, auth_service: AuthService):
        """Initialize GOGAPIService with dependencies.

        Args:
            http_client: HTTP client for making API requests
            auth_service: Authentication service for token management
        """
        self.http_client = http_client
        self.auth_service = auth_service


    async def get_games_list(self, page: int = 1) -> dict:
        """Fetch paginated games list from GOG account.

        Retrieves a page of games from the user's GOG library. The GOG API
        returns games in pages, so this method should be called multiple times
        to fetch all games.

        Args:
            page: Page number to fetch (1-indexed, default: 1)

        Returns:
            Dictionary containing:
                - 'products': List of game objects with basic info
                - 'page': Current page number
                - 'totalPages': Total number of pages
                - 'totalProducts': Total number of products in library

        Raises:
            NetworkError: If the API request fails
            AuthError: If authentication token is invalid or expired
        """
        logger.info(f"Fetching games list page {page}")

        # Get valid authentication token
        token = await self.auth_service.get_valid_token()

        # Prepare request parameters
        params = {
            "mediaType": self.MEDIA_TYPE_GAME,
            "page": str(page),
        }

        # Prepare authorization header
        headers = {
            "Authorization": f"Bearer {token.access_token}",
        }

        try:
            # Make API request
            response = await self.http_client.get(
                self.GOG_GAMES_AJAX_URL,
                params=params,
                headers=headers,
            )

            # Parse JSON response
            data = response.json()

            logger.info(
                f"Fetched page {page}: {len(data.get('products', []))} games, "
                f"total pages: {data.get('totalPages', 'unknown')}"
            )

            return data

        except Exception as e:
            logger.error(f"Failed to fetch games list page {page}: {e}")
            raise

    async def get_game_details(self, game_id: int) -> dict:
        """Fetch detailed game information including downloads and extras.

        Retrieves comprehensive information about a specific game, including:
        - All available downloads (installers, DLCs, patches)
        - Extra files (manuals, artwork, soundtracks)
        - Game metadata (title, images, changelog)
        - Serial keys

        Args:
            game_id: GOG game ID

        Returns:
            Dictionary containing detailed game information with keys:
                - 'title': Game title
                - 'backgroundImage': Background image URL
                - 'cdKey': Serial key if available
                - 'textInformation': Game information text
                - 'downloads': List of download objects
                - 'extras': List of extra file objects
                - 'dlcs': List of DLC objects
                - 'tags': List of game tags
                - And more game metadata

        Raises:
            NetworkError: If the API request fails
            AuthError: If authentication token is invalid or expired
        """
        logger.info(f"Fetching details for game ID {game_id}")

        # Get valid authentication token
        token = await self.auth_service.get_valid_token()

        # Prepare request URL with game ID
        url = f"{self.GOG_GAME_DETAILS_URL}/{game_id}.json"

        # Prepare authorization header
        headers = {
            "Authorization": f"Bearer {token.access_token}",
        }

        try:
            # Make API request
            response = await self.http_client.get(url, headers=headers)

            # Parse JSON response
            data = response.json()

            logger.debug(
                f"Fetched details for game {game_id}: "
                f"{data.get('title', 'unknown')}, "
                f"{len(data.get('downloads', []))} downloads, "
                f"{len(data.get('extras', []))} extras"
            )

            return data

        except Exception as e:
            logger.error(f"Failed to fetch game details for ID {game_id}: {e}")
            raise

    async def get_download_link(self, href: str) -> str:
        """Resolve download URL from GOG API href.

        GOG API returns relative hrefs that need to be resolved to actual
        download URLs. This method handles the resolution and returns a
        direct download URL. The URLs may expire after some time.

        Args:
            href: Relative API href (e.g., '/downloads/game/file_id')

        Returns:
            Direct download URL as a string

        Raises:
            NetworkError: If the API request fails or URL cannot be resolved
            AuthError: If authentication token is invalid or expired
        """
        logger.debug(f"Resolving download link for href: {href}")

        # Get valid authentication token
        token = await self.auth_service.get_valid_token()

        # Construct full URL
        # If href is already a full URL, use it as-is
        if href.startswith("http://") or href.startswith("https://"):
            url = href
        else:
            # Construct URL from GOG account base
            url = f"{self.GOG_ACCOUNT_URL}{href}"

        # Prepare authorization header
        headers = {
            "Authorization": f"Bearer {token.access_token}",
        }

        try:
            # Make API request - GOG API typically returns JSON with download URL
            response = await self.http_client.get(url, headers=headers)

            # Try to parse as JSON first (typical GOG API response)
            try:
                data = response.json()
                
                # GOG API may return different structures
                # Common patterns: {'downlink': 'url'} or {'url': 'url'}
                if "downlink" in data:
                    download_url = data["downlink"]
                elif "url" in data:
                    download_url = data["url"]
                else:
                    # If no known key, try to find any URL-like value
                    download_url = None
                    for value in data.values():
                        if isinstance(value, str) and value.startswith("http"):
                            download_url = value
                            break
                    
                    if not download_url:
                        raise NetworkError(f"Could not find download URL in response: {data}")

                logger.debug(f"Resolved download link: {download_url[:100]}...")
                return download_url

            except ValueError:
                # Response is not JSON - might be a redirect or direct URL
                # Check if we got redirected to a download URL
                if response.url and str(response.url) != url:
                    download_url = str(response.url)
                    logger.debug(f"Resolved download link via redirect: {download_url[:100]}...")
                    return download_url
                else:
                    raise NetworkError(f"Unexpected response format for download link: {href}")

        except Exception as e:
            logger.error(f"Failed to resolve download link for {href}: {e}")
            raise

    async def fetch_file_info(self, url: str) -> dict:
        """Fetch file metadata using HEAD request.

        Retrieves file information without downloading the entire file.
        This is useful for getting file size, content type, and other
        metadata before starting a download.

        Args:
            url: Direct download URL

        Returns:
            Dictionary containing file metadata:
                - 'size': File size in bytes (int)
                - 'content_type': MIME type of the file (str)
                - 'last_modified': Last modification date if available (str or None)
                - 'etag': ETag header if available (str or None)

        Raises:
            NetworkError: If the HEAD request fails
        """
        logger.debug(f"Fetching file info for URL: {url[:100]}...")

        try:
            # Make HEAD request to get metadata without downloading
            response = await self.http_client.head(url)

            # Extract metadata from headers
            file_info = {
                "size": int(response.headers.get("content-length", 0)),
                "content_type": response.headers.get("content-type", ""),
                "last_modified": response.headers.get("last-modified"),
                "etag": response.headers.get("etag"),
            }

            logger.debug(
                f"File info: size={file_info['size']} bytes, "
                f"type={file_info['content_type']}"
            )

            return file_info

        except Exception as e:
            logger.error(f"Failed to fetch file info: {e}")
            raise

    async def fetch_md5_xml(self, url: str) -> Optional[dict]:
        """Fetch and parse MD5 checksum XML file.

        GOG provides MD5 checksums for some files in XML format. This method
        fetches and parses the XML to extract checksums for verification.

        Args:
            url: URL to the MD5 XML file (typically ends with .xml)

        Returns:
            Dictionary mapping file names to their MD5 checksums, or None if
            the XML is not available or cannot be parsed. Example:
            {
                'setup_game.exe': 'abc123...',
                'setup_game-1.bin': 'def456...',
            }

        Raises:
            NetworkError: If the request fails with a non-404 error
        """
        logger.debug(f"Fetching MD5 XML from: {url[:100]}...")

        try:
            # Make GET request to fetch XML
            response = await self.http_client.get(url)

            # Parse XML content
            xml_content = response.text

            # Simple XML parsing for MD5 checksums
            # GOG MD5 XML format typically looks like:
            # <?xml version="1.0"?>
            # <files>
            #   <file name="setup_game.exe" md5="abc123..." />
            #   <file name="setup_game-1.bin" md5="def456..." />
            # </files>

            import xml.etree.ElementTree as ET

            try:
                root = ET.fromstring(xml_content)
                md5_dict = {}

                # Extract file elements and their MD5 attributes
                for file_elem in root.findall(".//file"):
                    name = file_elem.get("name")
                    md5 = file_elem.get("md5")

                    if name and md5:
                        md5_dict[name] = md5

                if md5_dict:
                    logger.debug(f"Parsed {len(md5_dict)} MD5 checksums from XML")
                    return md5_dict
                else:
                    logger.warning("MD5 XML contains no file entries")
                    return None

            except ET.ParseError as e:
                logger.warning(f"Failed to parse MD5 XML: {e}")
                return None

        except NetworkError as e:
            # Check if it's a 404 (file not found) - this is expected for some files
            if "404" in str(e):
                logger.debug("MD5 XML not available (404)")
                return None
            else:
                # Other network errors should be raised
                logger.error(f"Failed to fetch MD5 XML: {e}")
                raise

        except Exception as e:
            logger.warning(f"Unexpected error fetching MD5 XML: {e}")
            return None
