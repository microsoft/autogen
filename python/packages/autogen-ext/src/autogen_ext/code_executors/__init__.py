"""Code executor utilities for AutoGen-Ext."""

import os
import shutil
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
from .vetto import VettoCommandLineCodeExecutor


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


def _is_vetto_available() -> bool:
    """Check if the Vetto sandbox executable is installed and available in PATH."""
    env_path = os.getenv("VETTO_PATH")
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return True
    if shutil.which("vetto"):
        return True
    candidates = [
        os.path.expanduser("~/.cargo/bin/vetto"),
        "/usr/local/bin/vetto",
        "/usr/bin/vetto",
    ]
    return any(os.path.isfile(p) and os.access(p, os.X_OK) for p in candidates)


def create_default_code_executor(work_dir: Optional[str] = None) -> CodeExecutor:
    """Create a default code executor, preferring Docker or Vetto if available.

    This function creates a code executor using the following priority:
    1. DockerCommandLineCodeExecutor if Docker is available
    2. VettoCommandLineCodeExecutor if Vetto sandbox runtime is available
    3. LocalCommandLineCodeExecutor with a warning if no sandbox runtime is available

    Args:
        work_dir: Optional working directory for the code executor

    Returns:
        CodeExecutor: A code executor instance

    .. warning::
        For security, it is recommended to use DockerCommandLineCodeExecutor or
        VettoCommandLineCodeExecutor to isolate code execution.
    """
    if _is_docker_available() and DockerCommandLineCodeExecutor is not None:
        try:
            if work_dir:
                return DockerCommandLineCodeExecutor(work_dir=work_dir)
            else:
                return DockerCommandLineCodeExecutor()
        except Exception:
            pass

    if _is_vetto_available():
        try:
            if work_dir:
                return VettoCommandLineCodeExecutor(work_dir=work_dir)
            else:
                return VettoCommandLineCodeExecutor()
        except Exception:
            pass

    # Issue warning and use local executor if no isolated runtime is available
    warnings.warn(
        "Neither Docker nor Vetto is available. Using LocalCommandLineCodeExecutor instead of an isolated runtime. "
        "For security, it is recommended to install Vetto ('cargo install vetto' or 'npm install -g @shledery/vetto') "
        "or Docker before running code executors.",
        UserWarning,
        stacklevel=2,
    )

    if work_dir:
        return LocalCommandLineCodeExecutor(work_dir=work_dir)
    else:
        return LocalCommandLineCodeExecutor()


__all__ = [
    "create_default_code_executor",
    "LocalCommandLineCodeExecutor",
    "VettoCommandLineCodeExecutor",
]
