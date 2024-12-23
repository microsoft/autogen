import asyncio
from pathlib import Path

import pytest
import websockets
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.jupyter import JupyterCodeExecutor, JupyterCodeResult, LocalJupyterServer


@pytest.mark.asyncio
async def test_execute_code(tmp_path: Path) -> None:
    with LocalJupyterServer() as server, JupyterCodeExecutor(server, output_dir=tmp_path) as executor:
        # Test single code block.
        code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n", output_files=[])

        # Test multiple code blocks.
        code_blocks = [
            CodeBlock(code="import sys; print('hello world!')", language="python"),
            CodeBlock(code="a = 100 + 100; print(a)", language="python"),
        ]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n\n200\n", output_files=[])

        # Test running code.
        file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
        code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n200\n", output_files=[])


@pytest.mark.asyncio
async def test_execute_code_after_restart(tmp_path: Path) -> None:
    with LocalJupyterServer() as server, JupyterCodeExecutor(server, output_dir=tmp_path) as executor:
        await executor.restart()

        code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n", output_files=[])


@pytest.mark.asyncio
async def test_execute_code_after_stop(tmp_path: Path) -> None:
    with LocalJupyterServer() as server, JupyterCodeExecutor(server, output_dir=tmp_path) as executor:
        await asyncio.sleep(1)
        executor.stop()

        with pytest.raises(websockets.exceptions.InvalidStatus):
            code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
            await executor.execute_code_blocks(code_blocks, CancellationToken())


@pytest.mark.asyncio
async def test_execute_code_after_stop_and_start(tmp_path: Path) -> None:
    with LocalJupyterServer() as server, JupyterCodeExecutor(server, output_dir=tmp_path) as executor:
        executor.stop()
        executor.start()

        code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n", output_files=[])


@pytest.mark.asyncio
async def test_commandline_code_executor_timeout(tmp_path: Path) -> None:
    with LocalJupyterServer() as server, JupyterCodeExecutor(server, output_dir=tmp_path, timeout=1) as executor:
        code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

        with pytest.raises(asyncio.TimeoutError):
            await executor.execute_code_blocks(code_blocks, CancellationToken())


@pytest.mark.asyncio
async def test_commandline_code_executor_cancellation(tmp_path: Path) -> None:
    with LocalJupyterServer() as server, JupyterCodeExecutor(server, output_dir=tmp_path) as executor:
        executor = JupyterCodeExecutor(server=server, output_dir=tmp_path)
        code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

        cancellation_token = CancellationToken()
        code_result_coroutine = executor.execute_code_blocks(code_blocks, cancellation_token)

        await asyncio.sleep(1)
        cancellation_token.cancel()

        with pytest.raises(asyncio.CancelledError):
            await code_result_coroutine
