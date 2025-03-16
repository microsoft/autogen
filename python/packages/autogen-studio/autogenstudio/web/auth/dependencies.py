from typing import List

from fastapi import Depends, HTTPException, Request, WebSocket, status

from .exceptions import ForbiddenException
from .manager import AuthManager
from .models import User


async def get_auth_manager(request: Request) -> AuthManager:
    """Dependency provider for auth manager"""
    if hasattr(request.app.state, "auth_manager"):
        return request.app.state.auth_manager
    # We can remove this part since it depends on the global in deps.py
    # It's better to throw the error directly
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth manager not initialized")


def get_ws_auth_manager(websocket: WebSocket) -> AuthManager:
    """Get the auth manager from app state for WebSocket connections."""
    if hasattr(websocket.app.state, "auth_manager"):
        return websocket.app.state.auth_manager
    # Similar to above, remove the global reference
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication system not initialized"
    )


def get_current_user(request: Request) -> User:
    """Get the current authenticated user."""
    if hasattr(request.state, "user"):
        return request.state.user

    # Fall back to anonymous user if middleware didn't set user
    # This should generally not happen
    return User(id="anonymous", name="Anonymous User")


def require_authenticated(user: User = Depends(get_current_user)) -> User:
    """Require that the user is authenticated (not anonymous)."""
    if user.id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_roles(required_roles: List[str]):
    """
    Dependency factory to require specific roles.
    Example:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_roles(["admin"]))):
            # Only users with admin role will get here
            return {"message": "Welcome, admin!"}
    """

    def _require_roles(user: User = Depends(require_authenticated)) -> User:
        """Require that the user has at least one of the specified roles."""
        user_roles = set(user.roles or [])
        if not any(role in user_roles for role in required_roles):
            raise ForbiddenException(f"This endpoint requires one of these roles: {', '.join(required_roles)}")
        return user

    return _require_roles


def require_admin(user: User = Depends(require_roles(["admin"]))) -> User:
    """Convenience dependency to require admin role."""
    return user
