# mypy: disable-error-code="no-any-unimported"
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, TypeAlias

import pytest
import pytest_asyncio
from aiofiles import open
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor


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
) -> AsyncGenerator[tuple[DockerCommandLineCodeExecutor, str], None]:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            yield executor, temp_dir


ExecutorFixture: TypeAlias = tuple[DockerCommandLineCodeExecutor, str]


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
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
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_commandline_code_executor_timeout(executor_and_temp_dir: ExecutorFixture) -> None:
    _executor, temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

    async with DockerCommandLineCodeExecutor(timeout=1, work_dir=temp_dir) as executor:
        code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)

    assert code_result.exit_code and "Timeout" in code_result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
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
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
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


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_extra_args() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a file in temp_dir to mount
        host_file_path = Path(temp_dir) / "host_file.txt"
        host_file_path.write_text("This is a test file.")

        container_file_path = "/container/host_file.txt"

        extra_volumes = {str(host_file_path): {"bind": container_file_path, "mode": "rw"}}
        init_command = "echo 'Initialization command executed' > /workspace/init_command.txt"
        extra_hosts = {"example.com": "127.0.0.1"}

        async with DockerCommandLineCodeExecutor(
            work_dir=temp_dir,
            extra_volumes=extra_volumes,
            init_command=init_command,
            extra_hosts=extra_hosts,
        ) as executor:
            cancellation_token = CancellationToken()

            # Verify init_command was executed
            init_command_file_path = Path(temp_dir) / "init_command.txt"
            assert init_command_file_path.exists()

            # Verify extra_hosts
            ns_lookup_code_blocks = [
                CodeBlock(code="import socket; print(socket.gethostbyname('example.com'))", language="python")
            ]
            ns_lookup_result = await executor.execute_code_blocks(ns_lookup_code_blocks, cancellation_token)
            assert ns_lookup_result.exit_code == 0
            assert "127.0.0.1" in ns_lookup_result.output

            # Verify the file is accessible in the volume mounted in extra_volumes
            code_blocks = [
                CodeBlock(code=f"with open('{container_file_path}') as f: print(f.read())", language="python")
            ]
            code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert code_result.exit_code == 0
            assert "This is a test file." in code_result.output


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_serialization() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = DockerCommandLineCodeExecutor(work_dir=temp_dir)
        loaded_executor = DockerCommandLineCodeExecutor.load_component(executor.dump_component())
        assert executor.bind_dir == loaded_executor.bind_dir
        assert executor.timeout == loaded_executor.timeout
