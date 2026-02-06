"""Unit tests for the AuthService class."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import httpx

from gogrepoc.services.auth import AuthService
from gogrepoc.core.models import Token
from gogrepoc.core.exceptions import AuthError
from gogrepoc.infrastructure.storage import Storage
from gogrepoc.infrastructure.http_client import HTTPClient


@pytest.fixture
def mock_storage(tmp_path):
    """Create a mock Storage instance."""
    storage = Storage(tmp_path)
    return storage


@pytest.fixture
def mock_http_client():
    """Create a mock HTTPClient instance."""
    client = Mock(spec=HTTPClient)
    return client


@pytest.fixture
def auth_service(mock_storage, mock_http_client):
    """Create an AuthService instance with mocked dependencies."""
    return AuthService(mock_storage, mock_http_client)


@pytest.fixture
def sample_token():
    """Create a sample token for testing."""
    return Token(
        access_token="test_access_token_123",
        refresh_token="test_refresh_token_456",
        expires_at=datetime.now() + timedelta(hours=1),
        user_id="test_user_123",
    )


@pytest.fixture
def expired_token():
    """Create an expired token for testing."""
    return Token(
        access_token="expired_access_token",
        refresh_token="expired_refresh_token",
        expires_at=datetime.now() - timedelta(hours=1),
        user_id="test_user_123",
    )


class TestAuthServiceInit:
    """Tests for AuthService initialization."""

    def test_init_with_dependencies(self, mock_storage, mock_http_client):
        """Test initialization with storage and HTTP client."""
        service = AuthService(mock_storage, mock_http_client)
        
        assert service.storage == mock_storage
        assert service.http_client == mock_http_client
        assert service._cached_token is None

    def test_auth_endpoints_defined(self, auth_service):
        """Test that authentication endpoints are defined."""
        assert hasattr(AuthService, "AUTH_URL")
        assert hasattr(AuthService, "LOGIN_URL")
        assert hasattr(AuthService, "CLIENT_ID")
        assert hasattr(AuthService, "CLIENT_SECRET")
        assert hasattr(AuthService, "REDIRECT_URI")
        
        assert "auth.gog.com" in AuthService.AUTH_URL
        assert "login.gog.com" in AuthService.LOGIN_URL


class TestLogin:
    """Tests for login method."""

    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_http_client):
        """Test successful login flow."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        # Perform login
        token = await auth_service.login("test@example.com", "password123")
        
        # Verify token
        assert token.access_token == "new_access_token"
        assert token.refresh_token == "new_refresh_token"
        assert token.user_id == "user_123"
        assert token.expires_at > datetime.now()
        
        # Verify token was cached
        assert auth_service._cached_token == token
        
        # Verify HTTP client was called correctly
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert AuthService.AUTH_URL in call_args[0]
        assert "username" in call_args[1]["data"]
        assert "password" in call_args[1]["data"]

    @pytest.mark.asyncio
    async def test_login_with_2fa_code(self, auth_service, mock_http_client):
        """Test login with two-factor authentication code."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        token = await auth_service.login("test@example.com", "password123", two_factor_code="123456")
        
        assert token.access_token == "new_access_token"
        
        # Verify 2FA code was included in request
        call_args = mock_http_client.post.call_args
        assert "two_step_code" in call_args[1]["data"]
        assert call_args[1]["data"]["two_step_code"] == "123456"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, auth_service, mock_http_client):
        """Test login with invalid credentials."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid username or password",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login("test@example.com", "wrong_password")
        
        assert "Invalid username or password" in str(exc_info.value)
        assert exc_info.value.username == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_2fa_required(self, auth_service, mock_http_client):
        """Test login when 2FA is required."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": "two_factor_required",
            "error_description": "Two-factor authentication required",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login("test@example.com", "password123")
        
        assert "Two-factor authentication required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_missing_tokens_in_response(self, auth_service, mock_http_client):
        """Test login when API response is missing tokens."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "expires_in": 3600,
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login("test@example.com", "password123")
        
        assert "Invalid token response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_network_error(self, auth_service, mock_http_client):
        """Test login when network error occurs."""
        mock_http_client.post = AsyncMock(side_effect=Exception("Network error"))
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login("test@example.com", "password123")
        
        assert "Login failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_saves_token_to_storage(self, auth_service, mock_http_client, mock_storage):
        """Test that login saves token to storage."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        token = await auth_service.login("test@example.com", "password123")
        
        # Verify token was saved to storage
        loaded_token = mock_storage.load_token()
        assert loaded_token is not None
        assert loaded_token.access_token == token.access_token


class TestTokenRefresh:
    """Tests for token refresh logic."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_http_client, sample_token):
        """Test successful token refresh."""
        # Set up existing token
        auth_service._cached_token = sample_token
        
        # Mock refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        # Refresh token
        new_token = await auth_service.refresh_token()
        
        # Verify new token
        assert new_token.access_token == "refreshed_access_token"
        assert new_token.refresh_token == "refreshed_refresh_token"
        assert new_token.expires_at > datetime.now()
        
        # Verify cached token was updated
        assert auth_service._cached_token == new_token
        
        # Verify HTTP client was called with refresh grant
        call_args = mock_http_client.post.call_args
        assert call_args[1]["data"]["grant_type"] == "refresh_token"
        assert call_args[1]["data"]["refresh_token"] == sample_token.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_no_cached_token(self, auth_service, mock_http_client, mock_storage, sample_token):
        """Test refresh when token is not cached but exists in storage."""
        # Save token to storage but not cache
        mock_storage.save_token(sample_token)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        new_token = await auth_service.refresh_token()
        
        assert new_token.access_token == "refreshed_access_token"

    @pytest.mark.asyncio
    async def test_refresh_token_no_token_available(self, auth_service):
        """Test refresh when no token is available."""
        with pytest.raises(AuthError) as exc_info:
            await auth_service.refresh_token()
        
        assert "No token available to refresh" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_api_error(self, auth_service, mock_http_client, sample_token):
        """Test refresh when API returns error."""
        auth_service._cached_token = sample_token
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Refresh token expired",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.refresh_token()
        
        assert "Token refresh failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_saves_to_storage(self, auth_service, mock_http_client, mock_storage, sample_token):
        """Test that refresh saves new token to storage."""
        auth_service._cached_token = sample_token
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        new_token = await auth_service.refresh_token()
        
        # Verify new token was saved
        loaded_token = mock_storage.load_token()
        assert loaded_token is not None
        assert loaded_token.access_token == "refreshed_access_token"


class TestTokenExpiration:
    """Tests for token expiration checking."""

    def test_is_token_expired_valid_token(self, auth_service, sample_token):
        """Test checking expiration of valid token."""
        assert not auth_service._is_token_expired(sample_token)

    def test_is_token_expired_expired_token(self, auth_service, expired_token):
        """Test checking expiration of expired token."""
        assert auth_service._is_token_expired(expired_token)

    def test_is_token_expired_about_to_expire(self, auth_service):
        """Test checking expiration of token about to expire (within 5 min buffer)."""
        # Token expires in 3 minutes (within 5 minute buffer)
        token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=datetime.now() + timedelta(minutes=3),
            user_id="test",
        )
        
        assert auth_service._is_token_expired(token)

    def test_is_token_expired_just_outside_buffer(self, auth_service):
        """Test token that expires just outside the 5 minute buffer."""
        # Token expires in 6 minutes (outside 5 minute buffer)
        token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=datetime.now() + timedelta(minutes=6),
            user_id="test",
        )
        
        assert not auth_service._is_token_expired(token)


class TestGetValidToken:
    """Tests for get_valid_token method."""

    @pytest.mark.asyncio
    async def test_get_valid_token_cached_valid(self, auth_service, sample_token):
        """Test getting valid token from cache."""
        auth_service._cached_token = sample_token
        
        token = await auth_service.get_valid_token()
        
        assert token == sample_token

    @pytest.mark.asyncio
    async def test_get_valid_token_from_storage(self, auth_service, mock_storage, sample_token):
        """Test getting valid token from storage when not cached."""
        mock_storage.save_token(sample_token)
        
        token = await auth_service.get_valid_token()
        
        assert token.access_token == sample_token.access_token

    @pytest.mark.asyncio
    async def test_get_valid_token_no_token(self, auth_service):
        """Test getting valid token when none exists."""
        with pytest.raises(AuthError) as exc_info:
            await auth_service.get_valid_token()
        
        assert "No authentication token found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_valid_token_expired_refreshes(self, auth_service, mock_http_client, expired_token):
        """Test that expired token is automatically refreshed."""
        auth_service._cached_token = expired_token
        
        # Mock refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        token = await auth_service.get_valid_token()
        
        # Should return refreshed token
        assert token.access_token == "refreshed_access_token"


class TestAuthenticationStatus:
    """Tests for is_authenticated method."""

    def test_is_authenticated_valid_token(self, auth_service, sample_token):
        """Test authentication status with valid token."""
        auth_service._cached_token = sample_token
        
        assert auth_service.is_authenticated() is True

    def test_is_authenticated_expired_token(self, auth_service, expired_token):
        """Test authentication status with expired token."""
        auth_service._cached_token = expired_token
        
        assert auth_service.is_authenticated() is False

    def test_is_authenticated_no_token(self, auth_service):
        """Test authentication status with no token."""
        assert auth_service.is_authenticated() is False

    def test_is_authenticated_loads_from_storage(self, auth_service, mock_storage, sample_token):
        """Test that is_authenticated loads token from storage if not cached."""
        mock_storage.save_token(sample_token)
        
        assert auth_service.is_authenticated() is True
        
        # Verify token was loaded into cache
        assert auth_service._cached_token is not None


class TestTwoFactorAuthentication:
    """Tests for two-factor authentication support."""

    def test_requires_two_factor_positive(self, auth_service):
        """Test detecting 2FA requirement from error message."""
        error_messages = [
            "Two-factor authentication required",
            "Please enter your second factor code",
            "2FA verification needed",
            "Two factor authentication is enabled",
            "Authentication code required",
            "Verification code needed",
        ]
        
        for msg in error_messages:
            assert auth_service.requires_two_factor(msg) is True

    def test_requires_two_factor_negative(self, auth_service):
        """Test not detecting 2FA when not required."""
        error_messages = [
            "Invalid username or password",
            "Account locked",
            "Network error",
            "Server unavailable",
        ]
        
        for msg in error_messages:
            assert auth_service.requires_two_factor(msg) is False

    def test_requires_two_factor_case_insensitive(self, auth_service):
        """Test that 2FA detection is case insensitive."""
        assert auth_service.requires_two_factor("TWO-FACTOR REQUIRED") is True
        assert auth_service.requires_two_factor("Two-Factor Required") is True
        assert auth_service.requires_two_factor("two-factor required") is True

    @pytest.mark.asyncio
    async def test_login_with_2fa_convenience_method(self, auth_service, mock_http_client):
        """Test login_with_2fa convenience method."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        token = await auth_service.login_with_2fa("test@example.com", "password123", "123456")
        
        assert token.access_token == "new_access_token"
        
        # Verify 2FA code was included
        call_args = mock_http_client.post.call_args
        assert call_args[1]["data"]["two_step_code"] == "123456"


class TestAuthServiceIntegration:
    """Integration tests for complete authentication flows."""

    @pytest.mark.asyncio
    async def test_complete_login_flow(self, auth_service, mock_http_client, mock_storage):
        """Test complete login flow from start to finish."""
        # Mock login response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_in": 3600,
            "user_id": "user_789",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        # Login
        token = await auth_service.login("user@example.com", "password")
        
        # Verify authentication status
        assert auth_service.is_authenticated() is True
        
        # Verify token can be retrieved
        valid_token = await auth_service.get_valid_token()
        assert valid_token.access_token == "access_123"
        
        # Verify token persisted to storage
        loaded_token = mock_storage.load_token()
        assert loaded_token.access_token == "access_123"

    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, auth_service, mock_http_client, mock_storage):
        """Test token refresh flow."""
        # Create expired token
        expired = Token(
            access_token="old_access",
            refresh_token="old_refresh",
            expires_at=datetime.now() - timedelta(hours=1),
            user_id="user_123",
        )
        mock_storage.save_token(expired)
        
        # Mock refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)
        
        # Get valid token should trigger refresh
        token = await auth_service.get_valid_token()
        
        assert token.access_token == "new_access"
        assert auth_service.is_authenticated() is True
