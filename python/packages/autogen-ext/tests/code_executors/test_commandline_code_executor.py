# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_commandline_code_executor.py
# Credit to original authors

import asyncio
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import types
import venv
from pathlib import Path
from typing import AsyncGenerator, TypeAlias
from unittest.mock import patch

import pytest
import pytest_asyncio
from aiofiles import open
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

HAS_POWERSHELL: bool = platform.system() == "Windows" and (
    shutil.which("powershell") is not None or shutil.which("pwsh") is not None
)
IS_MACOS: bool = platform.system() == "Darwin"
IS_UV_VENV: bool = (
    lambda: (
        (
            lambda venv_path: (
                False
                if not venv_path
                else (
                    False
                    if not os.path.isfile(os.path.join(venv_path, "pyvenv.cfg"))
                    else (
                        subprocess.run(
                            ["grep", "-q", "^uv = ", os.path.join(venv_path, "pyvenv.cfg")],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        ).returncode
                        == 0
                    )
                )
            )
        )(os.environ.get("VIRTUAL_ENV"))
    )
)()
HAS_UV: bool = shutil.which("uv") is not None


def create_venv_with_uv(env_dir: str) -> types.SimpleNamespace:
    try:
        subprocess.run(
            ["uv", "venv", env_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        error_message = f"uv virtual env creation failed with error code {e.returncode}:\n"
        error_message += f"  cmd:\n{e.stdout.decode()}\n"
        error_message += f"  stderr:\n{e.stderr}\n"
        error_message += f"  stdout:\n{e.stdout}"
        raise RuntimeError(error_message) from e
    except Exception as e:
        raise RuntimeError(f"Failed to create uv virtual env: {e}") from e

    # create a venv.EnvBuilder context
    if platform.system() == "Windows":
        bin_name = "Scripts"
        exe_suffix = ".exe"
    else:
        bin_name = "bin"
        exe_suffix = ""

    bin_path = os.path.join(env_dir, bin_name)
    python_executable = os.path.join(bin_path, f"python{exe_suffix}")
    py_version_short = f"{sys.version_info.major}.{sys.version_info.minor}"
    lib_path = os.path.join(env_dir, "lib", f"python{py_version_short}", "site-packages")
    if not os.path.exists(lib_path):
        lib_path_fallback = os.path.join(env_dir, "lib")
        if os.path.exists(lib_path_fallback):
            lib_path = lib_path_fallback
        else:
            raise RuntimeError(f"Failed to find site-packages in {lib_path} or {lib_path_fallback}")

    context = types.SimpleNamespace(
        env_dir=env_dir,
        env_name=os.path.basename(env_dir),
        prompt=f"({os.path.basename(env_dir)}) ",
        executable=python_executable,
        python_dir=os.path.dirname(python_executable),
        python_exe=os.path.basename(python_executable),
        inc_path=os.path.join(env_dir, "include"),
        lib_path=lib_path,  # site-packages
        bin_path=bin_path,  # bin or Scripts
        bin_name=bin_name,  # bin or Scripts
        env_exe=python_executable,
        env_exec_cmd=python_executable,
    )

    return context


@pytest_asyncio.fixture(scope="function")  # type: ignore
async def executor_and_temp_dir(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[tuple[LocalCommandLineCodeExecutor, str], None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, cleanup_temp_files=False)
        await executor.start()
        yield executor, temp_dir


ExecutorFixture: TypeAlias = tuple[LocalCommandLineCodeExecutor, str]


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["local"], indirect=True)
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
@pytest.mark.parametrize("executor_and_temp_dir", ["local"], indirect=True)
async def test_commandline_code_executor_timeout(executor_and_temp_dir: ExecutorFixture) -> None:
    executor, temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    executor = LocalCommandLineCodeExecutor(timeout=1, work_dir=temp_dir)
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code and "Timeout" in code_result.output


@pytest.mark.asyncio
async def test_commandline_code_executor_cancellation() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        await executor.start()
        # Write code that sleep for 10 seconds and then write "hello world!"
        # to a file.
        code = """import time
time.sleep(10)
with open("hello.txt", "w") as f:
    f.write("hello world!")
"""
        code_blocks = [CodeBlock(code=code, language="python")]

        coro = executor.execute_code_blocks(code_blocks, cancellation_token)

        await asyncio.sleep(1)
        cancellation_token.cancel()
        code_result = await coro

        assert code_result.exit_code and "Cancelled" in code_result.output

        # Check if the file is not created.
        hello_file = Path(temp_dir) / "hello.txt"
        assert not hello_file.exists()


@pytest.mark.asyncio
async def test_local_commandline_code_executor_restart() -> None:
    executor = LocalCommandLineCodeExecutor()
    with pytest.warns(UserWarning, match=r".*No action is taken."):
        await executor.restart()


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["local"], indirect=True)
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
@pytest.mark.parametrize("executor_and_temp_dir", ["local"], indirect=True)
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
@pytest.mark.skipif(
    IS_MACOS and IS_UV_VENV,
    reason="uv-venv is not supported on macOS.",
)
async def test_local_executor_with_custom_venv() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env_builder = venv.EnvBuilder(with_pip=True)
        env_builder.create(temp_dir)
        env_builder_context = env_builder.ensure_directories(temp_dir)

        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, virtual_env_context=env_builder_context)
        await executor.start()

        code_blocks = [
            # https://stackoverflow.com/questions/1871549/how-to-determine-if-python-is-running-inside-a-virtualenv
            CodeBlock(code="import sys; print(sys.prefix != sys.base_prefix)", language="python"),
        ]
        cancellation_token = CancellationToken()
        result = await executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)

        assert result.exit_code == 0
        assert result.output.strip() == "True"


@pytest.mark.asyncio
@pytest.mark.skipif(
    IS_MACOS and IS_UV_VENV,
    reason="uv-venv is not supported on macOS.",
)
async def test_local_executor_with_custom_venv_in_local_relative_path() -> None:
    relative_folder_path = "tmp_dir"
    try:
        if not os.path.isdir(relative_folder_path):
            os.mkdir(relative_folder_path)

        env_path = os.path.join(relative_folder_path, ".venv")
        env_builder = venv.EnvBuilder(with_pip=True)
        env_builder.create(env_path)
        env_builder_context = env_builder.ensure_directories(env_path)

        executor = LocalCommandLineCodeExecutor(work_dir=relative_folder_path, virtual_env_context=env_builder_context)
        await executor.start()

        code_blocks = [
            CodeBlock(code="import sys; print(sys.executable)", language="python"),
        ]
        cancellation_token = CancellationToken()
        result = await executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)

        assert result.exit_code == 0

        # Check if the expected venv has been used
        bin_path = os.path.abspath(env_builder_context.bin_path)
        assert Path(result.output.strip()).parent.samefile(bin_path)
    finally:
        if os.path.isdir(relative_folder_path):
            shutil.rmtree(relative_folder_path)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not HAS_UV,
    reason="uv is not installed.",
)
async def test_local_executor_with_custom_uv_venv() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env_builder_context = create_venv_with_uv(temp_dir)

        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, virtual_env_context=env_builder_context)
        await executor.start()

        code_blocks = [
            # https://stackoverflow.com/questions/1871549/how-to-determine-if-python-is-running-inside-a-virtualenv
            CodeBlock(code="import sys; print(sys.prefix != sys.base_prefix)", language="python"),
        ]
        cancellation_token = CancellationToken()
        result = await executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)

        assert result.exit_code == 0
        assert result.output.strip() == "True"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not HAS_UV,
    reason="uv is not installed.",
)
async def test_local_executor_with_custom_uv_venv_in_local_relative_path() -> None:
    relative_folder_path = "tmp_dir"
    try:
        if not os.path.isdir(relative_folder_path):
            os.mkdir(relative_folder_path)

        env_path = os.path.join(relative_folder_path, ".venv")
        env_builder_context = create_venv_with_uv(env_path)

        executor = LocalCommandLineCodeExecutor(work_dir=relative_folder_path, virtual_env_context=env_builder_context)
        await executor.start()

        code_blocks = [
            CodeBlock(code="import sys; print(sys.executable)", language="python"),
        ]
        cancellation_token = CancellationToken()
        result = await executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)

        assert result.exit_code == 0

        # Check if the expected venv has been used
        bin_path = os.path.abspath(env_builder_context.bin_path)
        assert Path(result.output.strip()).parent.samefile(bin_path)
    finally:
        if os.path.isdir(relative_folder_path):
            shutil.rmtree(relative_folder_path)


@pytest.mark.asyncio
async def test_serialize_deserialize() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        await executor.start()
        executor_config = executor.dump_component()
        loaded_executor = LocalCommandLineCodeExecutor.load_component(executor_config)
        await loaded_executor.start()
        assert executor.work_dir == loaded_executor.work_dir

        await executor.stop()
        await loaded_executor.stop()


@pytest.mark.asyncio
@pytest.mark.windows
@pytest.mark.skipif(
    not HAS_POWERSHELL,
    reason="No PowerShell interpreter (powershell or pwsh) found on this environment.",
)
@pytest.mark.parametrize("executor_and_temp_dir", ["local"], indirect=True)
async def test_ps1_script(executor_and_temp_dir: ExecutorFixture) -> None:
    """
    Test execution of a simple PowerShell script.
    This test is skipped if powershell/pwsh is not installed.
    """
    executor, _ = executor_and_temp_dir
    cancellation_token = CancellationToken()
    code = 'Write-Host "hello from powershell!"'
    code_blocks = [CodeBlock(code=code, language="powershell")]
    result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert result.exit_code == 0
    assert "hello from powershell!" in result.output
    assert result.code_file is not None


@pytest.mark.asyncio
async def test_cleanup_temp_files_behavior() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with cleanup_temp_files=True (default)
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, cleanup_temp_files=True)
        await executor.start()
        cancellation_token = CancellationToken()
        code_blocks = [CodeBlock(code="print('cleanup test')", language="python")]
        result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert result.exit_code == 0
        assert "cleanup test" in result.output
        # The code file should have been deleted
        assert result.code_file is not None
        assert not Path(result.code_file).exists()

        # Test with cleanup_temp_files=False
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, cleanup_temp_files=False)
        await executor.start()
        cancellation_token = CancellationToken()
        code_blocks = [CodeBlock(code="print('no cleanup')", language="python")]
        result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert result.exit_code == 0
        assert "no cleanup" in result.output
        # The code file should still exist
        assert result.code_file is not None
        assert Path(result.code_file).exists()


@pytest.mark.asyncio
async def test_cleanup_temp_files_oserror(caplog: pytest.LogCaptureFixture) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, cleanup_temp_files=True)
        await executor.start()
        cancellation_token = CancellationToken()
        code_blocks = [CodeBlock(code="print('cleanup test')", language="python")]

        # Patch Path.unlink to raise OSError for this test
        with patch("pathlib.Path.unlink", side_effect=OSError("Mocked OSError")):
            with caplog.at_level("ERROR"):
                await executor.execute_code_blocks(code_blocks, cancellation_token)
                # The code file should have been attempted to be deleted and failed
                assert any("Failed to delete temporary file" in record.message for record in caplog.records)
                assert any("Mocked OSError" in record.message for record in caplog.records)
