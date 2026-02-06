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
        # Mock auth page response with login form
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with redirect containing code
        login_response = Mock()
        login_response.text = "<html></html>"
        login_response.url = "https://embed.gog.com/on_login_success?code=test_auth_code_123"
        
        # Mock token exchange response
        token_response = Mock()
        token_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        
        # Setup mock to return different responses for different calls
        mock_http_client.get = AsyncMock(side_effect=[auth_page_response, token_response])
        mock_http_client.post = AsyncMock(return_value=login_response)
        
        # Perform login
        token = await auth_service.login("test@example.com", "password123")
        
        # Verify token
        assert token.access_token == "new_access_token"
        assert token.refresh_token == "new_refresh_token"
        assert token.user_id == "user_123"
        assert token.expires_at > datetime.now()
        
        # Verify token was cached
        assert auth_service._cached_token == token

    @pytest.mark.asyncio
    async def test_login_with_2fa_code(self, auth_service, mock_http_client):
        """Test login with two-factor authentication code."""
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with 2FA redirect
        login_response = Mock()
        login_response.text = '''
        <html>
            <form>
                <input id="two_factor_totp_authentication__token" value="totp_token_123" />
            </form>
        </html>
        '''
        login_response.url = "https://login.gog.com/totp"
        
        # Mock 2FA response with success redirect
        totp_response = Mock()
        totp_response.text = "<html></html>"
        totp_response.url = "https://embed.gog.com/on_login_success?code=test_auth_code_456"
        
        # Mock token exchange response
        token_response = Mock()
        token_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        
        mock_http_client.get = AsyncMock(side_effect=[auth_page_response, token_response])
        mock_http_client.post = AsyncMock(side_effect=[login_response, totp_response])
        
        token = await auth_service.login("test@example.com", "password123", two_factor_code="123456")
        
        assert token.access_token == "new_access_token"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, auth_service, mock_http_client):
        """Test login with invalid credentials."""
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response that stays on login page (no redirect)
        login_response = Mock()
        login_response.text = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
                <div class="error">Invalid username or password</div>
            </form>
        </html>
        '''
        login_response.url = "https://login.gog.com/login_check"
        
        mock_http_client.get = AsyncMock(return_value=auth_page_response)
        mock_http_client.post = AsyncMock(return_value=login_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login("test@example.com", "wrong_password")
        
        assert "Login failed" in str(exc_info.value)
        assert exc_info.value.username == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_2fa_required(self, auth_service, mock_http_client):
        """Test login when 2FA is required."""
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with 2FA redirect (but no 2FA code provided)
        login_response = Mock()
        login_response.text = '''
        <html>
            <form>
                <input id="two_factor_totp_authentication__token" value="totp_token_123" />
            </form>
        </html>
        '''
        login_response.url = "https://login.gog.com/totp"
        
        mock_http_client.get = AsyncMock(return_value=auth_page_response)
        mock_http_client.post = AsyncMock(return_value=login_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login("test@example.com", "password123")
        
        assert "Two-factor authentication" in str(exc_info.value) or "TOTP" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_missing_tokens_in_response(self, auth_service, mock_http_client):
        """Test login when API response is missing tokens."""
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with redirect
        login_response = Mock()
        login_response.text = "<html></html>"
        login_response.url = "https://embed.gog.com/on_login_success?code=test_code"
        
        # Mock token exchange response missing tokens
        token_response = Mock()
        token_response.json.return_value = {
            "expires_in": 3600,
        }
        
        mock_http_client.get = AsyncMock(side_effect=[auth_page_response, token_response])
        mock_http_client.post = AsyncMock(return_value=login_response)
        
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
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with redirect
        login_response = Mock()
        login_response.text = "<html></html>"
        login_response.url = "https://embed.gog.com/on_login_success?code=test_code"
        
        # Mock token exchange response
        token_response = Mock()
        token_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        
        mock_http_client.get = AsyncMock(side_effect=[auth_page_response, token_response])
        mock_http_client.post = AsyncMock(return_value=login_response)
        
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
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with 2FA redirect
        login_response = Mock()
        login_response.text = '''
        <html>
            <form>
                <input id="two_factor_totp_authentication__token" value="totp_token_123" />
            </form>
        </html>
        '''
        login_response.url = "https://login.gog.com/totp"
        
        # Mock 2FA response with success redirect
        totp_response = Mock()
        totp_response.text = "<html></html>"
        totp_response.url = "https://embed.gog.com/on_login_success?code=test_auth_code_789"
        
        # Mock token exchange response
        token_response = Mock()
        token_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "user_id": "user_123",
        }
        
        mock_http_client.get = AsyncMock(side_effect=[auth_page_response, token_response])
        mock_http_client.post = AsyncMock(side_effect=[login_response, totp_response])
        
        token = await auth_service.login_with_2fa("test@example.com", "password123", "123456")
        
        assert token.access_token == "new_access_token"


class TestAuthServiceIntegration:
    """Integration tests for complete authentication flows."""

    @pytest.mark.asyncio
    async def test_complete_login_flow(self, auth_service, mock_http_client, mock_storage):
        """Test complete login flow from start to finish."""
        # Mock auth page response
        auth_page_html = '''
        <html>
            <form name="login">
                <input id="login__token" value="test_login_token_123" />
            </form>
        </html>
        '''
        auth_page_response = Mock()
        auth_page_response.text = auth_page_html
        auth_page_response.url = "https://auth.gog.com/auth"
        
        # Mock login response with redirect
        login_response = Mock()
        login_response.text = "<html></html>"
        login_response.url = "https://embed.gog.com/on_login_success?code=test_code"
        
        # Mock token exchange response
        token_response = Mock()
        token_response.json.return_value = {
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_in": 3600,
            "user_id": "user_789",
        }
        
        mock_http_client.get = AsyncMock(side_effect=[auth_page_response, token_response])
        mock_http_client.post = AsyncMock(return_value=login_response)
        
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


class TestOAuthMethods:
    """Tests for browser-based OAuth authentication methods."""

    def test_get_auth_url(self, auth_service):
        """Test generation of OAuth authorization URL."""
        url = auth_service.get_auth_url()
        
        # Verify URL structure
        assert url.startswith("https://auth.gog.com/auth?")
        assert "client_id=46899977096215655" in url
        assert "redirect_uri=https%3A%2F%2Fembed.gog.com%2Fon_login_success" in url
        assert "response_type=code" in url
        assert "layout=client2" in url

    def test_get_auth_url_contains_all_required_params(self, auth_service):
        """Test that auth URL contains all required OAuth parameters."""
        from urllib.parse import urlparse, parse_qs
        
        url = auth_service.get_auth_url()
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert "client_id" in params
        assert "redirect_uri" in params
        assert "response_type" in params
        assert "layout" in params
        
        assert params["client_id"][0] == AuthService.CLIENT_ID
        assert params["redirect_uri"][0] == AuthService.REDIRECT_URI
        assert params["response_type"][0] == "code"
        assert params["layout"][0] == "client2"

    @pytest.mark.asyncio
    async def test_login_with_code_success(self, auth_service, mock_http_client, mock_storage):
        """Test successful OAuth code exchange."""
        # Mock token exchange response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "oauth_access_token",
            "refresh_token": "oauth_refresh_token",
            "expires_in": 3600,
            "user_id": "oauth_user_123",
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        # Exchange code for token
        token = await auth_service.login_with_code("test_auth_code_xyz")
        
        # Verify token
        assert token.access_token == "oauth_access_token"
        assert token.refresh_token == "oauth_refresh_token"
        assert token.user_id == "oauth_user_123"
        assert token.expires_at > datetime.now()
        
        # Verify token was cached
        assert auth_service._cached_token == token
        
        # Verify HTTP client was called correctly
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert AuthService.TOKEN_URL in call_args[0]
        
        # Verify request parameters
        params = call_args[1]["params"]
        assert params["client_id"] == AuthService.CLIENT_ID
        assert params["client_secret"] == AuthService.CLIENT_SECRET
        assert params["grant_type"] == "authorization_code"
        assert params["code"] == "test_auth_code_xyz"
        assert params["redirect_uri"] == AuthService.REDIRECT_URI

    @pytest.mark.asyncio
    async def test_login_with_code_saves_to_storage(self, auth_service, mock_http_client, mock_storage):
        """Test that OAuth login saves token to storage."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "oauth_access_token",
            "refresh_token": "oauth_refresh_token",
            "expires_in": 3600,
            "user_id": "oauth_user_123",
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        token = await auth_service.login_with_code("test_code")
        
        # Verify token was saved to storage
        loaded_token = mock_storage.load_token()
        assert loaded_token is not None
        assert loaded_token.access_token == "oauth_access_token"
        assert loaded_token.refresh_token == "oauth_refresh_token"

    @pytest.mark.asyncio
    async def test_login_with_code_invalid_code(self, auth_service, mock_http_client):
        """Test OAuth code exchange with invalid code."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid authorization code",
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login_with_code("invalid_code")
        
        assert "Token exchange failed" in str(exc_info.value)
        assert "Invalid authorization code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_with_code_missing_tokens(self, auth_service, mock_http_client):
        """Test OAuth code exchange when response is missing tokens."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "expires_in": 3600,
            "user_id": "user_123",
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login_with_code("test_code")
        
        assert "Invalid token response" in str(exc_info.value)
        assert "missing tokens" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_with_code_network_error(self, auth_service, mock_http_client):
        """Test OAuth code exchange with network error."""
        mock_http_client.get = AsyncMock(side_effect=Exception("Connection timeout"))
        
        with pytest.raises(AuthError) as exc_info:
            await auth_service.login_with_code("test_code")
        
        assert "Failed to exchange authorization code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_with_code_calculates_expiration_correctly(self, auth_service, mock_http_client):
        """Test that OAuth login calculates token expiration correctly."""
        import time
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "oauth_access_token",
            "refresh_token": "oauth_refresh_token",
            "expires_in": 7200,  # 2 hours
            "user_id": "oauth_user_123",
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        before_time = time.time()
        token = await auth_service.login_with_code("test_code")
        after_time = time.time()
        
        # Verify expiration is approximately 2 hours from now
        expected_min = datetime.fromtimestamp(before_time + 7200)
        expected_max = datetime.fromtimestamp(after_time + 7200)
        
        assert expected_min <= token.expires_at <= expected_max

    @pytest.mark.asyncio
    async def test_oauth_flow_integration(self, auth_service, mock_http_client, mock_storage):
        """Test complete OAuth flow from URL generation to token storage."""
        # Step 1: Generate auth URL
        auth_url = auth_service.get_auth_url()
        assert "auth.gog.com" in auth_url
        
        # Step 2: Simulate user login and code exchange
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "oauth_access_token",
            "refresh_token": "oauth_refresh_token",
            "expires_in": 3600,
            "user_id": "oauth_user_123",
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        token = await auth_service.login_with_code("auth_code_from_redirect")
        
        # Step 3: Verify authentication status
        assert auth_service.is_authenticated() is True
        
        # Step 4: Verify token can be retrieved
        valid_token = await auth_service.get_valid_token()
        assert valid_token.access_token == "oauth_access_token"
        
        # Step 5: Verify token persisted
        loaded_token = mock_storage.load_token()
        assert loaded_token.access_token == "oauth_access_token"

