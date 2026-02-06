"""Unit tests for FastAPI endpoints.

Tests all API endpoints with mocked dependencies to ensure proper
request/response handling, error cases, and integration with services.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from gogrepoc.api.main import app
from gogrepoc.core.exceptions import AuthError, NetworkError, FileSystemError
from gogrepoc.core.models import Game, Download, Extra, Token


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_token() -> Token:
    """Create a mock authentication token."""
    return Token(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=datetime.now() + timedelta(hours=1),
        user_id="test_user_123",
    )


@pytest.fixture
def mock_game() -> Game:
    """Create a mock game for testing."""
    return Game(
        id=123,
        title="Test Game",
        folder_name="test_game",
        long_title="Test Game: Complete Edition",
        downloads=[
            Download(
                name="test_game_installer.exe",
                href="/download/123",
                size=1024000,
                md5="abc123",
                os_type="windows",
                lang="en",
                version="1.0",
                desc="Installer",
                updated=datetime.now(),
                verified=False,
            )
        ],
        galaxy_downloads=[],
        shared_downloads=[],
        extras=[
            Extra(
                name="manual.pdf",
                href="/extra/456",
                size=5000,
                desc="Game Manual",
                updated=datetime.now(),
            )
        ],
        serials={"key1": "ABC-123"},
        changelog="Version 1.0 - Initial release",
        image_url="https://example.com/image.jpg",
        bg_url="https://example.com/bg.jpg",
        store_url="https://www.gog.com/game/test_game",
        has_updates=False,
    )


# Authentication endpoint tests
class TestLoginEndpoint:
    """Tests for /api/login endpoint."""

    def test_login_success(self, client: TestClient, mock_token: Token) -> None:
        """Test successful login."""
        # Setup mock
        mock_auth_service = AsyncMock()
        mock_auth_service.login.return_value = mock_token
        
        # Override dependency
        from gogrepoc.api import routes
        app.dependency_overrides[routes.get_auth_service] = lambda: mock_auth_service

        try:
            # Make request
            response = client.post(
                "/api/login",
                json={
                    "username": "test@example.com",
                    "password": "password123",
                },
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["authenticated"] is True
            assert "successful" in data["message"].lower()
        finally:
            # Clean up
            app.dependency_overrides.clear()

    @patch("gogrepoc.api.routes.get_auth_service")
    def test_login_invalid_credentials(self, mock_get_auth, client: TestClient) -> None:
        """Test login with invalid credentials."""
        # Setup mock to raise AuthError
        mock_auth_service = AsyncMock()
        mock_auth_service.login.side_effect = AuthError("Invalid credentials")
        mock_auth_service.requires_two_factor.return_value = False
        mock_get_auth.return_value = mock_auth_service

        # Make request
        response = client.post(
            "/api/login",
            json={
                "username": "test@example.com",
                "password": "wrong_password",
            },
        )

        # Verify response
        assert response.status_code == 401

    @patch("gogrepoc.api.routes.get_auth_service")
    def test_login_requires_2fa(self, mock_get_auth, client: TestClient) -> None:
        """Test login when 2FA is required."""
        # Setup mock
        mock_auth_service = AsyncMock()
        mock_auth_service.login.side_effect = AuthError("Two-factor authentication required")
        mock_auth_service.requires_two_factor.return_value = True
        mock_get_auth.return_value = mock_auth_service

        # Make request
        response = client.post(
            "/api/login",
            json={
                "username": "test@example.com",
                "password": "password123",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["authenticated"] is False
        assert "two-factor" in data["message"].lower()

    @patch("gogrepoc.api.routes.get_auth_service")
    def test_login_with_2fa_code(self, mock_get_auth, client: TestClient, mock_token: Token) -> None:
        """Test login with 2FA code."""
        # Setup mock
        mock_auth_service = AsyncMock()
        mock_auth_service.login.return_value = mock_token
        mock_get_auth.return_value = mock_auth_service

        # Make request
        response = client.post(
            "/api/login",
            json={
                "username": "test@example.com",
                "password": "password123",
                "two_factor_code": "123456",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["authenticated"] is True


class TestCheckAuthEndpoint:
    """Tests for /api/check-auth endpoint."""

    @patch("gogrepoc.api.routes.get_auth_service")
    def test_check_auth_authenticated(
        self, mock_get_auth, client: TestClient, mock_token: Token
    ) -> None:
        """Test check auth when user is authenticated."""
        # Setup mock
        mock_auth_service = AsyncMock()
        mock_auth_service.is_authenticated.return_value = True
        mock_auth_service.get_valid_token.return_value = mock_token
        mock_get_auth.return_value = mock_auth_service

        # Make request
        response = client.get("/api/check-auth")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "test_user_123"

    @patch("gogrepoc.api.routes.get_auth_service")
    def test_check_auth_not_authenticated(self, mock_get_auth, client: TestClient) -> None:
        """Test check auth when user is not authenticated."""
        # Setup mock
        mock_auth_service = AsyncMock()
        mock_auth_service.is_authenticated.return_value = False
        mock_get_auth.return_value = mock_auth_service

        # Make request
        response = client.get("/api/check-auth")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user_id"] is None


# Manifest endpoint tests
class TestManifestEndpoint:
    """Tests for /api/manifest endpoint."""

    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_get_manifest(
        self, mock_get_manifest, client: TestClient, mock_game: Game
    ) -> None:
        """Test getting manifest."""
        # Setup mock
        mock_manifest_service = MagicMock()
        mock_manifest_service.get_all_games.return_value = [mock_game]
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.get("/api/manifest")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["games"]) == 1
        assert data["games"][0]["id"] == 123
        assert data["games"][0]["title"] == "Test Game"

    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_get_manifest_with_filters(
        self, mock_get_manifest, client: TestClient, mock_game: Game
    ) -> None:
        """Test getting manifest with OS and language filters."""
        # Setup mock
        mock_manifest_service = MagicMock()
        mock_manifest_service.filter_games.return_value = [mock_game]
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.get("/api/manifest?os_types=windows&languages=en")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

        # Verify filter was called
        mock_manifest_service.filter_games.assert_called_once()

    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_get_manifest_empty(self, mock_get_manifest, client: TestClient) -> None:
        """Test getting empty manifest."""
        # Setup mock
        mock_manifest_service = MagicMock()
        mock_manifest_service.get_all_games.return_value = []
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.get("/api/manifest")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert len(data["games"]) == 0


# Update endpoint tests
class TestUpdateEndpoint:
    """Tests for /api/update endpoint."""

    @patch("gogrepoc.api.routes.get_gog_api_service")
    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_update_specific_games(
        self,
        mock_get_manifest,
        mock_get_gog_api,
        client: TestClient,
        mock_game: Game,
    ) -> None:
        """Test updating specific games."""
        # Setup mocks
        mock_gog_api = AsyncMock()
        mock_gog_api.get_game_details.return_value = {
            "id": 123,
            "title": "Test Game",
        }
        mock_get_gog_api.return_value = mock_gog_api

        mock_manifest_service = MagicMock()
        mock_manifest_service.get_game_by_id.return_value = mock_game
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.post(
            "/api/update",
            json={
                "game_ids": [123],
                "os_types": ["windows"],
                "languages": ["en"],
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["games_updated"] >= 0
        assert data["games_added"] >= 0

    @patch("gogrepoc.api.routes.get_gog_api_service")
    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_update_auth_error(
        self, mock_get_manifest, mock_get_gog_api, client: TestClient
    ) -> None:
        """Test update with authentication error."""
        # Setup mock to raise AuthError
        mock_gog_api = AsyncMock()
        mock_gog_api.get_game_details.side_effect = AuthError("Not authenticated")
        mock_get_gog_api.return_value = mock_gog_api

        mock_manifest_service = MagicMock()
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.post(
            "/api/update",
            json={
                "game_ids": [123],
            },
        )

        # Verify response
        assert response.status_code == 401


# Download endpoint tests
class TestDownloadEndpoint:
    """Tests for /api/download endpoint."""

    @patch("gogrepoc.api.routes.get_download_service")
    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_start_download(
        self,
        mock_get_manifest,
        mock_get_download,
        client: TestClient,
        mock_game: Game,
    ) -> None:
        """Test starting a download."""
        # Setup mocks
        mock_manifest_service = MagicMock()
        mock_manifest_service.get_game_by_id.return_value = mock_game
        mock_get_manifest.return_value = mock_manifest_service

        mock_download_service = AsyncMock()
        mock_get_download.return_value = mock_download_service

        # Make request
        response = client.post(
            "/api/download",
            json={
                "game_ids": [123],
                "save_dir": "/tmp/games",
                "os_types": ["windows"],
                "languages": ["en"],
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "task_id" in data
        assert len(data["task_id"]) > 0

    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_start_download_game_not_found(
        self, mock_get_manifest, client: TestClient
    ) -> None:
        """Test starting download for non-existent game."""
        # Setup mock
        mock_manifest_service = MagicMock()
        mock_manifest_service.get_game_by_id.return_value = None
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.post(
            "/api/download",
            json={
                "game_ids": [999],
                "save_dir": "/tmp/games",
            },
        )

        # Verify response
        assert response.status_code == 404

    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_start_download_invalid_path(
        self, mock_get_manifest, client: TestClient, mock_game: Game
    ) -> None:
        """Test starting download with relative path."""
        # Setup mock
        mock_manifest_service = MagicMock()
        mock_manifest_service.get_game_by_id.return_value = mock_game
        mock_get_manifest.return_value = mock_manifest_service

        # Make request with relative path
        response = client.post(
            "/api/download",
            json={
                "game_ids": [123],
                "save_dir": "relative/path",
            },
        )

        # Verify response
        assert response.status_code == 400


class TestDownloadProgressEndpoint:
    """Tests for /api/download-progress/{task_id} endpoint."""

    def test_get_progress_task_not_found(self, client: TestClient) -> None:
        """Test getting progress for non-existent task."""
        response = client.get("/api/download-progress/invalid_task_id")
        assert response.status_code == 404


# Add without download endpoint tests
class TestAddWithoutDownloadEndpoint:
    """Tests for /api/add_without_download endpoint."""

    @patch("gogrepoc.api.routes.get_gog_api_service")
    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_add_without_download(
        self, mock_get_manifest, mock_get_gog_api, client: TestClient
    ) -> None:
        """Test adding games without downloading."""
        # Setup mocks
        mock_gog_api = AsyncMock()
        mock_gog_api.get_game_details.return_value = {
            "id": 123,
            "title": "Test Game",
        }
        mock_get_gog_api.return_value = mock_gog_api

        mock_manifest_service = MagicMock()
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.post(
            "/api/add_without_download",
            json={
                "game_ids": [123],
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["games_added"] >= 0

    @patch("gogrepoc.api.routes.get_gog_api_service")
    @patch("gogrepoc.api.routes.get_manifest_service")
    def test_add_without_download_auth_error(
        self, mock_get_manifest, mock_get_gog_api, client: TestClient
    ) -> None:
        """Test add without download with authentication error."""
        # Setup mock to raise AuthError
        mock_gog_api = AsyncMock()
        mock_gog_api.get_game_details.side_effect = AuthError("Not authenticated")
        mock_get_gog_api.return_value = mock_gog_api

        mock_manifest_service = MagicMock()
        mock_get_manifest.return_value = mock_manifest_service

        # Make request
        response = client.post(
            "/api/add_without_download",
            json={
                "game_ids": [123],
            },
        )

        # Verify response
        assert response.status_code == 401


# Health check test
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
