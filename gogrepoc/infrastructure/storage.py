"""Storage layer for persistent data.

This module provides the Storage class for managing persistent storage of
authentication tokens and game manifests using JSON serialization.
Token storage uses encryption for security.
"""

import json
import logging
from pathlib import Path
from typing import Any
import platform
import hashlib
import base64

from cryptography.fernet import Fernet, InvalidToken

from gogrepoc.core.models import Token, Game, Download, Extra

logger = logging.getLogger(__name__)


class Storage:
    """Handles persistent storage of tokens and manifests.

    This class manages the storage and retrieval of authentication tokens
    and game manifests using JSON files. It provides a clean interface for
    the service layer to persist and load data.

    Attributes:
        storage_dir: Directory path where storage files are kept
        token_file: Path to the token storage file
        manifest_file: Path to the manifest storage file
        downloaded_games_file: Path to the downloaded games tracking file
    """

    def __init__(self, storage_dir: Path | str = "."):
        """Initialize Storage with a storage directory.

        Args:
            storage_dir: Directory path for storage files. Defaults to current directory.
        """
        self.storage_dir = Path(storage_dir)
        self.token_file = self.storage_dir / "gog-token.dat"
        self.manifest_file = self.storage_dir / "gog-manifest.dat"
        self.downloaded_games_file = self.storage_dir / "gog-downloaded-games.dat"

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize encryption key
        self._encryption_key = self._get_encryption_key()

    def _get_encryption_key(self) -> bytes:
        """Generate a machine-specific encryption key.

        This creates a deterministic key based on machine characteristics.
        The key is derived from the machine's hostname and platform information.

        Returns:
            32-byte encryption key suitable for Fernet encryption

        Note:
            This provides basic encryption to prevent casual token theft.
            For production use, consider using system keyring services.
        """
        # Combine machine-specific identifiers
        machine_id = f"{platform.node()}-{platform.machine()}-{platform.system()}"

        # Create a deterministic key using SHA-256
        key_material = hashlib.sha256(machine_id.encode()).digest()

        # Fernet requires a base64-encoded 32-byte key
        return base64.urlsafe_b64encode(key_material)

    def save_token(self, token: Token) -> None:
        """Save authentication token to disk with encryption.

        The token is serialized to JSON, encrypted using Fernet symmetric
        encryption, and saved to disk. The encryption key is derived from
        machine-specific characteristics.

        Args:
            token: Token object to save

        Raises:
            OSError: If file cannot be written
        """
        token_data = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.isoformat(),
            "user_id": token.user_id,
        }

        # Serialize to JSON
        json_data = json.dumps(token_data)

        # Encrypt the data
        fernet = Fernet(self._encryption_key)
        encrypted_data = fernet.encrypt(json_data.encode("utf-8"))

        # Write encrypted data to file
        with open(self.token_file, "wb") as f:
            f.write(encrypted_data)

        logger.info("Token saved successfully with encryption")

    def load_token(self) -> Token | None:
        """Load authentication token from disk with decryption.

        Reads the encrypted token file, decrypts it, and deserializes the
        token data. Handles missing files and decryption errors gracefully.

        Returns:
            Token object if file exists and is valid, None otherwise

        Raises:
            OSError: If file cannot be read
        """
        if not self.token_file.exists():
            logger.debug("Token file does not exist")
            return None

        try:
            # Read encrypted data
            with open(self.token_file, "rb") as f:
                encrypted_data = f.read()

            # Decrypt the data
            fernet = Fernet(self._encryption_key)
            decrypted_data = fernet.decrypt(encrypted_data)

            # Parse JSON
            token_data = json.loads(decrypted_data.decode("utf-8"))

            from datetime import datetime

            logger.info("Token loaded successfully")
            return Token(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=datetime.fromisoformat(token_data["expires_at"]),
                user_id=token_data.get("user_id"),
            )

        except InvalidToken:
            logger.error(
                "Failed to decrypt token file - may be corrupted or from different machine"
            )
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse token data: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading token: {e}")
            return None

    def save_manifest(self, games: list[Game]) -> None:
        """Save game manifest to disk.

        Args:
            games: List of Game objects to save

        Raises:
            OSError: If file cannot be written
        """
        # Convert games to dictionary format for JSON serialization
        manifest_data = []
        for game in games:
            game_dict = {
                "id": game.id,
                "title": game.title,
                "folder_name": game.folder_name,
                "long_title": game.long_title,
                "downloads": [self._download_to_dict(d) for d in game.downloads],
                "galaxy_downloads": [self._download_to_dict(d) for d in game.galaxy_downloads],
                "shared_downloads": [self._download_to_dict(d) for d in game.shared_downloads],
                "extras": [self._extra_to_dict(e) for e in game.extras],
                "serials": game.serials,
                "changelog": game.changelog,
                "image_url": game.image_url,
                "bg_url": game.bg_url,
                "store_url": game.store_url,
                "has_updates": game.has_updates,
            }
            manifest_data.append(game_dict)

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

    def load_manifest(self) -> list[Game]:
        """Load game manifest from disk.

        Returns:
            List of Game objects, empty list if file doesn't exist

        Raises:
            OSError: If file cannot be read
            json.JSONDecodeError: If file contains invalid JSON
        """
        if not self.manifest_file.exists():
            return []

        with open(self.manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        games = []
        for game_dict in manifest_data:
            game = Game(
                id=game_dict["id"],
                title=game_dict["title"],
                folder_name=game_dict["folder_name"],
                long_title=game_dict["long_title"],
                downloads=[self._dict_to_download(d) for d in game_dict.get("downloads", [])],
                galaxy_downloads=[
                    self._dict_to_download(d) for d in game_dict.get("galaxy_downloads", [])
                ],
                shared_downloads=[
                    self._dict_to_download(d) for d in game_dict.get("shared_downloads", [])
                ],
                extras=[self._dict_to_extra(e) for e in game_dict.get("extras", [])],
                serials=game_dict.get("serials", {}),
                changelog=game_dict.get("changelog"),
                image_url=game_dict.get("image_url", ""),
                bg_url=game_dict.get("bg_url", ""),
                store_url=game_dict.get("store_url", ""),
                has_updates=game_dict.get("has_updates", False),
            )
            games.append(game)

        return games

    def save_downloaded_games(self, downloaded_games: dict[int, Any]) -> None:
        """Save downloaded games tracking data to disk.

        Args:
            downloaded_games: Dictionary mapping game IDs to download status

        Raises:
            OSError: If file cannot be written
        """
        with open(self.downloaded_games_file, "w", encoding="utf-8") as f:
            json.dump(downloaded_games, f, indent=2)

    def load_downloaded_games(self) -> dict[int, Any]:
        """Load downloaded games tracking data from disk.

        Returns:
            Dictionary mapping game IDs to download status, empty dict if file doesn't exist

        Raises:
            OSError: If file cannot be read
            json.JSONDecodeError: If file contains invalid JSON
        """
        if not self.downloaded_games_file.exists():
            return {}

        with open(self.downloaded_games_file, "r", encoding="utf-8") as f:
            data: dict[int, Any] = json.load(f)
            return data

    def _download_to_dict(self, download: Download) -> dict[str, Any]:
        """Convert Download object to dictionary for JSON serialization.

        Args:
            download: Download object to convert

        Returns:
            Dictionary representation of the download
        """
        return {
            "name": download.name,
            "href": download.href,
            "size": download.size,
            "md5": download.md5,
            "os_type": download.os_type,
            "lang": download.lang,
            "version": download.version,
            "desc": download.desc,
            "updated": download.updated.isoformat() if download.updated else None,
            "verified": download.verified,
        }

    def _dict_to_download(self, data: dict[str, Any]) -> Download:
        """Convert dictionary to Download object.

        Args:
            data: Dictionary containing download data

        Returns:
            Download object
        """
        from datetime import datetime

        return Download(
            name=data["name"],
            href=data["href"],
            size=data["size"],
            md5=data.get("md5"),
            os_type=data["os_type"],
            lang=data["lang"],
            version=data.get("version"),
            desc=data["desc"],
            updated=datetime.fromisoformat(data["updated"]) if data.get("updated") else None,
            verified=data.get("verified", False),
        )

    def _extra_to_dict(self, extra: Extra) -> dict[str, Any]:
        """Convert Extra object to dictionary for JSON serialization.

        Args:
            extra: Extra object to convert

        Returns:
            Dictionary representation of the extra
        """
        return {
            "name": extra.name,
            "href": extra.href,
            "size": extra.size,
            "desc": extra.desc,
            "updated": extra.updated.isoformat() if extra.updated else None,
        }

    def _dict_to_extra(self, data: dict[str, Any]) -> Extra:
        """Convert dictionary to Extra object.

        Args:
            data: Dictionary containing extra data

        Returns:
            Extra object
        """
        from datetime import datetime

        return Extra(
            name=data["name"],
            href=data["href"],
            size=data["size"],
            desc=data["desc"],
            updated=datetime.fromisoformat(data["updated"]) if data.get("updated") else None,
        )
