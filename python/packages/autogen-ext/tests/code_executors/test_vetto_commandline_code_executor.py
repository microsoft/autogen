from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors import create_default_code_executor
from autogen_ext.code_executors.vetto import (
    VettoCommandLineCodeExecutor,
    VettoCommandLineCodeExecutorConfig,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Provide a clean temporary workspace path."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_vetto_executor_initialization_defaults(temp_workspace: Path) -> None:
    """Verify default parameters and properties of VettoCommandLineCodeExecutor."""
    executor = VettoCommandLineCodeExecutor(work_dir=temp_workspace)
    assert executor.timeout == 60
    assert executor.net == "off"
    assert executor.work_dir.resolve() == temp_workspace.resolve()
    assert executor.functions == []


def test_vetto_executor_build_command_flags(temp_workspace: Path) -> None:
    """Verify command assembly with sandbox confinement flags."""
    executor = VettoCommandLineCodeExecutor(
        work_dir=temp_workspace,
        net="allowlist",
        allowed_domains=["api.anthropic.com", "pypi.org"],
        allow_write=["/tmp/cache"],
        allow_read=["/etc/ssl/certs"],
        memory_limit="512MB",
        timeout=30,
        vetto_binary="/opt/vetto/bin/vetto",
    )

    with patch.object(executor, "_resolve_vetto_binary", return_value="/opt/vetto/bin/vetto"):
        cmd = executor._build_command(["python3", "script.py"], cwd=temp_workspace, timeout=30)
        assert cmd[0] == "/opt/vetto/bin/vetto"
        assert cmd[1] == "run"
        assert "--net=allowlist" in cmd
        assert "--timeout" in cmd
        assert "30" in cmd
        assert "--memory" in cmd
        assert "512MB" in cmd
        assert "--allow-domain" in cmd
        assert "api.anthropic.com" in cmd
        assert "pypi.org" in cmd
        assert "--allow-write" in cmd
        assert "--allow-read" in cmd
        assert "--" in cmd
        assert cmd[-2:] == ["python3", "script.py"]


def test_vetto_executor_missing_binary_raises(temp_workspace: Path) -> None:
    """Verify fail-closed error when vetto binary is missing and fallback is disabled."""
    executor = VettoCommandLineCodeExecutor(work_dir=temp_workspace, allow_fallback=False)
    with patch.object(executor, "_resolve_vetto_binary", return_value=None):
        with pytest.raises(RuntimeError) as exc_info:
            executor._build_command(["echo", "hello"])
        assert "Vetto binary not found" in str(exc_info.value)


def test_vetto_executor_missing_binary_allows_fallback(temp_workspace: Path) -> None:
    """Verify unwrapped command returned when vetto binary is missing and fallback is enabled."""
    executor = VettoCommandLineCodeExecutor(work_dir=temp_workspace, allow_fallback=True)
    with patch.object(executor, "_resolve_vetto_binary", return_value=None):
        cmd = executor._build_command(["echo", "hello"])
        assert cmd == ["echo", "hello"]


@pytest.mark.asyncio
async def test_vetto_executor_python_execution_mocked(temp_workspace: Path) -> None:
    """Verify mock execution of python code blocks inside Vetto sandbox."""
    executor = VettoCommandLineCodeExecutor(work_dir=temp_workspace, allow_fallback=True)

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"42\n", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        code_block = CodeBlock(language="python", code="print(42)")
        result = await executor.execute_code_blocks(
            code_blocks=[code_block],
            cancellation_token=CancellationToken(),
        )
        assert result.exit_code == 0
        assert "42" in result.output
        assert result.code_file is not None


@pytest.mark.asyncio
async def test_vetto_executor_timeout_handling(temp_workspace: Path) -> None:
    """Verify timeout produces fail-closed exit code 124 and cleans up."""
    executor = VettoCommandLineCodeExecutor(work_dir=temp_workspace, timeout=1, allow_fallback=True)

    mock_proc = AsyncMock()
    mock_proc.communicate.side_effect = asyncio.TimeoutError
    mock_proc.returncode = 124

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(executor, "_kill_process_tree") as mock_kill:
            code_block = CodeBlock(language="python", code="import time; time.sleep(10)")
            result = await executor.execute_code_blocks(
                code_blocks=[code_block],
                cancellation_token=CancellationToken(),
            )
            assert result.exit_code == 124
            assert "Timeout" in result.output
            assert mock_kill.called


@pytest.mark.asyncio
async def test_vetto_executor_cancellation_handling(temp_workspace: Path) -> None:
    """Verify cancellation produces exit code 125."""
    executor = VettoCommandLineCodeExecutor(work_dir=temp_workspace, allow_fallback=True)

    mock_proc = AsyncMock()
    mock_proc.communicate.side_effect = asyncio.CancelledError
    mock_proc.returncode = 125

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(executor, "_kill_process_tree") as mock_kill:
            token = CancellationToken()
            code_block = CodeBlock(language="python", code="print('cancelled')")
            result = await executor.execute_code_blocks(
                code_blocks=[code_block],
                cancellation_token=token,
            )
            assert result.exit_code == 125
            assert "Cancelled" in result.output
            assert mock_kill.called


def test_vetto_executor_config_roundtrip(temp_workspace: Path) -> None:
    """Verify serialization to and from component configuration schema."""
    executor = VettoCommandLineCodeExecutor(
        work_dir=temp_workspace,
        timeout=45,
        net="allowlist",
        allowed_domains=["example.com"],
        allow_write=["/tmp/out"],
        allow_read=["/etc/hosts"],
        memory_limit="1GB",
        vetto_binary="/usr/bin/vetto",
        allow_fallback=True,
    )
    config = executor._to_config()
    assert isinstance(config, VettoCommandLineCodeExecutorConfig)
    assert config.timeout == 45
    assert config.net == "allowlist"
    assert config.allowed_domains == ["example.com"]
    assert config.memory_limit == "1GB"

    recreated = VettoCommandLineCodeExecutor._from_config(config)
    assert recreated.timeout == 45
    assert recreated.net == "allowlist"
    assert recreated.work_dir.resolve() == temp_workspace.resolve()


def test_create_default_code_executor_prefers_vetto(temp_workspace: Path) -> None:
    """Verify create_default_code_executor prioritizes Vetto over un-sandboxed Local executor."""
    with patch("autogen_ext.code_executors._is_docker_available", return_value=False):
        with patch("autogen_ext.code_executors._is_vetto_available", return_value=True):
            executor = create_default_code_executor(work_dir=str(temp_workspace))
            assert isinstance(executor, VettoCommandLineCodeExecutor)
