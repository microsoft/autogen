# api/deps.py
import logging
import os
from contextlib import contextmanager
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket
from fastapi import Depends, HTTPException, status

from ..database import DatabaseManager
from ..teammanager import TeamManager
from .config import settings
from .managers.connection import WebSocketManager
from .auth import AuthManager, AuthMiddleware, AuthConfig

logger = logging.getLogger(__name__)

# Global manager instances
_db_manager: Optional[DatabaseManager] = None
_websocket_manager: Optional[WebSocketManager] = None
_team_manager: Optional[TeamManager] = None
_auth_manager: Optional[AuthManager] = None 
# Context manager for database sessions


@contextmanager
def get_db_context():
    """Provide a transactional scope around a series of operations."""
    if not _db_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database manager not initialized"
        )
    try:
        yield _db_manager
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed"
        ) from e


# Dependency providers
async def get_auth_manager(request: Request) -> AuthManager:
    """Dependency provider for auth manager"""
    if hasattr(request.app.state, "auth_manager"):
        return request.app.state.auth_manager
    if not _auth_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Auth manager not initialized"
        )
    return _auth_manager

def get_ws_auth_manager(websocket: WebSocket) -> AuthManager:
    """Get the auth manager from app state for WebSocket connections."""
    if not hasattr(websocket.app.state, "auth_manager"):
        # Can't raise HTTPException in WebSockets, so we'll have to handle this differently
        logger.error("Authentication system not initialized")
        return None
    return websocket.app.state.auth_manager

async def get_db() -> DatabaseManager:
    """Dependency provider for database manager"""
    if not _db_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database manager not initialized"
        )
    return _db_manager


async def get_websocket_manager() -> WebSocketManager:
    """Dependency provider for connection manager"""
    if not _websocket_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Connection manager not initialized"
        )
    return _websocket_manager


async def get_team_manager() -> TeamManager:
    """Dependency provider for team manager"""
    if not _team_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Team manager not initialized")
    return _team_manager


# Authentication dependency


async def get_current_user(request: Request) -> str:
    """Get the current authenticated user."""
    if hasattr(request.state, "user"):
        return request.state.user.id
    
    # Fallback for routes not protected by auth middleware
    auth_manager = await get_auth_manager(request)
    if auth_manager.config.type == "none":
        return settings.DEFAULT_USER_ID
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )

async def register_auth_dependencies(app: FastAPI, config_dir: Path):
    """Initialize and register authentication system."""
    global _auth_manager
    
    # Check for auth configuration file
    auth_config_path = os.environ.get("AUTOGENSTUDIO_AUTH_CONFIG")
    
    if auth_config_path and os.path.exists(auth_config_path):
        # Load auth config from YAML file
        try:
            _auth_manager = AuthManager.from_yaml(auth_config_path)
            app.state.auth_manager = _auth_manager
            app.add_middleware(AuthMiddleware, auth_manager=_auth_manager)
            logger.info(f"Authentication initialized with provider: {_auth_manager.config.type}")
        except Exception as e:
            logger.error(f"Failed to initialize authentication from config file: {str(e)}")
            logger.warning("Falling back to no authentication")
            config = AuthConfig(type="none")
            _auth_manager = AuthManager(config)
            app.state.auth_manager = _auth_manager
    else:
        # No auth config provided
        config = AuthConfig(type="none")
        _auth_manager = AuthManager(config)
        app.state.auth_manager = _auth_manager
        logger.info("Authentication disabled (no config provided)")

# Manager initialization and cleanup


async def init_managers(database_uri: str, config_dir: str, app_root: str) -> None:
    """Initialize all manager instances"""
    global _db_manager, _websocket_manager, _team_manager

    logger.info("Initializing managers...")

    try:
        # Initialize database manager
        _db_manager = DatabaseManager(engine_uri=database_uri, base_dir=app_root)
        _db_manager.initialize_database(auto_upgrade=settings.UPGRADE_DATABASE)

        # init default team config
        await _db_manager.import_teams_from_directory(config_dir, settings.DEFAULT_USER_ID, check_exists=True)

        # Initialize connection manager
        _websocket_manager = WebSocketManager(db_manager=_db_manager)
        logger.info("Connection manager initialized")

        # Initialize team manager
        _team_manager = TeamManager()
        logger.info("Team manager initialized")

    except Exception as e:
        logger.error(f"Failed to initialize managers: {str(e)}")
        await cleanup_managers()  # Cleanup any partially initialized managers
        raise


async def cleanup_managers() -> None:
    """Cleanup and shutdown all manager instances"""
    global _db_manager, _websocket_manager, _team_manager, _auth_manager

    logger.info("Cleaning up managers...")

    # Cleanup connection manager first to ensure all active connections are closed
    if _websocket_manager:
        try:
            await _websocket_manager.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up connection manager: {str(e)}")
        finally:
            _websocket_manager = None

    # TeamManager doesn't need explicit cleanup since WebSocketManager handles it
    _team_manager = None

    _auth_manager = None  

    # Cleanup database manager last
    if _db_manager:
        try:
            await _db_manager.close()
        except Exception as e:
            logger.error(f"Error cleaning up database manager: {str(e)}")
        finally:
            _db_manager = None

    logger.info("All managers cleaned up")


# Utility functions for dependency management


def get_manager_status() -> dict:
    """Get the initialization status of all managers"""
    return {
        "database_manager": _db_manager is not None,
        "websocket_manager": _websocket_manager is not None,
        "team_manager": _team_manager is not None,
        "auth_manager": _auth_manager is not None,
    }


# Combined dependencies


async def get_managers():
    """Get all managers in one dependency"""
    return {"db": await get_db(), "connection": await get_websocket_manager(), "team": await get_team_manager()}


# Error handling for manager operations


class ManagerOperationError(Exception):
    """Custom exception for manager operation errors"""

    def __init__(self, manager_name: str, operation: str, detail: str):
        self.manager_name = manager_name
        self.operation = operation
        self.detail = detail
        super().__init__(f"{manager_name} failed during {operation}: {detail}")


# Dependency for requiring specific managers


def require_managers(*manager_names: str):
    """Decorator to require specific managers for a route"""

    async def dependency():
        status = get_manager_status()
        missing = [name for name in manager_names if not status.get(f"{name}_manager")]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Required managers not available: {', '.join(missing)}",
            )
        return True

    return Depends(dependency)
