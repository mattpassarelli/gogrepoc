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
        """Save game manifest to disk with JSON serialization.

        The manifest is saved in JSON format with a version marker to support
        future format changes. A backup of the previous manifest is created
        before saving.

        Args:
            games: List of Game objects to save

        Raises:
            OSError: If file cannot be written
        """
        # Create backup of existing manifest
        backup_file = self.manifest_file.with_suffix(self.manifest_file.suffix + ".bak")
        if self.manifest_file.exists():
            import shutil
            shutil.copy(self.manifest_file, backup_file)
            logger.debug(f"Created backup at {backup_file}")

        # Convert games to dictionary format for JSON serialization
        manifest_data = {
            "version": 2,  # New JSON format version
            "game_count": len(games),
            "games": []
        }
        
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
            manifest_data["games"].append(game_dict)

        # Write to temporary file first, then rename for atomic operation
        temp_file = self.manifest_file.with_suffix(self.manifest_file.suffix + ".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        
        # Atomic rename
        temp_file.replace(self.manifest_file)
        logger.info(f"Saved manifest with {len(games)} games")

    def load_manifest(self) -> list[Game]:
        """Load game manifest from disk with backward compatibility.

        Supports both the old Python literal format (from gogrepoc.py) and
        the new JSON format. Automatically migrates old format to new format
        on first load.

        Returns:
            List of Game objects, empty list if file doesn't exist

        Raises:
            OSError: If file cannot be read
        """
        if not self.manifest_file.exists():
            logger.debug("Manifest file does not exist")
            return []

        try:
            # Try loading as new JSON format first
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Check if it's the new JSON format
            if content.strip().startswith("{"):
                manifest_data = json.loads(content)
                
                # Handle new format with version
                if isinstance(manifest_data, dict) and "version" in manifest_data:
                    logger.info(f"Loading manifest version {manifest_data.get('version')}")
                    games_list = manifest_data.get("games", [])
                # Handle old JSON format (list of games without version wrapper)
                elif isinstance(manifest_data, list):
                    logger.info("Loading legacy JSON manifest format")
                    games_list = manifest_data
                else:
                    logger.error("Unknown JSON manifest format")
                    return []
                    
                games = []
                for game_dict in games_list:
                    game = self._dict_to_game(game_dict)
                    games.append(game)
                
                logger.info(f"Loaded {len(games)} games from JSON manifest")
                return games
            
            # Try loading as old Python literal format
            else:
                logger.info("Detected old Python literal manifest format, migrating...")
                games = self._load_old_manifest(content)
                
                # Automatically migrate to new format
                if games:
                    logger.info(f"Migrating {len(games)} games to new JSON format")
                    self.save_manifest(games)
                    logger.info("Migration complete")
                
                return games
                
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try old format
            logger.warning(f"JSON parsing failed: {e}, attempting old format")
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    content = f.read()
                games = self._load_old_manifest(content)
                
                # Migrate to new format
                if games:
                    logger.info(f"Migrating {len(games)} games to new JSON format")
                    self.save_manifest(games)
                
                return games
            except Exception as e2:
                logger.error(f"Failed to load manifest in any format: {e2}")
                return []
        except Exception as e:
            logger.error(f"Unexpected error loading manifest: {e}")
            return []

    def _load_old_manifest(self, content: str) -> list[Game]:
        """Load manifest from old Python literal format.

        The old format used Python's pprint to save AttrDict objects.
        This method parses that format and converts to Game objects.

        Args:
            content: Raw file content as string

        Returns:
            List of Game objects

        Raises:
            Exception: If parsing fails
        """
        import re
        
        # Remove comment line (e.g., "# 76 games")
        content = re.sub(r'^#.*\n', '', content, flags=re.MULTILINE)
        
        # Fix AttrDict munging if present
        content = re.sub(r'AttrDict\(\*\*', '', content)
        content = re.sub(r'\)\)', ')', content)
        
        # Fix Python 2 long integers (e.g., 123L -> 123)
        content = re.sub(r"'size': ([0-9]+)L,", r"'size': \1,", content)
        
        # Replace JSON null/true/false with Python None/True/False for eval
        content = content.replace(': null,', ': None,')
        content = content.replace(': null}', ': None}')
        content = content.replace(': null]', ': None]')
        content = content.replace(': true,', ': True,')
        content = content.replace(': true}', ': True}')
        content = content.replace(': true]', ': True]')
        content = content.replace(': false,', ': False,')
        content = content.replace(': false}', ': False}')
        content = content.replace(': false]', ': False]')
        
        # Safely evaluate the Python literal
        try:
            # Use ast.literal_eval for safer evaluation
            import ast
            manifest_list = ast.literal_eval(content)
        except (ValueError, SyntaxError):
            # Fallback to eval if ast.literal_eval fails (for complex structures)
            logger.warning("Using eval() for old manifest - this is less safe")
            manifest_list = eval(content)
        
        # Convert to Game objects
        games = []
        for item in manifest_list:
            # Old format uses dict-like objects
            if isinstance(item, dict):
                game = self._migrate_old_game_dict(item)
                if game:
                    games.append(game)
        
        return games

    def _migrate_old_game_dict(self, old_dict: dict[str, Any]) -> Game | None:
        """Migrate old manifest game dictionary to new Game object.

        The old format has different field names and structures.
        This method maps old fields to new Game model.

        Args:
            old_dict: Dictionary from old manifest format

        Returns:
            Game object or None if migration fails
        """
        try:
            # Extract basic fields (old format may use different keys)
            game_id = old_dict.get("id") or old_dict.get("_id_mirror")
            title = old_dict.get("title") or old_dict.get("_title_mirror", "")
            folder_name = old_dict.get("folder_name", title)
            long_title = old_dict.get("long_title") or old_dict.get("_long_title_mirror", title)
            
            # Extract downloads
            downloads = []
            for d in old_dict.get("downloads", []):
                download = self._migrate_old_download(d)
                if download:
                    downloads.append(download)
            
            # Extract galaxy downloads
            galaxy_downloads = []
            for d in old_dict.get("galaxy_downloads", []):
                download = self._migrate_old_download(d)
                if download:
                    galaxy_downloads.append(download)
            
            # Extract shared downloads
            shared_downloads = []
            for d in old_dict.get("shared_downloads", []):
                download = self._migrate_old_download(d)
                if download:
                    shared_downloads.append(download)
            
            # Extract extras
            extras = []
            for e in old_dict.get("extras", []):
                extra = self._migrate_old_extra(e)
                if extra:
                    extras.append(extra)
            
            # Extract other fields
            serials = old_dict.get("serials", {})
            changelog = old_dict.get("changelog", "")
            image_url = old_dict.get("image_url", "")
            bg_url = old_dict.get("bg_url", "")
            store_url = old_dict.get("store_url", "")
            has_updates = old_dict.get("has_updates", False)
            
            return Game(
                id=game_id,
                title=title,
                folder_name=folder_name,
                long_title=long_title,
                downloads=downloads,
                galaxy_downloads=galaxy_downloads,
                shared_downloads=shared_downloads,
                extras=extras,
                serials=serials,
                changelog=changelog,
                image_url=image_url,
                bg_url=bg_url,
                store_url=store_url,
                has_updates=has_updates,
            )
        except Exception as e:
            logger.error(f"Failed to migrate game: {e}")
            return None

    def _migrate_old_download(self, old_dict: dict[str, Any]) -> Download | None:
        """Migrate old download dictionary to Download object.

        Args:
            old_dict: Dictionary from old manifest format

        Returns:
            Download object or None if migration fails
        """
        try:
            from datetime import datetime
            
            # Old format may have nested structures
            name = old_dict.get("name", "")
            href = old_dict.get("href", "")
            size = old_dict.get("size", 0)
            
            # MD5 might be in nested structure
            md5 = old_dict.get("md5")
            if not md5 and "gog_data" in old_dict:
                gog_data = old_dict["gog_data"]
                if isinstance(gog_data, dict) and "md5_xml" in gog_data:
                    md5_xml = gog_data["md5_xml"]
                    if isinstance(md5_xml, dict):
                        md5 = md5_xml.get("md5")
            
            os_type = old_dict.get("os_type", old_dict.get("os", ""))
            lang = old_dict.get("lang", old_dict.get("language", "en"))
            version = old_dict.get("version", old_dict.get("ver"))
            desc = old_dict.get("desc", old_dict.get("description", ""))
            
            # Parse date/updated field
            updated = None
            date_str = old_dict.get("updated") or old_dict.get("date")
            if date_str:
                try:
                    if isinstance(date_str, str) and date_str:
                        # Try ISO format first
                        try:
                            updated = datetime.fromisoformat(date_str)
                        except ValueError:
                            # Try other common formats
                            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                                try:
                                    updated = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                except Exception:
                    pass
            
            verified = old_dict.get("verified", False)
            
            return Download(
                name=name,
                href=href,
                size=size,
                md5=md5,
                os_type=os_type,
                lang=lang,
                version=version,
                desc=desc,
                updated=updated,
                verified=verified,
            )
        except Exception as e:
            logger.error(f"Failed to migrate download: {e}")
            return None

    def _migrate_old_extra(self, old_dict: dict[str, Any]) -> Extra | None:
        """Migrate old extra dictionary to Extra object.

        Args:
            old_dict: Dictionary from old manifest format

        Returns:
            Extra object or None if migration fails
        """
        try:
            from datetime import datetime
            
            name = old_dict.get("name", "")
            href = old_dict.get("href", "")
            size = old_dict.get("size", 0)
            desc = old_dict.get("desc", old_dict.get("description", ""))
            
            # Parse date
            updated = None
            date_str = old_dict.get("updated") or old_dict.get("date")
            if date_str:
                try:
                    if isinstance(date_str, str) and date_str:
                        try:
                            updated = datetime.fromisoformat(date_str)
                        except ValueError:
                            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                                try:
                                    updated = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                except Exception:
                    pass
            
            return Extra(
                name=name,
                href=href,
                size=size,
                desc=desc,
                updated=updated,
            )
        except Exception as e:
            logger.error(f"Failed to migrate extra: {e}")
            return None

    def _dict_to_game(self, data: dict[str, Any]) -> Game:
        """Convert dictionary to Game object.

        Args:
            data: Dictionary containing game data

        Returns:
            Game object
        """
        return Game(
            id=data["id"],
            title=data["title"],
            folder_name=data["folder_name"],
            long_title=data["long_title"],
            downloads=[self._dict_to_download(d) for d in data.get("downloads", [])],
            galaxy_downloads=[
                self._dict_to_download(d) for d in data.get("galaxy_downloads", [])
            ],
            shared_downloads=[
                self._dict_to_download(d) for d in data.get("shared_downloads", [])
            ],
            extras=[self._dict_to_extra(e) for e in data.get("extras", [])],
            serials=data.get("serials", {}),
            changelog=data.get("changelog"),
            image_url=data.get("image_url", ""),
            bg_url=data.get("bg_url", ""),
            store_url=data.get("store_url", ""),
            has_updates=data.get("has_updates", False),
        )

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
