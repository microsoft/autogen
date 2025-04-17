import inspect
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, TypeAlias

import pytest
import pytest_asyncio
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker_jupyter import (
    DockerJupyterCodeExecutor,
    DockerJupyterServer,
)


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
) -> AsyncGenerator[tuple[DockerJupyterCodeExecutor, str], None]:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerJupyterServer(bind_dir=temp_dir) as jupyter_server:
            async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                yield executor, temp_dir


ExecutorFixture: TypeAlias = tuple[DockerJupyterCodeExecutor, str]


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_execute_code(executor_and_temp_dir: ExecutorFixture) -> None:
    executor, _temp_dir = executor_and_temp_dir
    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
    assert code_result.exit_code == 0 and "hello world!" in code_result.output

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and "200" in code_result.output

    # Test running code.
    file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and "200" in code_result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_jupyter_persist_variable(executor_and_temp_dir: ExecutorFixture) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerJupyterServer(bind_dir=temp_dir) as jupyter_server:
            async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                code_blocks_first = [
                    CodeBlock(code="a = 100 + 100; print(a)", language="python"),
                ]
                code_result_first = await executor.execute_code_blocks(
                    code_blocks_first, cancellation_token=CancellationToken()
                )
                assert code_result_first.exit_code == 0 and "200" in code_result_first.output
                code_blocks_second = [
                    CodeBlock(code="b = a + 100 ; print(b)", language="python"),
                ]
                code_result_second = await executor.execute_code_blocks(
                    code_blocks_second, cancellation_token=CancellationToken()
                )
                assert code_result_second.exit_code == 0 and "300" in code_result_second.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_commandline_code_executor_timeout(executor_and_temp_dir: ExecutorFixture) -> None:
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    async with DockerJupyterServer() as jupyter_server:
        async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server, timeout=1) as executor:
            code_result = await executor.execute_code_blocks(
                code_blocks=code_blocks, cancellation_token=CancellationToken()
            )

    assert code_result.exit_code and "Timeout" in code_result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_commandline_code_executor_cancellation(executor_and_temp_dir: ExecutorFixture) -> None:
    _executor, temp_dir = executor_and_temp_dir
    # Write code that sleep for 10 seconds and then write "hello world!"
    # to a file.
    code = """import time, os
time.sleep(10)
with open("hello.txt", "w") as f:
    f.write("hello world!")
    """
    code_blocks = [CodeBlock(code=code, language="python")]
    code_result = await _executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
    # Check if the file was created
    hello_file_path = Path(temp_dir) / "hello.txt"
    assert hello_file_path.exists() and code_result.exit_code == 0


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_start_stop() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    with tempfile.TemporaryDirectory() as temp_dir:
        jupyter_server = DockerJupyterServer(bind_dir=temp_dir)
        executor = DockerJupyterCodeExecutor(jupyter_server=jupyter_server)
        await executor.start()
        await executor.stop()


@pytest.mark.asyncio
async def test_invalid_timeout() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    with pytest.raises(ValueError, match="Timeout must be greater than or equal to 1."):
        with tempfile.TemporaryDirectory() as temp_dir:
            async with DockerJupyterServer(bind_dir=temp_dir) as jupyter_server:
                _ = DockerJupyterCodeExecutor(jupyter_server=jupyter_server, timeout=0)


@pytest.mark.asyncio
async def test_execute_code_with_image_output() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerJupyterServer(bind_dir=temp_dir) as jupyter_server:
            async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                code_blocks = [
                    CodeBlock(
                        code=inspect.cleandoc("""
                            !pip install pillow
                            from PIL import Image, ImageDraw
                            img = Image.new("RGB", (100, 100), color="white")
                            draw = ImageDraw.Draw(img)
                            draw.rectangle((10, 10, 90, 90), outline="black", fill="blue")
                            display(img)
                        """),
                        language="python",
                    )
                ]

                code_result = await executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
                assert len(code_result.output_files) == 1
                assert code_result.exit_code == 0
                assert "<PIL.Image.Image image mode=RGB size=100x100>" in code_result.output
                assert str(Path(code_result.output_files[0]).parent) == temp_dir
