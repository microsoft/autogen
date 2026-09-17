# Copyright (c) Microsoft. All rights reserved.
# Security regression tests for issue #7917 (OWASP ASI10 - Docker trust boundary).

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import NotFound

from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor


def _mock_docker_client():
    """Return a MagicMock that simulates a Docker daemon with no existing containers."""
    mock_container = MagicMock()
    mock_container.status = "running"

    class MockClient:
        def __init__(self):
            self.images = MagicMock()
            self.containers = MagicMock()
            self.containers.get.side_effect = NotFound("Container not found")
            self.containers.create.return_value = mock_container

        def __getattr__(self, name):
            return MagicMock()

    return MockClient()


@patch("docker.from_env", return_value=_mock_docker_client())
def test_sensitive_host_path_is_rejected(mock_docker):
    """Mounting /etc/passwd must be rejected as a trust boundary violation."""
    executor = DockerCommandLineCodeExecutor(
        image="python:3-slim",
        extra_volumes={"/etc/passwd": {"bind": "/mnt/passwd", "mode": "ro"}},
    )

    with pytest.raises(ValueError, match="Refusing to mount sensitive host path"):
        asyncio.run(executor.start())


@patch("docker.from_env", return_value=_mock_docker_client())
def test_docker_socket_is_rejected(mock_docker):
    """Mounting the Docker socket must be rejected (container escape vector)."""
    executor = DockerCommandLineCodeExecutor(
        image="python:3-slim",
        extra_volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
    )

    with pytest.raises(ValueError, match="Refusing to mount sensitive host path"):
        asyncio.run(executor.start())


@patch("docker.from_env", return_value=_mock_docker_client())
def test_path_traversal_is_rejected(mock_docker):
    """Relative paths with '..' components that escape the workspace must be rejected."""
    executor = DockerCommandLineCodeExecutor(
        image="python:3-slim",
        extra_volumes={"../../etc/passwd": {"bind": "/mnt/passwd", "mode": "ro"}},
    )

    with pytest.raises(ValueError):
        asyncio.run(executor.start())


@patch("docker.from_env", return_value=_mock_docker_client())
def test_relative_path_outside_workspace_is_rejected(mock_docker):
    """A relative path that escapes the workspace must be rejected."""
    executor = DockerCommandLineCodeExecutor(
        image="python:3-slim",
        extra_volumes={"./local_data": {"bind": "/data", "mode": "ro"}},
    )

    with pytest.raises(ValueError):
        asyncio.run(executor.start())


@patch("docker.from_env", return_value=_mock_docker_client())
def test_workspace_path_is_allowed(mock_docker):
    """Absolute paths inside the executor workspace must be allowed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sub_dir = Path(tmp_dir) / "local_data"
        sub_dir.mkdir()

        executor = DockerCommandLineCodeExecutor(
            image="python:3-slim",
            work_dir=tmp_dir,
            extra_volumes={str(sub_dir): {"bind": "/data", "mode": "ro"}},
        )

        # Should not raise a security ValueError (other ValueErrors are unrelated).
        try:
            asyncio.run(executor.start())
        except ValueError as exc:
            assert "Refusing to mount sensitive host path" not in str(exc)
            assert "Refusing to mount relative" not in str(exc)
        except Exception:
            # RuntimeError from the mocked docker client is expected and acceptable here.
            pass


@patch("docker.from_env", return_value=_mock_docker_client())
def test_empty_path_is_rejected(mock_docker):
    """Empty strings as host source paths must be rejected (would map to CWD by default)."""
    executor = DockerCommandLineCodeExecutor(
        image="python:3-slim",
        extra_volumes={"": {"bind": "/data", "mode": "ro"}},
    )

    with pytest.raises(ValueError, match="Empty host source path"):
        asyncio.run(executor.start())


@patch("docker.from_env", return_value=_mock_docker_client())
def test_invalid_mount_spec_is_rejected(mock_docker):
    """A non-dict mount specification must be rejected before any container is created."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sub_dir = Path(tmp_dir) / "data"
        sub_dir.mkdir()

        executor = DockerCommandLineCodeExecutor(
            image="python:3-slim",
            work_dir=tmp_dir,
            extra_volumes={str(sub_dir): "not-a-dict"},  # type: ignore[dict-item]
        )

        with pytest.raises(ValueError, match="Invalid bind specification"):
            asyncio.run(executor.start())
