import json
import secrets
from abc import ABC, abstractmethod
from urllib.parse import urlencode

import httpx
import msal
from loguru import logger

from .exceptions import ConfigurationException, ProviderAuthException
from .models import AuthConfig, GithubAuthConfig, User


class AuthProvider(ABC):
    """Base authentication provider interface."""

    @abstractmethod
    async def get_login_url(self) -> str:
        """Return the URL for initiating login."""
        pass

    @abstractmethod
    async def process_callback(self, code: str, state: str | None = None) -> User:
        """Process the OAuth callback code and return user data."""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate a provider token and return boolean indicating validity."""
        pass


class NoAuthProvider(AuthProvider):
    """Default provider that always authenticates (for development)."""

    def __init__(self):
        self.default_user = User(
            id="guestuser@gmail.com", name="Default User", email="guestuser@gmail.com", provider="none"
        )

    async def get_login_url(self) -> str:
        """Return the URL for initiating login."""
        return "/api/auth/callback?automatic=true"

    async def process_callback(self, code: str | None = None, state: str | None = None) -> User:
        """Process the OAuth callback code and return user data."""
        return self.default_user

    async def validate_token(self, token: str) -> bool:
        """Validate a provider token and return boolean indicating validity."""
        return True


class GithubAuthProvider(AuthProvider):
    """GitHub OAuth authentication provider."""

    def __init__(self, config: AuthConfig):
        if not config.github:
            raise ConfigurationException("GitHub auth configuration is missing")

        self.config = config.github
        self.client_id = self.config.client_id
        self.client_secret = self.config.client_secret
        self.callback_url = self.config.callback_url
        self.scopes = self.config.scopes

    async def get_login_url(self) -> str:
        """Return the GitHub OAuth login URL."""
        state = secrets.token_urlsafe(32)  # Generate a secure random state
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(self.scopes),
            "state": state,
            "allow_signup": "true",
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    async def process_callback(self, code: str, state: str | None = None) -> User:
        """Exchange code for access token and get user info."""
        if not code:
            raise ProviderAuthException("github", "Authorization code is missing")

        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.callback_url,
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data, headers={"Accept": "application/json"})

            if token_response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {token_response.text}")
                raise ProviderAuthException("github", "Failed to exchange code for access token")

            token_json = token_response.json()
            access_token = token_json.get("access_token")

            if not access_token:
                logger.error(f"No access token in GitHub response: {token_json}")
                raise ProviderAuthException("github", "No access token received")

            # Get user info with the access token
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}", "Accept": "application/json"},
            )

            if user_response.status_code != 200:
                logger.error(f"GitHub user info fetch failed: {user_response.text}")
                raise ProviderAuthException("github", "Failed to fetch user information")

            user_data = user_response.json()

            # Get user emails if scope includes email
            email = None
            if "user:email" in self.scopes:
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {access_token}", "Accept": "application/json"},
                )

                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_emails = [e for e in emails if e.get("primary") is True]
                    if primary_emails:
                        email = primary_emails[0].get("email")

            # Create User object
            return User(
                id=str(user_data.get("id")),
                name=user_data.get("name") or user_data.get("login"),
                email=email,
                avatar_url=user_data.get("avatar_url"),
                provider="github",
                metadata={
                    "login": user_data.get("login"),
                    "github_id": user_data.get("id"),
                    "access_token": access_token,
                },
            )

    async def validate_token(self, token: str) -> bool:
        """Validate a GitHub access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user", headers={"Authorization": f"token {token}", "Accept": "application/json"}
            )
            return response.status_code == 200


class MSALAuthProvider(AuthProvider):
    """Microsoft Authentication Library (MSAL) provider."""

    def __init__(self, config: AuthConfig):
        if not config.msal:
            raise ConfigurationException("MSAL auth configuration is missing")

        self.config = config.msal
        self.tenant_id = self.config.tenant_id
        self.client_id = self.config.client_id
        self.client_secret = self.config.client_secret
        self.callback_url = self.config.callback_url
        self.scopes = self.config.scopes

        # Initialize MSAL Confidential Client Application
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=authority,
        )

    async def get_login_url(self) -> str:
        """Return the Microsoft OAuth login URL."""
        state = secrets.token_urlsafe(32)  # Generate a secure random state
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.callback_url,
        )
        return auth_url

    async def process_callback(self, code: str, state: str | None = None) -> User:
        """Exchange code for access token and get user info."""
        if not code:
            raise ProviderAuthException("msal", "Authorization code is missing")

        try:
            # Exchange code for access token
            result = self.msal_app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.scopes,
                redirect_uri=self.callback_url,
            )

            if "error" in result:
                logger.error(f"MSAL token exchange failed: {result.get('error_description', result.get('error'))}")
                raise ProviderAuthException("msal", f"Failed to exchange code for access token: {result.get('error')}")

            access_token = result.get("access_token")
            if not access_token:
                logger.error(f"No access token in MSAL response: {result}")
                raise ProviderAuthException("msal", "No access token received")

            # Get user info with the access token
            async with httpx.AsyncClient() as client:
                user_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                )

                if user_response.status_code != 200:
                    logger.error(f"Microsoft Graph user info fetch failed: {user_response.text}")
                    raise ProviderAuthException("msal", "Failed to fetch user information")

                user_data = user_response.json()

                # Create User object
                return User(
                    id=str(user_data.get("id")),
                    name=user_data.get("displayName") or user_data.get("userPrincipalName"),
                    email=user_data.get("mail") or user_data.get("userPrincipalName"),
                    avatar_url=None,  # Microsoft Graph doesn't provide avatar URL in basic profile
                    provider="msal",
                    metadata={
                        "user_principal_name": user_data.get("userPrincipalName"),
                        "tenant_id": self.tenant_id,
                        "object_id": user_data.get("id"),
                        "access_token": access_token,
                        "id_token": result.get("id_token"),
                    },
                )

        except Exception as e:
            if isinstance(e, ProviderAuthException):
                raise
            logger.error(f"MSAL authentication error: {str(e)}")
            raise ProviderAuthException("msal", f"Authentication failed: {str(e)}")

    async def validate_token(self, token: str) -> bool:
        """Validate a Microsoft access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False


class FirebaseAuthProvider(AuthProvider):
    """Firebase authentication provider."""

    def __init__(self, config: AuthConfig):
        if not config.firebase:
            raise ConfigurationException("Firebase auth configuration is missing")

        self.config = config.firebase
        # Firebase provider implementation would go here
        # This is a placeholder - full implementation would use Firebase Admin SDK

    async def get_login_url(self) -> str:
        """Return information for Firebase auth (used differently than OAuth)."""
        # Firebase auth is typically handled on the client side
        return json.dumps(
            {"apiKey": self.config.api_key, "authDomain": self.config.auth_domain, "projectId": self.config.project_id}
        )

    async def process_callback(self, code: str, state: str | None = None) -> User:
        """Process a Firebase ID token."""
        # Placeholder - would verify Firebase ID token and get user info
        return User(id="firebase_user_id", name="Firebase User", provider="firebase")

    async def validate_token(self, token: str) -> bool:
        """Validate a Firebase ID token."""
        # Placeholder - would validate token with Firebase Admin SDK
        return False
