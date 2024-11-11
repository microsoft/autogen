# api/app.py
import os
# import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from loguru import logger

from .routes import sessions, runs, teams, agents, models, tools, ws
from .deps import init_managers, cleanup_managers
from .config import settings
from .initialization import AppInitializer
from ..version import VERSION

# Configure logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


# Initialize application
app_file_path = os.path.dirname(os.path.abspath(__file__))
initializer = AppInitializer(settings, app_file_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle manager for the FastAPI application.
    Handles initialization and cleanup of application resources.
    """
    # Startup
    logger.info("Initializing application...")
    try:
        # Initialize managers (DB, Connection, Team)
        await init_managers(initializer.database_uri, initializer.config_dir)
        logger.info("Managers initialized successfully")

        # Any other initialization code
        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

    yield  # Application runs here

    # Shutdown
    try:
        logger.info("Cleaning up application resources...")
        await cleanup_managers()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Create FastAPI application
app = FastAPI(lifespan=lifespan, debug=True)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://localhost:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with version and documentation
api = FastAPI(
    root_path="/api",
    title="AutoGen Studio API",
    version=VERSION,
    description="AutoGen Studio is a low-code tool for building and testing multi-agent workflows.",
    docs_url="/docs" if settings.API_DOCS else None,
)

# Include all routers with their prefixes
api.include_router(
    sessions.router,
    prefix="/sessions",
    tags=["sessions"],
    responses={404: {"description": "Not found"}},
)

api.include_router(
    runs.router,
    prefix="/runs",
    tags=["runs"],
    responses={404: {"description": "Not found"}},
)

api.include_router(
    teams.router,
    prefix="/teams",
    tags=["teams"],
    responses={404: {"description": "Not found"}},
)

api.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)

api.include_router(
    models.router,
    prefix="/models",
    tags=["models"],
    responses={404: {"description": "Not found"}},
)

api.include_router(
    tools.router,
    prefix="/tools",
    tags=["tools"],
    responses={404: {"description": "Not found"}},
)

api.include_router(
    ws.router,
    prefix="/ws",
    tags=["websocket"],
    responses={404: {"description": "Not found"}},
)


# Version endpoint


@api.get("/version")
async def get_version():
    """Get API version"""
    return {
        "status": True,
        "message": "Version retrieved successfully",
        "data": {"version": VERSION},
    }

# Health check endpoint


@api.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": True,
        "message": "Service is healthy",
    }

# Mount static file directories
app.mount("/api", api)
app.mount(
    "/files",
    StaticFiles(directory=initializer.static_root, html=True),
    name="files",
)
app.mount("/", StaticFiles(directory=initializer.ui_root, html=True), name="ui")

# Error handlers


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error: {str(exc)}")
    return {
        "status": False,
        "message": "Internal server error",
        "detail": str(exc) if settings.API_DOCS else "Internal server error"
    }


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    Useful for testing and different deployment scenarios.
    """
    return app
