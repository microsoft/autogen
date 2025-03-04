from fastapi import Depends, Request, HTTPException
from typing import List

from .manager import AuthManager
from .models import User
from .exceptions import ForbiddenException


def get_auth_manager(request: Request) -> AuthManager:
    """Get the auth manager from app state."""
    if not hasattr(request.app.state, "auth_manager"):
        raise HTTPException(
            status_code=500, 
            detail="Authentication system not initialized"
        )
    return request.app.state.auth_manager


def get_current_user(request: Request) -> User:
    """Get the current authenticated user."""
    if hasattr(request.state, "user"):
        return request.state.user
    
    # Fall back to anonymous user if middleware didn't set user
    # This should generally not happen
    return User(id="anonymous", name="Anonymous User")


def require_authenticated(
    user: User = Depends(get_current_user)
) -> User:
    """Require that the user is authenticated (not anonymous)."""
    if user.id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
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
            raise ForbiddenException(
                f"This endpoint requires one of these roles: {', '.join(required_roles)}"
            )
        return user
    
    return _require_roles


def require_admin(user: User = Depends(require_roles(["admin"]))) -> User:
    """Convenience dependency to require admin role."""
    return user