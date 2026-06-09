"""Code executor utilities for AutoGen-Ext."""

import warnings
from typing import Optional

from autogen_core.code_executor import CodeExecutor

# Docker imports for default code executor
try:
    import docker as docker_client
    from docker.errors import DockerException

    from .docker import DockerCommandLineCodeExecutor

    _docker_available = True
except ImportError:
    docker_client = None  # type: ignore
    DockerException = Exception  # type: ignore
    DockerCommandLineCodeExecutor = None  # type: ignore
    _docker_available = False

from .local import LocalCommandLineCodeExecutor


def _is_docker_available() -> bool:
    """Check if Docker is available and running."""
    if not _docker_available:
        return False

    try:
        if docker_client is not None:
            client = docker_client.from_env()
            client.ping()  # type: ignore
            return True
    except DockerException:
        return False

    return False


def create_default_code_executor(work_dir: Optional[str] = None) -> CodeExecutor:
    """Create a default code executor, preferring Docker if available.

    This function creates a code executor using the following priority:
    1. DockerCommandLineCodeExecutor if Docker is available
    2. LocalCommandLineCodeExecutor with a warning if Docker is not available

    Args:
        work_dir: Optional working directory for the code executor

    Returns:
        CodeExecutor: A code executor instance

    .. warning::
        For security, it is recommended to use DockerCommandLineCodeExecutor
        when available to isolate code execution.
    """
    if _is_docker_available() and DockerCommandLineCodeExecutor is not None:
        try:
            if work_dir:
                return DockerCommandLineCodeExecutor(work_dir=work_dir)
            else:
                return DockerCommandLineCodeExecutor()
        except Exception:
            # Fallback to local if Docker fails to initialize
            pass

    # Issue warning and use local executor if Docker is not available
    warnings.warn(
        "Docker is not available or not running. Using LocalCommandLineCodeExecutor instead of the recommended DockerCommandLineCodeExecutor. "
        "For security, it is recommended to install Docker and ensure it's running before using code executors. "
        "To install Docker, visit: https://docs.docker.com/get-docker/",
        UserWarning,
        stacklevel=2,
    )

    if work_dir:
        return LocalCommandLineCodeExecutor(work_dir=work_dir)
    else:
        return LocalCommandLineCodeExecutor()


__all__ = ["create_default_code_executor"]
