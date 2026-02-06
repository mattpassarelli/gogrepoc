"""Authentication service for GOG API.

This module provides the AuthService class for handling authentication
with the GOG API, including login, token management, and refresh logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from gogrepoc.core.exceptions import AuthError
from gogrepoc.core.models import Token
from gogrepoc.infrastructure.http_client import HTTPClient
from gogrepoc.infrastructure.storage import Storage

logger = logging.getLogger(__name__)


class AuthService:
    """Manages GOG authentication and tokens.

    This service handles all authentication-related operations including:
    - User login with credentials
    - Token storage and retrieval
    - Token refresh when expired
    - Authentication status checking
    - Two-factor authentication support

    Attributes:
        storage: Storage instance for persisting tokens
        http_client: HTTP client for API requests
    """

    # GOG authentication endpoints
    AUTH_URL = "https://auth.gog.com/token"
    LOGIN_URL = "https://login.gog.com/login_check"
    
    # OAuth client credentials for GOG API
    CLIENT_ID = "46899977096215655"
    CLIENT_SECRET = "9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9"
    REDIRECT_URI = "https://embed.gog.com/on_login_success?origin=client"

    def __init__(self, storage: Storage, http_client: HTTPClient):
        """Initialize AuthService with dependencies.

        Args:
            storage: Storage instance for token persistence
            http_client: HTTP client for API requests
        """
        self.storage = storage
        self.http_client = http_client
        self._cached_token: Optional[Token] = None


    async def login(self, username: str, password: str, two_factor_code: Optional[str] = None) -> Token:
        """Authenticate with GOG and obtain access token.

        Sends user credentials to GOG API and retrieves an OAuth token.
        The token is stored both in memory and persisted to disk.

        Args:
            username: GOG account username/email
            password: GOG account password
            two_factor_code: Optional 2FA code if required

        Returns:
            Token object containing access and refresh tokens

        Raises:
            AuthError: If authentication fails (invalid credentials, 2FA required, etc.)
        """
        logger.info(f"Attempting login for user: {username}")

        try:
            # Prepare authentication request data
            auth_data = {
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET,
                "grant_type": "password",
                "username": username,
                "password": password,
            }

            # Add 2FA code if provided
            if two_factor_code:
                auth_data["two_step_code"] = two_factor_code

            # Send authentication request
            response = await self.http_client.post(
                self.AUTH_URL,
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Parse response
            token_data = response.json()

            # Check for errors in response
            if "error" in token_data:
                error_msg = token_data.get("error_description", token_data["error"])
                
                # Check if 2FA is required
                if "two" in error_msg.lower() or "second" in error_msg.lower():
                    raise AuthError("Two-factor authentication required", username=username)
                
                raise AuthError(error_msg, username=username)

            # Extract token information
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            user_id = token_data.get("user_id")

            if not access_token or not refresh_token:
                raise AuthError("Invalid token response from GOG API", username=username)

            # Calculate expiration time
            expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Create token object
            token = Token(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                user_id=user_id,
            )

            # Store token
            self.storage.save_token(token)
            self._cached_token = token

            logger.info(f"Login successful for user: {username}")
            return token

        except AuthError:
            # Re-raise AuthError as-is
            raise
        except Exception as e:
            # Wrap other exceptions in AuthError
            logger.error(f"Login failed for user {username}: {e}")
            raise AuthError(f"Login failed: {str(e)}", username=username) from e


    async def refresh_token(self) -> Token:
        """Refresh an expired access token using the refresh token.

        Uses the stored refresh token to obtain a new access token from GOG API.
        The new token is stored both in memory and persisted to disk.

        Returns:
            New Token object with refreshed access token

        Raises:
            AuthError: If token refresh fails or no refresh token is available
        """
        logger.info("Attempting to refresh token")

        # Load current token if not cached
        if not self._cached_token:
            self._cached_token = self.storage.load_token()

        if not self._cached_token:
            raise AuthError("No token available to refresh. Please login first.")

        try:
            # Prepare refresh request data
            refresh_data = {
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self._cached_token.refresh_token,
            }

            # Send refresh request
            response = await self.http_client.post(
                self.AUTH_URL,
                data=refresh_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Parse response
            token_data = response.json()

            # Check for errors
            if "error" in token_data:
                error_msg = token_data.get("error_description", token_data["error"])
                raise AuthError(f"Token refresh failed: {error_msg}")

            # Extract new token information
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            user_id = token_data.get("user_id", self._cached_token.user_id)

            if not access_token or not refresh_token:
                raise AuthError("Invalid token response during refresh")

            # Calculate new expiration time
            expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Create new token object
            token = Token(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                user_id=user_id,
            )

            # Store new token
            self.storage.save_token(token)
            self._cached_token = token

            logger.info("Token refresh successful")
            return token

        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise AuthError(f"Token refresh failed: {str(e)}") from e

    def _is_token_expired(self, token: Token) -> bool:
        """Check if a token is expired or about to expire.

        Considers a token expired if it expires within the next 5 minutes
        to provide a buffer for API calls.

        Args:
            token: Token to check

        Returns:
            True if token is expired or about to expire, False otherwise
        """
        # Add 5 minute buffer to avoid using tokens that are about to expire
        buffer = timedelta(minutes=5)
        return datetime.now() + buffer >= token.expires_at

    async def get_valid_token(self) -> Token:
        """Get a valid access token, refreshing if necessary.

        This method ensures that a valid, non-expired token is always returned.
        It automatically refreshes the token if it's expired.

        Returns:
            Valid Token object

        Raises:
            AuthError: If no token exists or refresh fails
        """
        # Load token from cache or storage
        if not self._cached_token:
            self._cached_token = self.storage.load_token()

        if not self._cached_token:
            raise AuthError("No authentication token found. Please login first.")

        # Check if token is expired and refresh if needed
        if self._is_token_expired(self._cached_token):
            logger.info("Token expired, refreshing...")
            return await self.refresh_token()

        return self._cached_token


    def is_authenticated(self) -> bool:
        """Check if user is authenticated with a valid token.

        Checks for the existence of a valid, non-expired authentication token.
        Does not make any API calls.

        Returns:
            True if a valid token exists, False otherwise
        """
        # Load token from cache or storage
        if not self._cached_token:
            self._cached_token = self.storage.load_token()

        # No token found
        if not self._cached_token:
            return False

        # Check if token is expired
        if self._is_token_expired(self._cached_token):
            logger.debug("Token exists but is expired")
            return False

        return True


    def requires_two_factor(self, error_message: str) -> bool:
        """Check if an authentication error indicates 2FA is required.

        Analyzes error messages to determine if two-factor authentication
        is needed for login.

        Args:
            error_message: Error message from authentication attempt

        Returns:
            True if 2FA is required, False otherwise
        """
        # Check for common 2FA-related keywords in error message
        two_factor_keywords = [
            "two-factor",
            "two factor",
            "2fa",
            "second factor",
            "authentication code",
            "verification code",
        ]

        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in two_factor_keywords)

    async def login_with_2fa(self, username: str, password: str, two_factor_code: str) -> Token:
        """Authenticate with GOG using two-factor authentication.

        This is a convenience method that calls login() with the 2FA code.
        It's provided for clarity when 2FA is explicitly required.

        Args:
            username: GOG account username/email
            password: GOG account password
            two_factor_code: Two-factor authentication code

        Returns:
            Token object containing access and refresh tokens

        Raises:
            AuthError: If authentication fails
        """
        logger.info(f"Attempting 2FA login for user: {username}")
        return await self.login(username, password, two_factor_code=two_factor_code)
