"""Unit tests for the ManifestService class."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from gogrepoc.services.manifest import ManifestService
from gogrepoc.core.models import Game, Download, Extra
from gogrepoc.infrastructure.storage import Storage


@pytest.fixture
def mock_storage(tmp_path):
    """Create a Storage instance with temporary directory."""
    storage = Storage(tmp_path)
    return storage


@pytest.fixture
def manifest_service(mock_storage):
    """Create a ManifestService instance with mocked storage."""
    return ManifestService(mock_storage)


@pytest.fixture
def sample_game():
    """Create a sample game for testing."""
    return Game(
        id=1,
        title="Test Game",
        folder_name="test_game",
        long_title="Test Game: Complete Edition",
        downloads=[
            Download(
                name="Test Game Installer",
                href="/download/test_game/1",
                size=1000000,
                md5="abc123",
                os_type="windows",
                lang="en",
                version="1.0",
                desc="Windows installer",
                updated=datetime(2024, 1, 1),
                verified=False,
            )
        ],
        galaxy_downloads=[],
        shared_downloads=[],
        extras=[
            Extra(
                name="Manual",
                href="/download/test_game/manual",
                size=5000,
                desc="Game manual",
                updated=datetime(2024, 1, 1),
            )
        ],
        serials={"key1": "ABC-123"},
        changelog="Initial release",
        image_url="https://example.com/image.jpg",
        bg_url="https://example.com/bg.jpg",
        store_url="https://www.gog.com/game/test_game",
        has_updates=False,
    )


@pytest.fixture
def sample_game_2():
    """Create a second sample game for testing."""
    return Game(
        id=2,
        title="Another Game",
        folder_name="another_game",
        long_title="Another Game: Deluxe Edition",
        downloads=[
            Download(
                name="Another Game Installer",
                href="/download/another_game/1",
                size=2000000,
                md5="def456",
                os_type="linux",
                lang="en",
                version="2.0",
                desc="Linux installer",
                updated=datetime(2024, 2, 1),
                verified=False,
            )
        ],
        galaxy_downloads=[],
        shared_downloads=[],
        extras=[],
        serials={},
        changelog="Version 2.0",
        image_url="https://example.com/image2.jpg",
        bg_url="https://example.com/bg2.jpg",
        store_url="https://www.gog.com/game/another_game",
        has_updates=True,
    )


class TestManifestServiceInit:
    """Tests for ManifestService initialization."""

    def test_init_with_storage(self, mock_storage):
        """Test initialization with storage dependency."""
        service = ManifestService(mock_storage)
        
        assert service.storage == mock_storage
        assert service._manifest_cache == {}

    def test_init_creates_empty_cache(self, manifest_service):
        """Test that initialization creates an empty cache."""
        assert isinstance(manifest_service._manifest_cache, dict)
        assert len(manifest_service._manifest_cache) == 0


class TestLoadManifest:
    """Tests for load_manifest method."""

    def test_load_manifest_empty(self, manifest_service):
        """Test loading manifest when no manifest file exists."""
        games = manifest_service.load_manifest()
        
        assert games == []
        assert manifest_service._manifest_cache == {}

    def test_load_manifest_with_games(self, manifest_service, mock_storage, sample_game, sample_game_2):
        """Test loading manifest with existing games."""
        # Save games to storage first
        mock_storage.save_manifest([sample_game, sample_game_2])
        
        # Load manifest
        games = manifest_service.load_manifest()
        
        assert len(games) == 2
        assert games[0].id == sample_game.id
        assert games[1].id == sample_game_2.id
        
        # Verify cache was populated
        assert len(manifest_service._manifest_cache) == 2
        assert sample_game.id in manifest_service._manifest_cache
        assert sample_game_2.id in manifest_service._manifest_cache

    def test_load_manifest_builds_cache_by_id(self, manifest_service, mock_storage, sample_game):
        """Test that load_manifest builds cache indexed by game ID."""
        mock_storage.save_manifest([sample_game])
        
        manifest_service.load_manifest()
        
        # Verify cache is indexed by game ID
        assert sample_game.id in manifest_service._manifest_cache
        assert manifest_service._manifest_cache[sample_game.id] == sample_game

    def test_load_manifest_replaces_existing_cache(self, manifest_service, mock_storage, sample_game, sample_game_2):
        """Test that loading manifest replaces existing cache."""
        # Set up initial cache
        manifest_service._manifest_cache = {999: sample_game}
        
        # Save different games to storage
        mock_storage.save_manifest([sample_game_2])
        
        # Load manifest
        games = manifest_service.load_manifest()
        
        # Verify cache was replaced
        assert len(manifest_service._manifest_cache) == 1
        assert 999 not in manifest_service._manifest_cache
        assert sample_game_2.id in manifest_service._manifest_cache

    def test_load_manifest_preserves_game_data(self, manifest_service, mock_storage, sample_game):
        """Test that loading manifest preserves all game data."""
        mock_storage.save_manifest([sample_game])
        
        games = manifest_service.load_manifest()
        loaded_game = games[0]
        
        # Verify all fields are preserved
        assert loaded_game.id == sample_game.id
        assert loaded_game.title == sample_game.title
        assert loaded_game.folder_name == sample_game.folder_name
        assert loaded_game.long_title == sample_game.long_title
        assert len(loaded_game.downloads) == len(sample_game.downloads)
        assert len(loaded_game.extras) == len(sample_game.extras)
        assert loaded_game.serials == sample_game.serials
        assert loaded_game.changelog == sample_game.changelog
        assert loaded_game.has_updates == sample_game.has_updates


class TestSaveManifest:
    """Tests for save_manifest method."""

    def test_save_manifest_empty(self, manifest_service, mock_storage):
        """Test saving empty manifest."""
        manifest_service.save_manifest()
        
        # Verify empty manifest was saved
        loaded_games = mock_storage.load_manifest()
        assert loaded_games == []

    def test_save_manifest_with_games(self, manifest_service, mock_storage, sample_game, sample_game_2):
        """Test saving manifest with games."""
        # Add games to cache
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        # Save manifest
        manifest_service.save_manifest()
        
        # Verify games were saved
        loaded_games = mock_storage.load_manifest()
        assert len(loaded_games) == 2
        
        # Verify game IDs are present
        loaded_ids = {game.id for game in loaded_games}
        assert sample_game.id in loaded_ids
        assert sample_game_2.id in loaded_ids

    def test_save_manifest_preserves_data(self, manifest_service, mock_storage, sample_game):
        """Test that saving manifest preserves all game data."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        manifest_service.save_manifest()
        
        # Load and verify
        loaded_games = mock_storage.load_manifest()
        loaded_game = loaded_games[0]
        
        assert loaded_game.title == sample_game.title
        assert loaded_game.folder_name == sample_game.folder_name
        assert len(loaded_game.downloads) == len(sample_game.downloads)
        assert loaded_game.downloads[0].name == sample_game.downloads[0].name

    def test_save_manifest_overwrites_existing(self, manifest_service, mock_storage, sample_game, sample_game_2):
        """Test that saving manifest overwrites existing manifest file."""
        # Save initial manifest
        mock_storage.save_manifest([sample_game])
        
        # Update cache with different game
        manifest_service._manifest_cache = {sample_game_2.id: sample_game_2}
        
        # Save new manifest
        manifest_service.save_manifest()
        
        # Verify only new game is in manifest
        loaded_games = mock_storage.load_manifest()
        assert len(loaded_games) == 1
        assert loaded_games[0].id == sample_game_2.id


class TestUpdateGame:
    """Tests for update_game method."""

    def test_update_game_add_new(self, manifest_service, sample_game):
        """Test adding a new game to manifest."""
        manifest_service.update_game(sample_game)
        
        assert sample_game.id in manifest_service._manifest_cache
        assert manifest_service._manifest_cache[sample_game.id] == sample_game
        # New games should not have updates flag set
        assert manifest_service._manifest_cache[sample_game.id].has_updates is False

    def test_update_game_replace_existing(self, manifest_service, sample_game):
        """Test updating an existing game in manifest."""
        # Add initial game
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        # Create updated version
        updated_game = Game(
            id=sample_game.id,
            title="Updated Title",
            folder_name=sample_game.folder_name,
            long_title="Updated Long Title",
            downloads=[],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog="Updated changelog",
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=True,
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify game was updated
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.title == "Updated Title"
        assert cached_game.changelog == "Updated changelog"
        # has_updates should be True because downloads list changed (1 -> 0)
        assert cached_game.has_updates is True

    def test_update_game_multiple_games(self, manifest_service, sample_game, sample_game_2):
        """Test updating multiple games."""
        manifest_service.update_game(sample_game)
        manifest_service.update_game(sample_game_2)
        
        assert len(manifest_service._manifest_cache) == 2
        assert sample_game.id in manifest_service._manifest_cache
        assert sample_game_2.id in manifest_service._manifest_cache

    def test_update_game_does_not_auto_save(self, manifest_service, mock_storage, sample_game):
        """Test that update_game does not automatically save to storage."""
        manifest_service.update_game(sample_game)
        
        # Verify game is in cache but not in storage
        assert sample_game.id in manifest_service._manifest_cache
        
        loaded_games = mock_storage.load_manifest()
        assert len(loaded_games) == 0

    def test_update_game_detects_version_change(self, manifest_service, sample_game):
        """Test that update_game detects version changes in downloads."""
        # Add initial game
        manifest_service.update_game(sample_game)
        
        # Create updated version with new version number
        updated_game = Game(
            id=sample_game.id,
            title=sample_game.title,
            folder_name=sample_game.folder_name,
            long_title=sample_game.long_title,
            downloads=[
                Download(
                    name="Test Game Installer",
                    href="/download/test_game/1",
                    size=1000000,
                    md5="abc123",
                    os_type="windows",
                    lang="en",
                    version="2.0",  # Changed from 1.0
                    desc="Windows installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                )
            ],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=sample_game.extras,
            serials=sample_game.serials,
            changelog=sample_game.changelog,
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=False,
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify has_updates was set to True
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.has_updates is True

    def test_update_game_detects_timestamp_change(self, manifest_service, sample_game):
        """Test that update_game detects timestamp changes in downloads."""
        # Add initial game
        manifest_service.update_game(sample_game)
        
        # Create updated version with new timestamp
        updated_game = Game(
            id=sample_game.id,
            title=sample_game.title,
            folder_name=sample_game.folder_name,
            long_title=sample_game.long_title,
            downloads=[
                Download(
                    name="Test Game Installer",
                    href="/download/test_game/1",
                    size=1000000,
                    md5="abc123",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="Windows installer",
                    updated=datetime(2024, 2, 1),  # Changed from 2024-01-01
                    verified=False,
                )
            ],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=sample_game.extras,
            serials=sample_game.serials,
            changelog=sample_game.changelog,
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=False,
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify has_updates was set to True
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.has_updates is True

    def test_update_game_detects_new_download(self, manifest_service, sample_game):
        """Test that update_game detects new downloads added."""
        # Add initial game
        manifest_service.update_game(sample_game)
        
        # Create updated version with additional download
        updated_game = Game(
            id=sample_game.id,
            title=sample_game.title,
            folder_name=sample_game.folder_name,
            long_title=sample_game.long_title,
            downloads=[
                sample_game.downloads[0],
                Download(
                    name="Test Game DLC",
                    href="/download/test_game/dlc",
                    size=500000,
                    md5="def456",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="DLC installer",
                    updated=datetime(2024, 1, 15),
                    verified=False,
                )
            ],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=sample_game.extras,
            serials=sample_game.serials,
            changelog=sample_game.changelog,
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=False,
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify has_updates was set to True
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.has_updates is True

    def test_update_game_detects_new_extra(self, manifest_service, sample_game):
        """Test that update_game detects new extras added."""
        # Add initial game
        manifest_service.update_game(sample_game)
        
        # Create updated version with additional extra
        updated_game = Game(
            id=sample_game.id,
            title=sample_game.title,
            folder_name=sample_game.folder_name,
            long_title=sample_game.long_title,
            downloads=sample_game.downloads,
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[
                sample_game.extras[0],
                Extra(
                    name="Soundtrack",
                    href="/download/test_game/soundtrack",
                    size=50000000,
                    desc="Game soundtrack",
                    updated=datetime(2024, 1, 15),
                )
            ],
            serials=sample_game.serials,
            changelog=sample_game.changelog,
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=False,
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify has_updates was set to True
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.has_updates is True

    def test_update_game_no_changes_preserves_flag(self, manifest_service, sample_game):
        """Test that update_game preserves has_updates flag when no changes detected."""
        # Add initial game (will be set to has_updates=False for new games)
        manifest_service.update_game(sample_game)
        
        # Manually set has_updates=True to simulate a game that was previously marked with updates
        manifest_service._manifest_cache[sample_game.id].has_updates = True
        
        # Create identical game (no changes)
        updated_game = Game(
            id=sample_game.id,
            title=sample_game.title,
            folder_name=sample_game.folder_name,
            long_title=sample_game.long_title,
            downloads=sample_game.downloads,
            galaxy_downloads=[],
            shared_downloads=[],
            extras=sample_game.extras,
            serials=sample_game.serials,
            changelog=sample_game.changelog,
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=False,  # This should be ignored
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify has_updates was preserved from original
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.has_updates is True

    def test_update_game_detects_galaxy_download_changes(self, manifest_service, sample_game):
        """Test that update_game detects changes in galaxy downloads."""
        # Add initial game with galaxy download
        sample_game.galaxy_downloads = [
            Download(
                name="Galaxy Installer",
                href="/download/test_game/galaxy",
                size=1000000,
                md5="gal123",
                os_type="windows",
                lang="en",
                version="1.0",
                desc="Galaxy installer",
                updated=datetime(2024, 1, 1),
                verified=False,
            )
        ]
        manifest_service.update_game(sample_game)
        
        # Create updated version with new galaxy version
        updated_game = Game(
            id=sample_game.id,
            title=sample_game.title,
            folder_name=sample_game.folder_name,
            long_title=sample_game.long_title,
            downloads=sample_game.downloads,
            galaxy_downloads=[
                Download(
                    name="Galaxy Installer",
                    href="/download/test_game/galaxy",
                    size=1000000,
                    md5="gal123",
                    os_type="windows",
                    lang="en",
                    version="2.0",  # Changed version
                    desc="Galaxy installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                )
            ],
            shared_downloads=[],
            extras=sample_game.extras,
            serials=sample_game.serials,
            changelog=sample_game.changelog,
            image_url=sample_game.image_url,
            bg_url=sample_game.bg_url,
            store_url=sample_game.store_url,
            has_updates=False,
        )
        
        # Update game
        manifest_service.update_game(updated_game)
        
        # Verify has_updates was set to True
        cached_game = manifest_service._manifest_cache[sample_game.id]
        assert cached_game.has_updates is True


class TestGetGameById:
    """Tests for get_game_by_id method."""

    def test_get_game_by_id_found(self, manifest_service, sample_game):
        """Test retrieving an existing game by ID."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        game = manifest_service.get_game_by_id(sample_game.id)
        
        assert game is not None
        assert game.id == sample_game.id
        assert game.title == sample_game.title

    def test_get_game_by_id_not_found(self, manifest_service):
        """Test retrieving a non-existent game by ID."""
        game = manifest_service.get_game_by_id(999)
        
        assert game is None

    def test_get_game_by_id_empty_cache(self, manifest_service):
        """Test retrieving game from empty cache."""
        game = manifest_service.get_game_by_id(1)
        
        assert game is None

    def test_get_game_by_id_multiple_games(self, manifest_service, sample_game, sample_game_2):
        """Test retrieving specific game when multiple games exist."""
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        game = manifest_service.get_game_by_id(sample_game_2.id)
        
        assert game is not None
        assert game.id == sample_game_2.id
        assert game.title == sample_game_2.title


class TestGetAllGames:
    """Tests for get_all_games method."""

    def test_get_all_games_empty(self, manifest_service):
        """Test getting all games from empty manifest."""
        games = manifest_service.get_all_games()
        
        assert games == []

    def test_get_all_games_single(self, manifest_service, sample_game):
        """Test getting all games with single game."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        games = manifest_service.get_all_games()
        
        assert len(games) == 1
        assert games[0] == sample_game

    def test_get_all_games_multiple(self, manifest_service, sample_game, sample_game_2):
        """Test getting all games with multiple games."""
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        games = manifest_service.get_all_games()
        
        assert len(games) == 2
        assert sample_game in games
        assert sample_game_2 in games

    def test_get_all_games_returns_list(self, manifest_service, sample_game):
        """Test that get_all_games returns a list."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        games = manifest_service.get_all_games()
        
        assert isinstance(games, list)


class TestGetGameCount:
    """Tests for get_game_count method."""

    def test_get_game_count_empty(self, manifest_service):
        """Test getting game count from empty manifest."""
        count = manifest_service.get_game_count()
        
        assert count == 0

    def test_get_game_count_single(self, manifest_service, sample_game):
        """Test getting game count with single game."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        count = manifest_service.get_game_count()
        
        assert count == 1

    def test_get_game_count_multiple(self, manifest_service, sample_game, sample_game_2):
        """Test getting game count with multiple games."""
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        count = manifest_service.get_game_count()
        
        assert count == 2


class TestClearManifest:
    """Tests for clear_manifest method."""

    def test_clear_manifest_empty(self, manifest_service):
        """Test clearing empty manifest."""
        manifest_service.clear_manifest()
        
        assert len(manifest_service._manifest_cache) == 0

    def test_clear_manifest_with_games(self, manifest_service, sample_game, sample_game_2):
        """Test clearing manifest with games."""
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        manifest_service.clear_manifest()
        
        assert len(manifest_service._manifest_cache) == 0
        assert manifest_service.get_game_count() == 0

    def test_clear_manifest_does_not_affect_storage(self, manifest_service, mock_storage, sample_game):
        """Test that clearing manifest does not affect storage."""
        # Save game to storage
        mock_storage.save_manifest([sample_game])
        
        # Load into cache
        manifest_service.load_manifest()
        
        # Clear cache
        manifest_service.clear_manifest()
        
        # Verify storage still has the game
        loaded_games = mock_storage.load_manifest()
        assert len(loaded_games) == 1

    def test_clear_manifest_can_be_saved(self, manifest_service, mock_storage, sample_game):
        """Test that cleared manifest can be saved to persist empty state."""
        # Set up initial state
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        manifest_service.save_manifest()
        
        # Clear and save
        manifest_service.clear_manifest()
        manifest_service.save_manifest()
        
        # Verify storage is now empty
        loaded_games = mock_storage.load_manifest()
        assert len(loaded_games) == 0


class TestManifestServiceIntegration:
    """Integration tests for complete manifest workflows."""

    def test_complete_workflow_add_save_load(self, manifest_service, mock_storage, sample_game, sample_game_2):
        """Test complete workflow: add games, save, load."""
        # Add games
        manifest_service.update_game(sample_game)
        manifest_service.update_game(sample_game_2)
        
        # Save manifest
        manifest_service.save_manifest()
        
        # Create new service instance and load
        new_service = ManifestService(mock_storage)
        games = new_service.load_manifest()
        
        # Verify games were persisted and loaded
        assert len(games) == 2
        assert new_service.get_game_by_id(sample_game.id) is not None
        assert new_service.get_game_by_id(sample_game_2.id) is not None

    def test_workflow_update_existing_game(self, manifest_service, mock_storage, sample_game):
        """Test workflow: add game, save, update, save, load."""
        # Add and save initial game
        manifest_service.update_game(sample_game)
        manifest_service.save_manifest()
        
        # Update game
        sample_game.has_updates = True
        sample_game.changelog = "New update"
        manifest_service.update_game(sample_game)
        manifest_service.save_manifest()
        
        # Load in new service
        new_service = ManifestService(mock_storage)
        new_service.load_manifest()
        
        # Verify updates were persisted
        loaded_game = new_service.get_game_by_id(sample_game.id)
        assert loaded_game.has_updates is True
        assert loaded_game.changelog == "New update"

    def test_workflow_remove_game_by_clearing(self, manifest_service, mock_storage, sample_game, sample_game_2):
        """Test workflow: add games, remove one by clearing and re-adding."""
        # Add both games
        manifest_service.update_game(sample_game)
        manifest_service.update_game(sample_game_2)
        manifest_service.save_manifest()
        
        # Clear and add only one game back
        manifest_service.clear_manifest()
        manifest_service.update_game(sample_game)
        manifest_service.save_manifest()
        
        # Load in new service
        new_service = ManifestService(mock_storage)
        new_service.load_manifest()
        
        # Verify only one game remains
        assert new_service.get_game_count() == 1
        assert new_service.get_game_by_id(sample_game.id) is not None
        assert new_service.get_game_by_id(sample_game_2.id) is None

    def test_workflow_multiple_services_same_storage(self, mock_storage, sample_game):
        """Test multiple service instances sharing same storage."""
        # Service 1 adds and saves game
        service1 = ManifestService(mock_storage)
        service1.update_game(sample_game)
        service1.save_manifest()
        
        # Service 2 loads and verifies
        service2 = ManifestService(mock_storage)
        service2.load_manifest()
        
        assert service2.get_game_count() == 1
        assert service2.get_game_by_id(sample_game.id) is not None


class TestFilterGames:
    """Tests for filter_games method."""

    @pytest.fixture
    def multi_os_game(self):
        """Create a game with downloads for multiple OS types."""
        return Game(
            id=10,
            title="Multi-OS Game",
            folder_name="multi_os_game",
            long_title="Multi-OS Game: Complete Edition",
            downloads=[
                Download(
                    name="Windows Installer",
                    href="/download/game/win",
                    size=1000000,
                    md5="win123",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="Windows installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
                Download(
                    name="Linux Installer",
                    href="/download/game/linux",
                    size=1100000,
                    md5="lin123",
                    os_type="linux",
                    lang="en",
                    version="1.0",
                    desc="Linux installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
                Download(
                    name="Mac Installer",
                    href="/download/game/mac",
                    size=1200000,
                    md5="mac123",
                    os_type="mac",
                    lang="en",
                    version="1.0",
                    desc="Mac installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
            ],
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

    @pytest.fixture
    def multi_lang_game(self):
        """Create a game with downloads for multiple languages."""
        return Game(
            id=11,
            title="Multi-Lang Game",
            folder_name="multi_lang_game",
            long_title="Multi-Lang Game: International Edition",
            downloads=[
                Download(
                    name="English Installer",
                    href="/download/game/en",
                    size=1000000,
                    md5="en123",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="English installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
                Download(
                    name="German Installer",
                    href="/download/game/de",
                    size=1050000,
                    md5="de123",
                    os_type="windows",
                    lang="de",
                    version="1.0",
                    desc="German installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
                Download(
                    name="French Installer",
                    href="/download/game/fr",
                    size=1060000,
                    md5="fr123",
                    os_type="windows",
                    lang="fr",
                    version="1.0",
                    desc="French installer",
                    updated=datetime(2024, 1, 1),
                    verified=False,
                ),
            ],
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

    def test_filter_games_no_filters(self, manifest_service, sample_game, sample_game_2):
        """Test filtering with no filters returns all games."""
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        filtered = manifest_service.filter_games()
        
        assert len(filtered) == 2
        assert any(g.id == sample_game.id for g in filtered)
        assert any(g.id == sample_game_2.id for g in filtered)

    def test_filter_games_empty_filters(self, manifest_service, sample_game, sample_game_2):
        """Test filtering with empty filter lists returns all games."""
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        filtered = manifest_service.filter_games(os_types=[], languages=[])
        
        assert len(filtered) == 2

    def test_filter_games_by_os_single(self, manifest_service, multi_os_game):
        """Test filtering by single OS type."""
        manifest_service._manifest_cache = {multi_os_game.id: multi_os_game}
        
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        assert len(filtered) == 1
        assert filtered[0].id == multi_os_game.id
        assert len(filtered[0].downloads) == 1
        assert filtered[0].downloads[0].os_type == "windows"

    def test_filter_games_by_os_multiple(self, manifest_service, multi_os_game):
        """Test filtering by multiple OS types."""
        manifest_service._manifest_cache = {multi_os_game.id: multi_os_game}
        
        filtered = manifest_service.filter_games(os_types=['windows', 'linux'])
        
        assert len(filtered) == 1
        assert len(filtered[0].downloads) == 2
        os_types = {d.os_type for d in filtered[0].downloads}
        assert os_types == {'windows', 'linux'}

    def test_filter_games_by_language_single(self, manifest_service, multi_lang_game):
        """Test filtering by single language."""
        manifest_service._manifest_cache = {multi_lang_game.id: multi_lang_game}
        
        filtered = manifest_service.filter_games(languages=['en'])
        
        assert len(filtered) == 1
        assert len(filtered[0].downloads) == 1
        assert filtered[0].downloads[0].lang == "en"

    def test_filter_games_by_language_multiple(self, manifest_service, multi_lang_game):
        """Test filtering by multiple languages."""
        manifest_service._manifest_cache = {multi_lang_game.id: multi_lang_game}
        
        filtered = manifest_service.filter_games(languages=['en', 'de'])
        
        assert len(filtered) == 1
        assert len(filtered[0].downloads) == 2
        langs = {d.lang for d in filtered[0].downloads}
        assert langs == {'en', 'de'}

    def test_filter_games_by_os_and_language(self, manifest_service):
        """Test filtering by both OS and language."""
        game = Game(
            id=12,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game",
            downloads=[
                Download(
                    name="Win EN",
                    href="/1",
                    size=1000,
                    md5="1",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
                Download(
                    name="Win DE",
                    href="/2",
                    size=1000,
                    md5="2",
                    os_type="windows",
                    lang="de",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
                Download(
                    name="Linux EN",
                    href="/3",
                    size=1000,
                    md5="3",
                    os_type="linux",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
            ],
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
        manifest_service._manifest_cache = {game.id: game}
        
        filtered = manifest_service.filter_games(
            os_types=['windows'],
            languages=['en']
        )
        
        assert len(filtered) == 1
        assert len(filtered[0].downloads) == 1
        assert filtered[0].downloads[0].os_type == "windows"
        assert filtered[0].downloads[0].lang == "en"

    def test_filter_games_excludes_no_match(self, manifest_service, sample_game, sample_game_2):
        """Test that games with no matching downloads are excluded."""
        # sample_game has windows downloads, sample_game_2 has linux
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
        }
        
        filtered = manifest_service.filter_games(os_types=['mac'])
        
        # No games should match
        assert len(filtered) == 0

    def test_filter_games_case_insensitive(self, manifest_service, multi_os_game):
        """Test that filtering is case-insensitive."""
        manifest_service._manifest_cache = {multi_os_game.id: multi_os_game}
        
        # Use uppercase filter
        filtered = manifest_service.filter_games(os_types=['WINDOWS'])
        
        assert len(filtered) == 1
        assert len(filtered[0].downloads) == 1
        assert filtered[0].downloads[0].os_type == "windows"

    def test_filter_games_preserves_original(self, manifest_service, multi_os_game):
        """Test that filtering doesn't modify the original game in cache."""
        manifest_service._manifest_cache = {multi_os_game.id: multi_os_game}
        original_download_count = len(multi_os_game.downloads)
        
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        # Original game should still have all downloads
        assert len(multi_os_game.downloads) == original_download_count
        assert len(manifest_service._manifest_cache[multi_os_game.id].downloads) == original_download_count
        
        # Filtered game should have fewer
        assert len(filtered[0].downloads) < original_download_count

    def test_filter_games_filters_galaxy_downloads(self, manifest_service):
        """Test that filtering applies to galaxy downloads."""
        game = Game(
            id=13,
            title="Galaxy Game",
            folder_name="galaxy_game",
            long_title="Galaxy Game",
            downloads=[],
            galaxy_downloads=[
                Download(
                    name="Galaxy Win",
                    href="/gal/win",
                    size=1000,
                    md5="gw",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
                Download(
                    name="Galaxy Linux",
                    href="/gal/lin",
                    size=1000,
                    md5="gl",
                    os_type="linux",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
            ],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=False,
        )
        manifest_service._manifest_cache = {game.id: game}
        
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        assert len(filtered) == 1
        assert len(filtered[0].galaxy_downloads) == 1
        assert filtered[0].galaxy_downloads[0].os_type == "windows"

    def test_filter_games_filters_shared_downloads(self, manifest_service):
        """Test that filtering applies to shared downloads."""
        game = Game(
            id=14,
            title="Shared Game",
            folder_name="shared_game",
            long_title="Shared Game",
            downloads=[],
            galaxy_downloads=[],
            shared_downloads=[
                Download(
                    name="Shared Win",
                    href="/shared/win",
                    size=1000,
                    md5="sw",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
                Download(
                    name="Shared Mac",
                    href="/shared/mac",
                    size=1000,
                    md5="sm",
                    os_type="mac",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
            ],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=False,
        )
        manifest_service._manifest_cache = {game.id: game}
        
        filtered = manifest_service.filter_games(os_types=['mac'])
        
        assert len(filtered) == 1
        assert len(filtered[0].shared_downloads) == 1
        assert filtered[0].shared_downloads[0].os_type == "mac"

    def test_filter_games_includes_if_any_download_matches(self, manifest_service):
        """Test that game is included if any download type matches."""
        game = Game(
            id=15,
            title="Mixed Game",
            folder_name="mixed_game",
            long_title="Mixed Game",
            downloads=[
                Download(
                    name="Regular Linux",
                    href="/reg/lin",
                    size=1000,
                    md5="rl",
                    os_type="linux",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
            ],
            galaxy_downloads=[
                Download(
                    name="Galaxy Win",
                    href="/gal/win",
                    size=1000,
                    md5="gw",
                    os_type="windows",
                    lang="en",
                    version="1.0",
                    desc="",
                    updated=None,
                    verified=False,
                ),
            ],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=False,
        )
        manifest_service._manifest_cache = {game.id: game}
        
        # Filter for windows - should include game because galaxy download matches
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        assert len(filtered) == 1
        assert len(filtered[0].downloads) == 0  # Regular download filtered out
        assert len(filtered[0].galaxy_downloads) == 1  # Galaxy download included

    def test_filter_games_empty_manifest(self, manifest_service):
        """Test filtering on empty manifest."""
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        assert len(filtered) == 0

    def test_filter_games_multiple_games_mixed_results(
        self, manifest_service, sample_game, sample_game_2, multi_os_game
    ):
        """Test filtering multiple games with mixed results."""
        # sample_game: windows/en
        # sample_game_2: linux/en
        # multi_os_game: windows/linux/mac, all en
        manifest_service._manifest_cache = {
            sample_game.id: sample_game,
            sample_game_2.id: sample_game_2,
            multi_os_game.id: multi_os_game,
        }
        
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        # Should get sample_game and multi_os_game (with only windows downloads)
        assert len(filtered) == 2
        game_ids = {g.id for g in filtered}
        assert sample_game.id in game_ids
        assert multi_os_game.id in game_ids
        assert sample_game_2.id not in game_ids
        
        # multi_os_game should only have windows download
        multi_os_filtered = next(g for g in filtered if g.id == multi_os_game.id)
        assert len(multi_os_filtered.downloads) == 1
        assert multi_os_filtered.downloads[0].os_type == "windows"

    def test_filter_games_preserves_extras(self, manifest_service, sample_game):
        """Test that filtering preserves extras (they are not filtered)."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        # Extras should be preserved
        assert len(filtered[0].extras) == len(sample_game.extras)
        assert filtered[0].extras[0].name == sample_game.extras[0].name

    def test_filter_games_preserves_metadata(self, manifest_service, sample_game):
        """Test that filtering preserves game metadata."""
        manifest_service._manifest_cache = {sample_game.id: sample_game}
        
        filtered = manifest_service.filter_games(os_types=['windows'])
        
        # Metadata should be preserved
        assert filtered[0].id == sample_game.id
        assert filtered[0].title == sample_game.title
        assert filtered[0].folder_name == sample_game.folder_name
        assert filtered[0].long_title == sample_game.long_title
        assert filtered[0].serials == sample_game.serials
        assert filtered[0].changelog == sample_game.changelog
        assert filtered[0].image_url == sample_game.image_url
        assert filtered[0].has_updates == sample_game.has_updates


