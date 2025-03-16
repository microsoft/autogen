from fastapi import HTTPException


class AuthException(HTTPException):
    """Base class for authentication exceptions."""

    def __init__(self, detail: str, headers: dict | None = None):
        super().__init__(status_code=401, detail=detail, headers=headers)


class InvalidTokenException(AuthException):
    """Exception raised when token is invalid."""

    def __init__(self):
        super().__init__(detail="Invalid or expired token")


class MissingTokenException(AuthException):
    """Exception raised when token is missing."""

    def __init__(self):
        super().__init__(detail="Authentication token is missing")


class ProviderAuthException(AuthException):
    """Exception raised when authentication with provider fails."""

    def __init__(self, provider: str, detail: str):
        super().__init__(detail=f"Authentication failed with {provider}: {detail}")


class ConfigurationException(Exception):
    """Exception raised when there's an issue with auth configuration."""

    pass


class ForbiddenException(HTTPException):
    """Exception raised when user doesn't have permission."""

    def __init__(self, detail: str = "You don't have permission to access this resource"):
        super().__init__(status_code=403, detail=detail)
