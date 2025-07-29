"""Docker image constants for MagenticOne agents."""

import os

# Docker registry and image constants
DOCKER_REGISTRY = "mcr.microsoft.com/autogen"
PYTHON_IMAGE_ENV_VAR = "AUTOGEN_PYTHON_IMAGE"

# Default Python image for code execution
PYTHON_IMAGE = os.getenv(
    PYTHON_IMAGE_ENV_VAR, f"{DOCKER_REGISTRY}/python:latest"
)
