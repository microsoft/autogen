# api/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status
import logging
from contextlib import contextmanager

from ..database.dbmanager import DBManager
from .managers.connection import ConnectionManager
from ..teammanager import TeamManager
from .config import settings

logger = logging.getLogger(__name__)

# Global manager instances
_db_manager: Optional[DBManager] = None
_connection_manager: Optional[ConnectionManager] = None
_team_manager: Optional[TeamManager] = None

# Context manager for database sessions


@contextmanager
def get_db_context():
    """Provide a transactional scope around a series of operations."""
    if not _db_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database manager not initialized"
        )
    try:
        yield _db_manager
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )

# Dependency providers


async def get_db() -> DBManager:
    """Dependency provider for database manager"""
    if not _db_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database manager not initialized"
        )
    return _db_manager


async def get_connection_manager() -> ConnectionManager:
    """Dependency provider for connection manager"""
    if not _connection_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection manager not initialized"
        )
    return _connection_manager


async def get_team_manager() -> TeamManager:
    """Dependency provider for team manager"""
    if not _team_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Team manager not initialized"
        )
    return _team_manager

# Authentication dependency


async def get_current_user(
    # Add your authentication logic here
    # For example: token: str = Depends(oauth2_scheme)
) -> str:
    """
    Dependency for getting the current authenticated user.
    Replace with your actual authentication logic.
    """
    # Implement your user authentication here
    return "user_id"  # Replace with actual user identification

# Manager initialization and cleanup


def init_managers(database_uri: str) -> None:
    """Initialize all manager instances"""
    global _db_manager, _connection_manager, _team_manager

    logger.info("Initializing managers...")

    try:
        # Initialize database manager
        _db_manager = DBManager(engine_uri=database_uri)
        _db_manager.create_db_and_tables()
        logger.info("Database manager initialized")

        # Initialize connection manager
        _connection_manager = ConnectionManager(
            db_manager=_db_manager,
            cleanup_interval=settings.CLEANUP_INTERVAL
        )
        logger.info("Connection manager initialized")

        # Initialize team manager
        _team_manager = TeamManager()
        logger.info("Team manager initialized")

    except Exception as e:
        logger.error(f"Failed to initialize managers: {str(e)}")
        cleanup_managers()  # Cleanup any partially initialized managers
        raise


async def cleanup_managers() -> None:
    """Cleanup and shutdown all manager instances"""
    global _db_manager, _connection_manager, _team_manager

    logger.info("Cleaning up managers...")

    # Cleanup connection manager
    if _connection_manager:
        try:
            # Cancel any ongoing cleanup tasks
            _connection_manager.cleanup_task.cancel()
            await _connection_manager.cleanup_task
        except Exception as e:
            logger.error(f"Error cleaning up connection manager: {str(e)}")
        finally:
            _connection_manager = None

    # Cleanup team manager
    if _team_manager:
        try:
            await _team_manager.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up team manager: {str(e)}")
        finally:
            _team_manager = None

    # Cleanup database manager
    if _db_manager:
        try:
            await _db_manager.close()
        except Exception as e:
            logger.error(f"Error cleaning up database manager: {str(e)}")
        finally:
            _db_manager = None

# Utility functions for dependency management


def get_manager_status() -> dict:
    """Get the initialization status of all managers"""
    return {
        "database_manager": _db_manager is not None,
        "connection_manager": _connection_manager is not None,
        "team_manager": _team_manager is not None
    }

# Combined dependencies


async def get_managers():
    """Get all managers in one dependency"""
    return {
        "db": await get_db(),
        "connection": await get_connection_manager(),
        "team": await get_team_manager()
    }

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
        missing = [name for name in manager_names if not status.get(
            f"{name}_manager")]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Required managers not available: {', '.join(missing)}"
            )
        return True
    return Depends(dependency)
