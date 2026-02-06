"""Unit tests for core data models.

Tests model instantiation, field validation, and serialization/deserialization.
"""

import pytest
from dataclasses import asdict
from datetime import datetime, timezone

from gogrepoc.core.models import Download, Extra, Game, Token


class TestDownload:
    """Tests for the Download model."""

    def test_download_instantiation_with_all_fields(self) -> None:
        """Test creating a Download with all fields specified."""
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        download = Download(
            name="test_installer.exe",
            href="/download/test_game/1",
            size=1024000,
            md5="d41d8cd98f00b204e9800998ecf8427e",
            os_type="windows",
            lang="en",
            version="1.0.0",
            desc="Test Installer",
            updated=updated,
            verified=True,
        )

        assert download.name == "test_installer.exe"
        assert download.href == "/download/test_game/1"
        assert download.size == 1024000
        assert download.md5 == "d41d8cd98f00b204e9800998ecf8427e"
        assert download.os_type == "windows"
        assert download.lang == "en"
        assert download.version == "1.0.0"
        assert download.desc == "Test Installer"
        assert download.updated == updated
        assert download.verified is True

    def test_download_instantiation_with_optional_fields_none(self) -> None:
        """Test creating a Download with optional fields set to None."""
        download = Download(
            name="test_installer.exe",
            href="/download/test_game/1",
            size=1024000,
            md5=None,
            os_type="windows",
            lang="en",
            version=None,
            desc="Test Installer",
            updated=None,
        )

        assert download.md5 is None
        assert download.version is None
        assert download.updated is None
        assert download.verified is False  # Default value

    def test_download_default_verified_field(self) -> None:
        """Test that verified field defaults to False."""
        download = Download(
            name="test.exe",
            href="/download/1",
            size=1000,
            md5=None,
            os_type="windows",
            lang="en",
            version=None,
            desc="Test",
            updated=None,
        )

        assert download.verified is False

    def test_download_serialization(self) -> None:
        """Test serializing Download to dictionary."""
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        download = Download(
            name="test.exe",
            href="/download/1",
            size=1000,
            md5="abc123",
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Test",
            updated=updated,
            verified=True,
        )

        data = asdict(download)

        assert data["name"] == "test.exe"
        assert data["href"] == "/download/1"
        assert data["size"] == 1000
        assert data["md5"] == "abc123"
        assert data["os_type"] == "windows"
        assert data["lang"] == "en"
        assert data["version"] == "1.0"
        assert data["desc"] == "Test"
        assert data["updated"] == updated
        assert data["verified"] is True

    def test_download_deserialization(self) -> None:
        """Test deserializing Download from dictionary."""
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        data = {
            "name": "test.exe",
            "href": "/download/1",
            "size": 1000,
            "md5": "abc123",
            "os_type": "windows",
            "lang": "en",
            "version": "1.0",
            "desc": "Test",
            "updated": updated,
            "verified": True,
        }

        download = Download(**data)  # type: ignore[arg-type]

        assert download.name == "test.exe"
        assert download.href == "/download/1"
        assert download.size == 1000
        assert download.md5 == "abc123"
        assert download.os_type == "windows"
        assert download.lang == "en"
        assert download.version == "1.0"
        assert download.desc == "Test"
        assert download.updated == updated
        assert download.verified is True

    def test_download_with_zero_size(self) -> None:
        """Test creating a Download with zero size."""
        download = Download(
            name="empty.txt",
            href="/download/empty",
            size=0,
            md5=None,
            os_type="windows",
            lang="en",
            version=None,
            desc="Empty file",
            updated=None,
        )

        assert download.size == 0

    def test_download_with_large_size(self) -> None:
        """Test creating a Download with large file size."""
        large_size = 50 * 1024 * 1024 * 1024  # 50 GB
        download = Download(
            name="large_game.bin",
            href="/download/large",
            size=large_size,
            md5=None,
            os_type="windows",
            lang="en",
            version=None,
            desc="Large game file",
            updated=None,
        )

        assert download.size == large_size


class TestExtra:
    """Tests for the Extra model."""

    def test_extra_instantiation_with_all_fields(self) -> None:
        """Test creating an Extra with all fields specified."""
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        extra = Extra(
            name="manual.pdf",
            href="/download/manual/1",
            size=5000000,
            desc="Game Manual",
            updated=updated,
        )

        assert extra.name == "manual.pdf"
        assert extra.href == "/download/manual/1"
        assert extra.size == 5000000
        assert extra.desc == "Game Manual"
        assert extra.updated == updated

    def test_extra_instantiation_with_none_updated(self) -> None:
        """Test creating an Extra with updated field set to None."""
        extra = Extra(
            name="artwork.zip",
            href="/download/artwork/1",
            size=10000000,
            desc="Game Artwork",
            updated=None,
        )

        assert extra.updated is None

    def test_extra_serialization(self) -> None:
        """Test serializing Extra to dictionary."""
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        extra = Extra(
            name="manual.pdf",
            href="/download/manual/1",
            size=5000000,
            desc="Game Manual",
            updated=updated,
        )

        data = asdict(extra)

        assert data["name"] == "manual.pdf"
        assert data["href"] == "/download/manual/1"
        assert data["size"] == 5000000
        assert data["desc"] == "Game Manual"
        assert data["updated"] == updated

    def test_extra_deserialization(self) -> None:
        """Test deserializing Extra from dictionary."""
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        data = {
            "name": "manual.pdf",
            "href": "/download/manual/1",
            "size": 5000000,
            "desc": "Game Manual",
            "updated": updated,
        }

        extra = Extra(**data)  # type: ignore[arg-type]

        assert extra.name == "manual.pdf"
        assert extra.href == "/download/manual/1"
        assert extra.size == 5000000
        assert extra.desc == "Game Manual"
        assert extra.updated == updated


class TestGame:
    """Tests for the Game model."""

    def test_game_instantiation_with_all_fields(self) -> None:
        """Test creating a Game with all fields specified."""
        download = Download(
            name="installer.exe",
            href="/download/1",
            size=1000,
            md5=None,
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Installer",
            updated=None,
        )
        extra = Extra(
            name="manual.pdf",
            href="/download/manual",
            size=5000,
            desc="Manual",
            updated=None,
        )

        game = Game(
            id=12345,
            title="test_game",
            folder_name="test_game",
            long_title="Test Game: The Adventure",
            downloads=[download],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[extra],
            serials={"key1": "ABC-123"},
            changelog="Version 1.0: Initial release",
            image_url="https://example.com/image.jpg",
            bg_url="https://example.com/bg.jpg",
            store_url="https://www.gog.com/game/test_game",
            has_updates=True,
        )

        assert game.id == 12345
        assert game.title == "test_game"
        assert game.folder_name == "test_game"
        assert game.long_title == "Test Game: The Adventure"
        assert len(game.downloads) == 1
        assert game.downloads[0] == download
        assert len(game.galaxy_downloads) == 0
        assert len(game.shared_downloads) == 0
        assert len(game.extras) == 1
        assert game.extras[0] == extra
        assert game.serials == {"key1": "ABC-123"}
        assert game.changelog == "Version 1.0: Initial release"
        assert game.image_url == "https://example.com/image.jpg"
        assert game.bg_url == "https://example.com/bg.jpg"
        assert game.store_url == "https://www.gog.com/game/test_game"
        assert game.has_updates is True

    def test_game_instantiation_with_minimal_fields(self) -> None:
        """Test creating a Game with only required fields."""
        game = Game(
            id=1,
            title="minimal_game",
            folder_name="minimal_game",
            long_title="Minimal Game",
        )

        assert game.id == 1
        assert game.title == "minimal_game"
        assert game.folder_name == "minimal_game"
        assert game.long_title == "Minimal Game"
        assert game.downloads == []
        assert game.galaxy_downloads == []
        assert game.shared_downloads == []
        assert game.extras == []
        assert game.serials == {}
        assert game.changelog is None
        assert game.image_url == ""
        assert game.bg_url == ""
        assert game.store_url == ""
        assert game.has_updates is False

    def test_game_default_list_fields(self) -> None:
        """Test that list fields default to empty lists."""
        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
        )

        assert isinstance(game.downloads, list)
        assert isinstance(game.galaxy_downloads, list)
        assert isinstance(game.shared_downloads, list)
        assert isinstance(game.extras, list)
        assert len(game.downloads) == 0
        assert len(game.galaxy_downloads) == 0
        assert len(game.shared_downloads) == 0
        assert len(game.extras) == 0

    def test_game_default_dict_field(self) -> None:
        """Test that serials field defaults to empty dict."""
        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
        )

        assert isinstance(game.serials, dict)
        assert len(game.serials) == 0

    def test_game_serialization(self) -> None:
        """Test serializing Game to dictionary."""
        download = Download(
            name="installer.exe",
            href="/download/1",
            size=1000,
            md5=None,
            os_type="windows",
            lang="en",
            version="1.0",
            desc="Installer",
            updated=None,
        )

        game = Game(
            id=12345,
            title="test_game",
            folder_name="test_game",
            long_title="Test Game",
            downloads=[download],
            serials={"key1": "ABC-123"},
        )

        data = asdict(game)

        assert data["id"] == 12345
        assert data["title"] == "test_game"
        assert data["folder_name"] == "test_game"
        assert data["long_title"] == "Test Game"
        assert len(data["downloads"]) == 1
        assert data["downloads"][0]["name"] == "installer.exe"
        assert data["serials"] == {"key1": "ABC-123"}

    def test_game_deserialization(self) -> None:
        """Test deserializing Game from dictionary."""
        data = {
            "id": 12345,
            "title": "test_game",
            "folder_name": "test_game",
            "long_title": "Test Game",
            "downloads": [],
            "galaxy_downloads": [],
            "shared_downloads": [],
            "extras": [],
            "serials": {"key1": "ABC-123"},
            "changelog": None,
            "image_url": "",
            "bg_url": "",
            "store_url": "",
            "has_updates": False,
        }

        game = Game(**data)  # type: ignore[arg-type]

        assert game.id == 12345
        assert game.title == "test_game"
        assert game.folder_name == "test_game"
        assert game.long_title == "Test Game"
        assert game.serials == {"key1": "ABC-123"}

    def test_game_with_multiple_downloads(self) -> None:
        """Test creating a Game with multiple downloads."""
        downloads = [
            Download(
                name=f"installer_{i}.exe",
                href=f"/download/{i}",
                size=1000 * i,
                md5=None,
                os_type="windows",
                lang="en",
                version="1.0",
                desc=f"Installer {i}",
                updated=None,
            )
            for i in range(1, 4)
        ]

        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
            downloads=downloads,
        )

        assert len(game.downloads) == 3
        assert game.downloads[0].name == "installer_1.exe"
        assert game.downloads[1].name == "installer_2.exe"
        assert game.downloads[2].name == "installer_3.exe"

    def test_game_with_multiple_extras(self) -> None:
        """Test creating a Game with multiple extras."""
        extras = [
            Extra(
                name=f"extra_{i}.pdf",
                href=f"/download/extra/{i}",
                size=5000 * i,
                desc=f"Extra {i}",
                updated=None,
            )
            for i in range(1, 4)
        ]

        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
            extras=extras,
        )

        assert len(game.extras) == 3
        assert game.extras[0].name == "extra_1.pdf"
        assert game.extras[1].name == "extra_2.pdf"
        assert game.extras[2].name == "extra_3.pdf"

    def test_game_with_multiple_serials(self) -> None:
        """Test creating a Game with multiple serial keys."""
        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
            serials={
                "key1": "ABC-123",
                "key2": "DEF-456",
                "key3": "GHI-789",
            },
        )

        assert len(game.serials) == 3
        assert game.serials["key1"] == "ABC-123"
        assert game.serials["key2"] == "DEF-456"
        assert game.serials["key3"] == "GHI-789"


class TestToken:
    """Tests for the Token model."""

    def test_token_instantiation_with_all_fields(self) -> None:
        """Test creating a Token with all fields specified."""
        expires_at = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        token = Token(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
            user_id="user_789",
        )

        assert token.access_token == "access_token_123"
        assert token.refresh_token == "refresh_token_456"
        assert token.expires_at == expires_at
        assert token.user_id == "user_789"

    def test_token_instantiation_with_none_user_id(self) -> None:
        """Test creating a Token with user_id set to None."""
        expires_at = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        token = Token(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
        )

        assert token.user_id is None

    def test_token_default_user_id_field(self) -> None:
        """Test that user_id field defaults to None."""
        expires_at = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        token = Token(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
        )

        assert token.user_id is None

    def test_token_serialization(self) -> None:
        """Test serializing Token to dictionary."""
        expires_at = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        token = Token(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
            user_id="user_789",
        )

        data = asdict(token)

        assert data["access_token"] == "access_token_123"
        assert data["refresh_token"] == "refresh_token_456"
        assert data["expires_at"] == expires_at
        assert data["user_id"] == "user_789"

    def test_token_deserialization(self) -> None:
        """Test deserializing Token from dictionary."""
        expires_at = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        data = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_456",
            "expires_at": expires_at,
            "user_id": "user_789",
        }

        token = Token(**data)  # type: ignore[arg-type]

        assert token.access_token == "access_token_123"
        assert token.refresh_token == "refresh_token_456"
        assert token.expires_at == expires_at
        assert token.user_id == "user_789"

    def test_token_with_past_expiration(self) -> None:
        """Test creating a Token with past expiration date."""
        expires_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        token = Token(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
        )

        assert token.expires_at == expires_at
        # Note: The model itself doesn't validate expiration,
        # that's the responsibility of the AuthService

    def test_token_with_future_expiration(self) -> None:
        """Test creating a Token with future expiration date."""
        expires_at = datetime(2030, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        token = Token(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
        )

        assert token.expires_at == expires_at
