"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from typing import Generator
from unittest.mock import Mock


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def temp_game_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for game files."""
    game_dir = tmp_path / "games"
    game_dir.mkdir()
    return game_dir


@pytest.fixture
def temp_manifest_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for manifest files."""
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    return manifest_dir


@pytest.fixture
def mock_http_response() -> Mock:
    """Provide a mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.text = ""
    response.json.return_value = {}
    return response


@pytest.fixture
def sample_game_data() -> dict:
    """Provide sample game data for testing."""
    return {
        "id": 1,
        "title": "test_game",
        "folder_name": "test_game",
        "long_title": "Test Game",
        "downloads": [],
        "galaxy_downloads": [],
        "shared_downloads": [],
        "extras": [],
        "serials": {},
        "changelog": None,
        "image_url": "https://example.com/image.jpg",
        "bg_url": "https://example.com/bg.jpg",
        "store_url": "https://www.gog.com/game/test_game",
        "has_updates": False,
    }


@pytest.fixture
def sample_download_data() -> dict:
    """Provide sample download data for testing."""
    return {
        "name": "test_installer.exe",
        "href": "/download/test_game/1",
        "size": 1024000,
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
        "os_type": "windows",
        "lang": "en",
        "version": "1.0.0",
        "desc": "Test Installer",
        "updated": "2024-01-01T00:00:00Z",
        "verified": False,
    }
