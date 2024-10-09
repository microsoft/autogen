# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_commandline_code_executor.py
# Credit to original authors

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, TypeAlias

import pytest
import pytest_asyncio
from aiofiles import open
from autogen_core.base import CancellationToken
from autogen_core.components.code_executor import CodeBlock, DockerCommandLineCodeExecutor, LocalCommandLineCodeExecutor


def docker_tests_enabled() -> bool:
    if os.environ.get("SKIP_DOCKER", "unset").lower() == "true":
        return False

    try:
        import docker
        from docker.errors import DockerException
    except ImportError:
        return False

    try:
        client = docker.from_env()
        client.ping()  # type: ignore
        return True
    except DockerException:
        return False


@pytest_asyncio.fixture(scope="function")  # type: ignore
async def executor_and_temp_dir(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[tuple[LocalCommandLineCodeExecutor | DockerCommandLineCodeExecutor, str], None]:
    if request.param == "local":
        with tempfile.TemporaryDirectory() as temp_dir:
            yield LocalCommandLineCodeExecutor(work_dir=temp_dir), temp_dir
    elif request.param == "docker":
        if not docker_tests_enabled():
            pytest.skip("Docker tests are disabled")

        with tempfile.TemporaryDirectory() as temp_dir:
            async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
                yield executor, temp_dir


ExecutorFixture: TypeAlias = tuple[LocalCommandLineCodeExecutor | DockerCommandLineCodeExecutor, str]


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["local", "docker"], indirect=True)
async def test_execute_code(executor_and_temp_dir: ExecutorFixture) -> None:
    executor, _temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()

    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Test bash script.
    if sys.platform not in ["win32"]:
        code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
        code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test running code.
    file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Check saved code file.
    async with open(code_result.code_file) as f:
        code_lines = await f.readlines()
        for file_line, code_line in zip(file_lines, code_lines, strict=False):
            assert file_line.strip() == code_line.strip()


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["local", "docker"], indirect=True)
async def test_commandline_code_executor_timeout(executor_and_temp_dir: ExecutorFixture) -> None:
    executor, temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    executor = LocalCommandLineCodeExecutor(timeout=1, work_dir=temp_dir)
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code and "Timeout" in code_result.output


# TODO: add docker when cancellation is supported
@pytest.mark.asyncio
async def test_commandline_code_executor_cancellation() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

        coro = executor.execute_code_blocks(code_blocks, cancellation_token)

        await asyncio.sleep(1)
        cancellation_token.cancel()
        code_result = await coro

        assert code_result.exit_code and "Cancelled" in code_result.output


@pytest.mark.asyncio
async def test_local_commandline_code_executor_restart() -> None:
    executor = LocalCommandLineCodeExecutor()
    with pytest.warns(UserWarning, match=r".*No action is taken."):
        await executor.restart()


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["local", "docker"], indirect=True)
async def test_invalid_relative_path(executor_and_temp_dir: ExecutorFixture) -> None:
    executor, _temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    code = """# filename: /tmp/test.py

print("hello world")
"""
    result = await executor.execute_code_blocks(
        [CodeBlock(code=code, language="python")], cancellation_token=cancellation_token
    )
    assert result.exit_code == 1 and "Filename is not in the workspace" in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["local", "docker"], indirect=True)
async def test_valid_relative_path(executor_and_temp_dir: ExecutorFixture) -> None:
    executor, temp_dir_str = executor_and_temp_dir

    cancellation_token = CancellationToken()
    temp_dir = Path(temp_dir_str)

    code = """# filename: test.py

print("hello world")
"""
    result = await executor.execute_code_blocks(
        [CodeBlock(code=code, language="python")], cancellation_token=cancellation_token
    )
    assert result.exit_code == 0
    assert "hello world" in result.output
    assert result.code_file is not None
    assert "test.py" in result.code_file
    assert (temp_dir / Path("test.py")).resolve() == Path(result.code_file).resolve()
    assert (temp_dir / Path("test.py")).exists()


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_start_stop() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        executor = DockerCommandLineCodeExecutor(work_dir=temp_dir)
        await executor.start()
        await executor.stop()


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_start_stop_context_manager() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as _exec:
            pass
