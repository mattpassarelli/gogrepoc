"""Manifest management service.

This module provides the ManifestService class for managing the game manifest,
which tracks all games in the user's GOG library along with their downloadable
content and metadata.
"""

import logging
from typing import Optional

from gogrepoc.core.models import Game, Download
from gogrepoc.infrastructure.storage import Storage

logger = logging.getLogger(__name__)


class ManifestService:
    """Manages game manifest with in-memory caching.

    This service provides a high-level interface for managing the game manifest,
    which contains information about all games in the user's GOG library. It
    maintains an in-memory cache of the manifest for efficient access and
    delegates persistence to the Storage layer.

    The manifest tracks:
    - Game metadata (title, ID, images, etc.)
    - Available downloads (installers, DLCs)
    - Extra files (manuals, artwork, soundtracks)
    - Update status

    Attributes:
        storage: Storage instance for persistence
        _manifest_cache: In-memory cache of games (dict mapping game ID to Game)
    """

    def __init__(self, storage: Storage):
        """Initialize ManifestService with Storage dependency.

        Args:
            storage: Storage instance for loading/saving manifest data
        """
        self.storage = storage
        self._manifest_cache: dict[int, Game] = {}
        logger.debug("ManifestService initialized")

    def load_manifest(self) -> list[Game]:
        """Load manifest from storage into memory cache.

        Loads the game manifest from persistent storage and caches it in memory
        for efficient access. If the manifest file doesn't exist, returns an
        empty list and initializes an empty cache.

        Returns:
            List of Game objects from the manifest

        Raises:
            OSError: If manifest file cannot be read
        """
        games = self.storage.load_manifest()
        
        # Build in-memory cache indexed by game ID
        self._manifest_cache = {game.id: game for game in games}
        
        logger.info(f"Loaded manifest with {len(games)} games into cache")
        return games

    def save_manifest(self) -> None:
        """Save current in-memory manifest to storage.

        Persists the current state of the manifest cache to disk. This should
        be called after any modifications to the manifest (adding/updating games).

        Raises:
            OSError: If manifest file cannot be written
        """
        games = list(self._manifest_cache.values())
        self.storage.save_manifest(games)
        logger.info(f"Saved manifest with {len(games)} games")

    def update_game(self, game: Game) -> None:
        """Update or add a game to the manifest.

        If the game already exists in the manifest (by ID), it is updated.
        The method detects if there are changes by comparing download versions
        and update timestamps, and marks the game with has_updates=True if
        changes are detected.
        
        Otherwise, it is added as a new entry. The manifest is not automatically
        saved to disk - call save_manifest() to persist changes.

        Args:
            game: Game object to add or update
        """
        if game.id in self._manifest_cache:
            logger.debug(f"Updating existing game: {game.title} (ID: {game.id})")
            
            # Check if game has updates by comparing with existing version
            existing_game = self._manifest_cache[game.id]
            has_updates = self._detect_game_updates(existing_game, game)
            
            if has_updates:
                logger.info(f"Game has updates: {game.title} (ID: {game.id})")
                # Mark the game as having updates
                game.has_updates = True
            else:
                # Preserve existing has_updates flag if no new updates detected
                game.has_updates = existing_game.has_updates
        else:
            logger.debug(f"Adding new game: {game.title} (ID: {game.id})")
            # New games don't have updates
            game.has_updates = False
        
        self._manifest_cache[game.id] = game

    def _detect_game_updates(self, old_game: Game, new_game: Game) -> bool:
        """Detect if a game has updates by comparing old and new versions.

        Compares download lists, versions, and update timestamps to determine
        if the new game data contains updates compared to the old version.

        Args:
            old_game: Existing game from manifest
            new_game: New game data from GOG API

        Returns:
            True if updates are detected, False otherwise
        """
        # Check if number of downloads changed
        if len(old_game.downloads) != len(new_game.downloads):
            logger.debug(f"Download count changed for {new_game.title}")
            return True
        
        if len(old_game.galaxy_downloads) != len(new_game.galaxy_downloads):
            logger.debug(f"Galaxy download count changed for {new_game.title}")
            return True
        
        if len(old_game.extras) != len(new_game.extras):
            logger.debug(f"Extras count changed for {new_game.title}")
            return True
        
        # Check if any download versions or timestamps changed
        old_downloads_map = {d.href: d for d in old_game.downloads}
        for new_download in new_game.downloads:
            old_download = old_downloads_map.get(new_download.href)
            
            if old_download is None:
                # New download added
                logger.debug(f"New download found: {new_download.name}")
                return True
            
            # Check version changes
            if old_download.version != new_download.version:
                logger.debug(
                    f"Version changed for {new_download.name}: "
                    f"{old_download.version} -> {new_download.version}"
                )
                return True
            
            # Check update timestamp changes
            if old_download.updated != new_download.updated:
                logger.debug(
                    f"Update timestamp changed for {new_download.name}: "
                    f"{old_download.updated} -> {new_download.updated}"
                )
                return True
        
        # Check galaxy downloads
        old_galaxy_map = {d.href: d for d in old_game.galaxy_downloads}
        for new_download in new_game.galaxy_downloads:
            old_download = old_galaxy_map.get(new_download.href)
            
            if old_download is None:
                logger.debug(f"New galaxy download found: {new_download.name}")
                return True
            
            if old_download.version != new_download.version:
                logger.debug(
                    f"Galaxy version changed for {new_download.name}: "
                    f"{old_download.version} -> {new_download.version}"
                )
                return True
            
            if old_download.updated != new_download.updated:
                logger.debug(
                    f"Galaxy update timestamp changed for {new_download.name}"
                )
                return True
        
        # Check extras
        old_extras_map = {e.href: e for e in old_game.extras}
        for new_extra in new_game.extras:
            old_extra = old_extras_map.get(new_extra.href)
            
            if old_extra is None:
                logger.debug(f"New extra found: {new_extra.name}")
                return True
            
            if old_extra.updated != new_extra.updated:
                logger.debug(
                    f"Extra update timestamp changed for {new_extra.name}"
                )
                return True
        
        # No updates detected
        return False

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        """Retrieve a game from the manifest by its ID.

        Args:
            game_id: GOG game ID to look up

        Returns:
            Game object if found, None otherwise
        """
        game = self._manifest_cache.get(game_id)
        
        if game:
            logger.debug(f"Found game: {game.title} (ID: {game_id})")
        else:
            logger.debug(f"Game not found: ID {game_id}")
        
        return game

    def get_all_games(self) -> list[Game]:
        """Get all games from the manifest.

        Returns:
            List of all Game objects in the manifest
        """
        return list(self._manifest_cache.values())

    def get_game_count(self) -> int:
        """Get the total number of games in the manifest.

        Returns:
            Number of games in the manifest
        """
        return len(self._manifest_cache)

    def filter_games(
        self,
        os_types: list[str] | None = None,
        languages: list[str] | None = None
    ) -> list[Game]:
        """Filter games by OS type and language.

        Returns a filtered list of games where each game only includes downloads
        that match the specified OS types and languages. Games with no matching
        downloads after filtering are excluded from the results.

        Args:
            os_types: List of OS types to include (e.g., ['windows', 'linux']).
                     If None or empty, all OS types are included.
            languages: List of language codes to include (e.g., ['en', 'de']).
                      If None or empty, all languages are included.

        Returns:
            List of Game objects with filtered downloads. Each game is a copy
            with only the downloads matching the filter criteria.

        Example:
            # Filter for Windows and Linux games in English
            filtered = service.filter_games(
                os_types=['windows', 'linux'],
                languages=['en']
            )
        """
        from copy import deepcopy
        
        # If no filters specified, return all games
        if not os_types and not languages:
            return self.get_all_games()
        
        # Normalize filters to lowercase for case-insensitive matching
        os_filter = set(os.lower() for os in os_types) if os_types else None
        lang_filter = set(lang.lower() for lang in languages) if languages else None
        
        filtered_games = []
        
        for game in self._manifest_cache.values():
            # Create a deep copy to avoid modifying the original game
            filtered_game = deepcopy(game)
            
            # Filter downloads
            filtered_game.downloads = self._filter_downloads(
                game.downloads, os_filter, lang_filter
            )
            
            # Filter galaxy downloads
            filtered_game.galaxy_downloads = self._filter_downloads(
                game.galaxy_downloads, os_filter, lang_filter
            )
            
            # Filter shared downloads
            filtered_game.shared_downloads = self._filter_downloads(
                game.shared_downloads, os_filter, lang_filter
            )
            
            # Only include game if it has at least one matching download
            if (filtered_game.downloads or 
                filtered_game.galaxy_downloads or 
                filtered_game.shared_downloads):
                filtered_games.append(filtered_game)
        
        logger.info(
            f"Filtered {len(self._manifest_cache)} games to {len(filtered_games)} "
            f"games (OS: {os_types}, Languages: {languages})"
        )
        
        return filtered_games

    def _filter_downloads(
        self,
        downloads: list[Download],
        os_filter: set[str] | None,
        lang_filter: set[str] | None
    ) -> list[Download]:
        """Filter a list of downloads by OS and language.

        Args:
            downloads: List of Download objects to filter
            os_filter: Set of lowercase OS types to include, or None for all
            lang_filter: Set of lowercase language codes to include, or None for all

        Returns:
            Filtered list of Download objects
        """
        filtered = []
        
        for download in downloads:
            # Check OS filter
            if os_filter and download.os_type.lower() not in os_filter:
                continue
            
            # Check language filter
            if lang_filter and download.lang.lower() not in lang_filter:
                continue
            
            # Download matches all filters
            filtered.append(download)
        
        return filtered

    def clear_manifest(self) -> None:
        """Clear the in-memory manifest cache.

        This does not affect the persisted manifest on disk. Call save_manifest()
        after clearing to persist an empty manifest.
        """
        count = len(self._manifest_cache)
        self._manifest_cache.clear()
        logger.info(f"Cleared manifest cache ({count} games removed)")
