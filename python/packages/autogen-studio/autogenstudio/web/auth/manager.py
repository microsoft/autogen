import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
import yaml
from fastapi import Request
from loguru import logger
from typing_extensions import Self

from .exceptions import ConfigurationException, InvalidTokenException, MissingTokenException
from .models import AuthConfig, User
from .providers import AuthProvider, FirebaseAuthProvider, GithubAuthProvider, MSALAuthProvider, NoAuthProvider

# Allowed JWT algorithms — explicitly pin to HS256 only to prevent algorithm confusion
# and reject the 'none' algorithm attack vector.
_ALLOWED_JWT_ALGORITHMS = ["HS256"]

# Minimum acceptable JWT secret length to resist brute-force attacks.
_MIN_JWT_SECRET_LENGTH = 32


class AuthManager:
    """
    Manages authentication for the application.
    Handles token creation, validation, and provider selection.
    """

    def __init__(self, config: AuthConfig):
        """Initialize the auth manager with configuration."""
        self.config = config
        self.provider = self._create_provider()
        if config.jwt_secret and len(config.jwt_secret) < _MIN_JWT_SECRET_LENGTH:
            logger.warning(
                "JWT secret is shorter than the recommended minimum of "
                f"{_MIN_JWT_SECRET_LENGTH} characters; consider using a longer secret."
            )
        logger.info(f"Initialized auth manager with provider: {config.type}")

    def _create_provider(self) -> AuthProvider:
        """Create the appropriate auth provider based on config."""
        try:
            if self.config.type == "github":
                return GithubAuthProvider(self.config)
            elif self.config.type == "msal":
                return MSALAuthProvider(self.config)
            elif self.config.type == "firebase":
                return FirebaseAuthProvider(self.config)
            else:
                return NoAuthProvider()
        except Exception as e:
            logger.error(f"Failed to create auth provider: {str(e)}")
            # Fall back to no auth if provider creation fails
            return NoAuthProvider()

    def create_token(self, user: User) -> str:
        """Create a JWT token for authenticated user."""
        if not self.config.jwt_secret:
            logger.warning("JWT secret not configured, using insecure token")
            return "dummy_token_" + user.id

        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=self.config.token_expiry_minutes)
        payload = {
            "sub": user.id,
            "name": user.name,
            "email": user.email,
            "provider": user.provider,
            "roles": user.roles,
            "iat": now,
            "exp": expiry,
        }
        return jwt.encode(payload, self.config.jwt_secret, algorithm="HS256")

    def _decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token with strict options.

        Raises InvalidTokenException on any validation failure.
        """
        if not self.config.jwt_secret:
            raise InvalidTokenException()

        decode_options: Dict[str, Any] = {
            "verify_signature": True,
            "require": ["sub", "exp", "iat"],
            "verify_exp": True,
            "verify_iat": True,
        }

        return jwt.decode(
            token,
            self.config.jwt_secret,
            algorithms=_ALLOWED_JWT_ALGORITHMS,
            options=decode_options,
        )

    async def authenticate_request(self, request: Request) -> User:
        """Authenticate a request and return user information."""
        # Check if path should be excluded from auth
        # print("************ authenticating request ************", request.url.path, self.config.type )
        if request.url.path in self.config.exclude_paths:
            return User(id="guestuser@gmail.com", name="Default User", provider="none")

        if self.config.type == "none":
            # No auth mode - return default user
            return User(id="guestuser@gmail.com", name="Default User", provider="none")

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise MissingTokenException()

        token = auth_header.replace("Bearer ", "")

        try:
            if not self.config.jwt_secret:
                # JWT secret is mandatory for authenticated providers; refuse the request.
                logger.error("JWT secret not configured but authentication is required")
                raise InvalidTokenException()

            # Decode and validate JWT with strict algorithm pinning and claim checks.
            payload = self._decode_token(token)

            # Create User object from token payload
            return User(
                id=payload.get("sub"),
                name=payload.get("name", "Unknown User"),
                email=payload.get("email"),
                provider=payload.get("provider", "jwt"),
                roles=payload.get("roles", ["user"]),
            )

        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Expired token received: {token[:10]}...")
            raise InvalidTokenException() from e
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token received: {token[:10]}...")
            raise InvalidTokenException() from e

    def is_valid_token(self, token: str) -> bool:
        """Check if a JWT token is valid."""
        if not self.config.jwt_secret:
            return False  # Refuse validation when no secret is configured

        try:
            self._decode_token(token)
            return True
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, InvalidTokenException):
            logger.warning("Token validation failed")
            return False

    @classmethod
    def from_yaml(cls, yaml_path: str) -> Self:
        """Create AuthManager from YAML config file."""
        try:
            with open(yaml_path, "r") as f:
                config_data = yaml.safe_load(f)
            config = AuthConfig(**config_data)
            return cls(config)
        except Exception as e:
            logger.error(f"Failed to load auth config from {yaml_path}: {str(e)}")
            raise ConfigurationException(f"Failed to load auth config: {str(e)}") from e

    @classmethod
    def from_env(cls) -> Self:
        """Create AuthManager from environment variables."""
        auth_type = os.environ.get("AUTOGENSTUDIO_AUTH_TYPE", "none")

        config_dict: Dict[str, Any] = {
            "type": auth_type,
            "jwt_secret": os.environ.get("AUTOGENSTUDIO_JWT_SECRET"),
            "token_expiry_minutes": int(os.environ.get("AUTOGENSTUDIO_TOKEN_EXPIRY", "60")),
        }

        # Add provider-specific config based on the auth type
        if auth_type == "github":
            config_dict["github"] = {
                "client_id": os.environ.get("AUTOGENSTUDIO_GITHUB_CLIENT_ID", ""),
                "client_secret": os.environ.get("AUTOGENSTUDIO_GITHUB_CLIENT_SECRET", ""),
                "callback_url": os.environ.get("AUTOGENSTUDIO_GITHUB_CALLBACK_URL", ""),
                "scopes": os.environ.get("AUTOGENSTUDIO_GITHUB_SCOPES", "user:email").split(","),
            }
        # Add other provider config parsing here

        config = AuthConfig(**config_dict)
        return cls(config)
