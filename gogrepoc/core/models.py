"""Core data models for GOGRepoc.

This module defines the core data structures used throughout the application,
including Game, Download, Extra, and Token models.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Download:
    """Represents a downloadable game file (installer or DLC).
    
    Attributes:
        name: Display name of the download
        href: API endpoint or URL for the download
        size: File size in bytes
        md5: MD5 checksum for verification (optional)
        os_type: Operating system (e.g., 'windows', 'linux', 'mac')
        lang: Language code (e.g., 'en', 'de', 'fr')
        version: Version string of the game/installer (optional)
        desc: Description of the download
        updated: Last update timestamp (optional)
        verified: Whether the file has been verified locally
    """
    name: str
    href: str
    size: int
    md5: str | None
    os_type: str
    lang: str
    version: str | None
    desc: str
    updated: datetime | None
    verified: bool = False


@dataclass
class Extra:
    """Represents an extra downloadable file (manual, artwork, etc.).
    
    Attributes:
        name: Display name of the extra
        href: API endpoint or URL for the download
        size: File size in bytes
        desc: Description of the extra
        updated: Last update timestamp (optional)
    """
    name: str
    href: str
    size: int
    desc: str
    updated: datetime | None


@dataclass
class Game:
    """Represents a GOG game with all its downloadable content.
    
    Attributes:
        id: Unique GOG game ID
        title: Short title of the game
        folder_name: Sanitized folder name for local storage
        long_title: Full title of the game
        downloads: List of standard installers
        galaxy_downloads: List of GOG Galaxy installers
        shared_downloads: List of shared/common downloads
        extras: List of extra files (manuals, artwork, etc.)
        serials: Dictionary of serial keys/codes
        changelog: Game changelog text (optional)
        image_url: URL to game cover image
        bg_url: URL to game background image
        store_url: URL to GOG store page
        has_updates: Whether the game has available updates
    """
    id: int
    title: str
    folder_name: str
    long_title: str
    downloads: list[Download] = field(default_factory=list)
    galaxy_downloads: list[Download] = field(default_factory=list)
    shared_downloads: list[Download] = field(default_factory=list)
    extras: list[Extra] = field(default_factory=list)
    serials: dict[str, str] = field(default_factory=dict)
    changelog: str | None = None
    image_url: str = ""
    bg_url: str = ""
    store_url: str = ""
    has_updates: bool = False


@dataclass
class Token:
    """Represents an authentication token for GOG API access.
    
    Attributes:
        access_token: The OAuth access token
        refresh_token: Token used to refresh the access token
        expires_at: Timestamp when the access token expires
        user_id: GOG user ID (optional)
    """
    access_token: str
    refresh_token: str
    expires_at: datetime
    user_id: str | None = None
