"""Unit tests for the Storage class."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from gogrepoc.infrastructure.storage import Storage
from gogrepoc.core.models import Token, Game, Download, Extra


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    """Create a Storage instance with a temporary directory."""
    return Storage(tmp_path)


@pytest.fixture
def sample_token() -> Token:
    """Create a sample token for testing."""
    return Token(
        access_token="test_access_token_123",
        refresh_token="test_refresh_token_456",
        expires_at=datetime.now() + timedelta(hours=1),
        user_id="test_user_123",
    )


@pytest.fixture
def sample_download() -> Download:
    """Create a sample download for testing."""
    return Download(
        name="test_installer.exe",
        href="/download/test_game/1",
        size=1024000,
        md5="d41d8cd98f00b204e9800998ecf8427e",
        os_type="windows",
        lang="en",
        version="1.0.0",
        desc="Test Installer",
        updated=datetime(2024, 1, 1, 0, 0, 0),
        verified=False,
    )


@pytest.fixture
def sample_extra() -> Extra:
    """Create a sample extra for testing."""
    return Extra(
        name="manual.pdf",
        href="/download/test_game/manual",
        size=5000,
        desc="Game Manual",
        updated=datetime(2024, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def sample_game(sample_download: Download, sample_extra: Extra) -> Game:
    """Create a sample game for testing."""
    return Game(
        id=1,
        title="test_game",
        folder_name="test_game",
        long_title="Test Game",
        downloads=[sample_download],
        galaxy_downloads=[],
        shared_downloads=[],
        extras=[sample_extra],
        serials={"key1": "value1"},
        changelog="Initial release",
        image_url="https://example.com/image.jpg",
        bg_url="https://example.com/bg.jpg",
        store_url="https://www.gog.com/game/test_game",
        has_updates=False,
    )


class TestStorageInit:
    """Tests for Storage initialization."""

    def test_init_with_path_object(self, tmp_path: Path):
        """Test initialization with Path object."""
        storage = Storage(tmp_path)
        assert storage.storage_dir == tmp_path
        assert storage.token_file == tmp_path / "gog-token.dat"
        assert storage.manifest_file == tmp_path / "gog-manifest.dat"
        assert storage.downloaded_games_file == tmp_path / "gog-downloaded-games.dat"

    def test_init_with_string_path(self, tmp_path: Path):
        """Test initialization with string path."""
        storage = Storage(str(tmp_path))
        assert storage.storage_dir == tmp_path

    def test_init_creates_directory(self, tmp_path: Path):
        """Test that initialization creates the storage directory if it doesn't exist."""
        new_dir = tmp_path / "new_storage"
        assert not new_dir.exists()

        storage = Storage(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_init_default_directory(self):
        """Test initialization with default directory."""
        storage = Storage()
        assert storage.storage_dir == Path(".")


class TestTokenOperations:
    """Tests for token save/load operations."""

    def test_save_token(self, storage: Storage, sample_token: Token):
        """Test saving a token to disk with encryption."""
        storage.save_token(sample_token)

        assert storage.token_file.exists()

        # Verify file content is encrypted (not plain JSON)
        with open(storage.token_file, "rb") as f:
            data = f.read()

        # Encrypted data should be bytes and not start with '{'
        assert isinstance(data, bytes)
        assert not data.startswith(b"{")

    def test_load_token(self, storage: Storage, sample_token: Token):
        """Test loading a token from disk with decryption."""
        storage.save_token(sample_token)
        loaded_token = storage.load_token()

        assert loaded_token is not None
        assert loaded_token.access_token == sample_token.access_token
        assert loaded_token.refresh_token == sample_token.refresh_token
        assert loaded_token.user_id == sample_token.user_id
        # Compare timestamps with some tolerance for serialization
        assert abs((loaded_token.expires_at - sample_token.expires_at).total_seconds()) < 1

    def test_load_token_nonexistent_file(self, storage: Storage):
        """Test loading token when file doesn't exist."""
        loaded_token = storage.load_token()
        assert loaded_token is None

    def test_save_token_without_user_id(self, storage: Storage):
        """Test saving a token without user_id."""
        token = Token(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at=datetime.now() + timedelta(hours=1),
            user_id=None,
        )
        storage.save_token(token)
        loaded_token = storage.load_token()

        assert loaded_token is not None
        assert loaded_token.user_id is None

    def test_load_token_corrupted_file(self, storage: Storage):
        """Test loading token when file is corrupted."""
        # Write invalid encrypted data
        with open(storage.token_file, "wb") as f:
            f.write(b"invalid encrypted data")

        loaded_token = storage.load_token()
        assert loaded_token is None

    def test_load_token_invalid_json(self, storage: Storage):
        """Test loading token when decrypted data is not valid JSON."""
        from cryptography.fernet import Fernet

        # Encrypt invalid JSON
        fernet = Fernet(storage._encryption_key)
        encrypted_data = fernet.encrypt(b"not valid json")

        with open(storage.token_file, "wb") as f:
            f.write(encrypted_data)

        loaded_token = storage.load_token()
        assert loaded_token is None

    def test_encryption_key_deterministic(self, tmp_path: Path):
        """Test that encryption key is deterministic for same machine."""
        storage1 = Storage(tmp_path)
        storage2 = Storage(tmp_path)

        assert storage1._encryption_key == storage2._encryption_key

    def test_token_roundtrip_encryption(self, storage: Storage, sample_token: Token):
        """Test that token can be saved and loaded multiple times."""
        # First save/load cycle
        storage.save_token(sample_token)
        loaded1 = storage.load_token()

        assert loaded1 is not None
        assert loaded1.access_token == sample_token.access_token

        # Second save/load cycle with loaded token
        storage.save_token(loaded1)
        loaded2 = storage.load_token()

        assert loaded2 is not None
        assert loaded2.access_token == sample_token.access_token
        assert loaded2.refresh_token == sample_token.refresh_token


class TestManifestOperations:
    """Tests for manifest save/load operations."""

    def test_save_manifest_empty_list(self, storage: Storage):
        """Test saving an empty manifest."""
        storage.save_manifest([])

        assert storage.manifest_file.exists()

        with open(storage.manifest_file, "r") as f:
            data = json.load(f)

        assert data == []

    def test_save_manifest_single_game(self, storage: Storage, sample_game: Game):
        """Test saving a manifest with a single game."""
        storage.save_manifest([sample_game])

        assert storage.manifest_file.exists()

        with open(storage.manifest_file, "r") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["id"] == sample_game.id
        assert data[0]["title"] == sample_game.title
        assert len(data[0]["downloads"]) == 1
        assert len(data[0]["extras"]) == 1

    def test_load_manifest_empty(self, storage: Storage):
        """Test loading manifest when file doesn't exist."""
        games = storage.load_manifest()
        assert games == []

    def test_load_manifest_single_game(self, storage: Storage, sample_game: Game):
        """Test loading a manifest with a single game."""
        storage.save_manifest([sample_game])
        loaded_games = storage.load_manifest()

        assert len(loaded_games) == 1
        loaded_game = loaded_games[0]

        assert loaded_game.id == sample_game.id
        assert loaded_game.title == sample_game.title
        assert loaded_game.folder_name == sample_game.folder_name
        assert loaded_game.long_title == sample_game.long_title
        assert len(loaded_game.downloads) == 1
        assert len(loaded_game.extras) == 1
        assert loaded_game.serials == sample_game.serials
        assert loaded_game.changelog == sample_game.changelog
        assert loaded_game.image_url == sample_game.image_url
        assert loaded_game.bg_url == sample_game.bg_url
        assert loaded_game.store_url == sample_game.store_url
        assert loaded_game.has_updates == sample_game.has_updates

    def test_load_manifest_multiple_games(self, storage: Storage, sample_game: Game):
        """Test loading a manifest with multiple games."""
        game2 = Game(
            id=2,
            title="test_game_2",
            folder_name="test_game_2",
            long_title="Test Game 2",
            downloads=[],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=True,
        )

        storage.save_manifest([sample_game, game2])
        loaded_games = storage.load_manifest()

        assert len(loaded_games) == 2
        assert loaded_games[0].id == 1
        assert loaded_games[1].id == 2
        assert loaded_games[1].has_updates is True

    def test_manifest_download_serialization(self, storage: Storage, sample_download: Download):
        """Test that download objects are correctly serialized and deserialized."""
        game = Game(
            id=1, title="test", folder_name="test", long_title="Test", downloads=[sample_download]
        )

        storage.save_manifest([game])
        loaded_games = storage.load_manifest()

        loaded_download = loaded_games[0].downloads[0]
        assert loaded_download.name == sample_download.name
        assert loaded_download.href == sample_download.href
        assert loaded_download.size == sample_download.size
        assert loaded_download.md5 == sample_download.md5
        assert loaded_download.os_type == sample_download.os_type
        assert loaded_download.lang == sample_download.lang
        assert loaded_download.version == sample_download.version
        assert loaded_download.desc == sample_download.desc
        assert loaded_download.verified == sample_download.verified
        # Compare timestamps
        assert loaded_download.updated == sample_download.updated

    def test_manifest_extra_serialization(self, storage: Storage, sample_extra: Extra):
        """Test that extra objects are correctly serialized and deserialized."""
        game = Game(
            id=1, title="test", folder_name="test", long_title="Test", extras=[sample_extra]
        )

        storage.save_manifest([game])
        loaded_games = storage.load_manifest()

        loaded_extra = loaded_games[0].extras[0]
        assert loaded_extra.name == sample_extra.name
        assert loaded_extra.href == sample_extra.href
        assert loaded_extra.size == sample_extra.size
        assert loaded_extra.desc == sample_extra.desc
        assert loaded_extra.updated == sample_extra.updated

    def test_manifest_with_none_values(self, storage: Storage):
        """Test manifest with None values for optional fields."""
        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
            downloads=[],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=False,
        )

        storage.save_manifest([game])
        loaded_games = storage.load_manifest()

        assert len(loaded_games) == 1
        assert loaded_games[0].changelog is None


class TestDownloadedGamesOperations:
    """Tests for downloaded games tracking operations."""

    def test_save_downloaded_games_empty(self, storage: Storage):
        """Test saving empty downloaded games dict."""
        storage.save_downloaded_games({})

        assert storage.downloaded_games_file.exists()

        with open(storage.downloaded_games_file, "r") as f:
            data = json.load(f)

        assert data == {}

    def test_save_downloaded_games(self, storage: Storage):
        """Test saving downloaded games tracking data."""
        downloaded = {
            1: {"status": "complete", "path": "/games/game1"},
            2: {"status": "partial", "path": "/games/game2"},
        }

        storage.save_downloaded_games(downloaded)

        assert storage.downloaded_games_file.exists()

        with open(storage.downloaded_games_file, "r") as f:
            data = json.load(f)

        # JSON keys are strings, so convert for comparison
        assert "1" in data
        assert "2" in data

    def test_load_downloaded_games_nonexistent(self, storage: Storage):
        """Test loading downloaded games when file doesn't exist."""
        downloaded = storage.load_downloaded_games()
        assert downloaded == {}

    def test_load_downloaded_games(self, storage: Storage):
        """Test loading downloaded games tracking data."""
        downloaded = {
            1: {"status": "complete", "path": "/games/game1"},
            2: {"status": "partial", "path": "/games/game2"},
        }

        storage.save_downloaded_games(downloaded)
        loaded = storage.load_downloaded_games()

        # JSON converts int keys to strings
        assert "1" in loaded
        assert "2" in loaded
        assert loaded["1"]["status"] == "complete"
        assert loaded["2"]["status"] == "partial"


class TestStorageHelperMethods:
    """Tests for internal helper methods."""

    def test_download_to_dict(self, storage: Storage, sample_download: Download):
        """Test converting Download to dict."""
        result = storage._download_to_dict(sample_download)

        assert result["name"] == sample_download.name
        assert result["href"] == sample_download.href
        assert result["size"] == sample_download.size
        assert result["md5"] == sample_download.md5
        assert result["os_type"] == sample_download.os_type
        assert result["lang"] == sample_download.lang
        assert result["version"] == sample_download.version
        assert result["desc"] == sample_download.desc
        assert result["verified"] == sample_download.verified
        assert result["updated"] is not None

    def test_dict_to_download(self, storage: Storage):
        """Test converting dict to Download."""
        data = {
            "name": "test.exe",
            "href": "/download/1",
            "size": 1000,
            "md5": "abc123",
            "os_type": "windows",
            "lang": "en",
            "version": "1.0",
            "desc": "Test",
            "updated": "2024-01-01T00:00:00",
            "verified": True,
        }

        download = storage._dict_to_download(data)

        assert download.name == data["name"]
        assert download.href == data["href"]
        assert download.size == data["size"]
        assert download.md5 == data["md5"]
        assert download.os_type == data["os_type"]
        assert download.lang == data["lang"]
        assert download.version == data["version"]
        assert download.desc == data["desc"]
        assert download.verified == data["verified"]
        assert download.updated is not None

    def test_extra_to_dict(self, storage: Storage, sample_extra: Extra):
        """Test converting Extra to dict."""
        result = storage._extra_to_dict(sample_extra)

        assert result["name"] == sample_extra.name
        assert result["href"] == sample_extra.href
        assert result["size"] == sample_extra.size
        assert result["desc"] == sample_extra.desc
        assert result["updated"] is not None

    def test_dict_to_extra(self, storage: Storage):
        """Test converting dict to Extra."""
        data = {
            "name": "manual.pdf",
            "href": "/download/manual",
            "size": 5000,
            "desc": "Manual",
            "updated": "2024-01-01T00:00:00",
        }

        extra = storage._dict_to_extra(data)

        assert extra.name == data["name"]
        assert extra.href == data["href"]
        assert extra.size == data["size"]
        assert extra.desc == data["desc"]
        assert extra.updated is not None

    def test_download_with_none_updated(self, storage: Storage):
        """Test converting Download with None updated field."""
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
            verified=False,
        )

        result = storage._download_to_dict(download)
        assert result["updated"] is None

        loaded = storage._dict_to_download(result)
        assert loaded.updated is None

    def test_extra_with_none_updated(self, storage: Storage):
        """Test converting Extra with None updated field."""
        extra = Extra(
            name="manual.pdf", href="/download/manual", size=5000, desc="Manual", updated=None
        )

        result = storage._extra_to_dict(extra)
        assert result["updated"] is None

        loaded = storage._dict_to_extra(result)
        assert loaded.updated is None


class TestStorageEdgeCases:
    """Tests for edge cases and error handling."""

    def test_save_manifest_with_all_download_types(
        self, storage: Storage, sample_download: Download
    ):
        """Test saving a game with all types of downloads."""
        game = Game(
            id=1,
            title="test",
            folder_name="test",
            long_title="Test",
            downloads=[sample_download],
            galaxy_downloads=[sample_download],
            shared_downloads=[sample_download],
            extras=[],
        )

        storage.save_manifest([game])
        loaded_games = storage.load_manifest()

        assert len(loaded_games[0].downloads) == 1
        assert len(loaded_games[0].galaxy_downloads) == 1
        assert len(loaded_games[0].shared_downloads) == 1

    def test_roundtrip_preserves_data(self, storage: Storage, sample_game: Game):
        """Test that save/load roundtrip preserves all data."""
        storage.save_manifest([sample_game])
        loaded_games = storage.load_manifest()

        # Save again and compare
        storage.save_manifest(loaded_games)
        reloaded_games = storage.load_manifest()

        assert len(reloaded_games) == 1
        assert reloaded_games[0].id == sample_game.id
        assert reloaded_games[0].title == sample_game.title
