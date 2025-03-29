import asyncio
import inspect
from pathlib import Path

import pytest
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.jupyter import JupyterCodeExecutor, JupyterCodeResult


@pytest.mark.asyncio
async def test_execute_code(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n", output_files=[])
        await executor.stop()


@pytest.mark.asyncio
async def test_execute_code_error(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [CodeBlock(code="print(undefined_variable)", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(
            exit_code=1,
            output=inspect.cleandoc("""
                ---------------------------------------------------------------------------
                NameError                                 Traceback (most recent call last)
                Cell In[1], line 1
                ----> 1 print(undefined_variable)

                NameError: name 'undefined_variable' is not defined
            """),
            output_files=[],
        )
        await executor.stop()


@pytest.mark.asyncio
async def test_execute_multiple_code_blocks(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [
            CodeBlock(code="import sys; print('hello world!')", language="python"),
            CodeBlock(code="a = 100 + 100; print(a)", language="python"),
        ]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n\n200\n", output_files=[])
        await executor.stop()


@pytest.mark.asyncio
async def test_depedent_executions(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks_1 = [CodeBlock(code="a = 'hello world!'", language="python")]
        code_blocks_2 = [
            CodeBlock(code="print(a)", language="python"),
        ]
        await executor.execute_code_blocks(code_blocks_1, CancellationToken())
        code_result = await executor.execute_code_blocks(code_blocks_2, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n", output_files=[])
        await executor.stop()


@pytest.mark.asyncio
async def test_execute_multiple_code_blocks_error(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [
            CodeBlock(code="import sys; print('hello world!')", language="python"),
            CodeBlock(code="a = 100 + 100; print(a); print(undefined_variable)", language="python"),
        ]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(
            exit_code=1,
            output=inspect.cleandoc("""
                hello world!

                200

                ---------------------------------------------------------------------------
                NameError                                 Traceback (most recent call last)
                Cell In[2], line 1
                ----> 1 a = 100 + 100; print(a); print(undefined_variable)

                NameError: name 'undefined_variable' is not defined
            """),
            output_files=[],
        )
        await executor.stop()


@pytest.mark.asyncio
async def test_execute_code_after_restart(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        await executor.restart()

        code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())
        assert code_result == JupyterCodeResult(exit_code=0, output="hello world!\n", output_files=[])
        await executor.stop()


@pytest.mark.asyncio
async def test_commandline_code_executor_timeout(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path, timeout=2) as executor:
        await executor.start()
        code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

        with pytest.raises(asyncio.TimeoutError):
            await executor.execute_code_blocks(code_blocks, CancellationToken())

        await executor.stop()


@pytest.mark.asyncio
async def test_commandline_code_executor_cancellation(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

        cancellation_token = CancellationToken()
        code_result_coroutine = executor.execute_code_blocks(code_blocks, cancellation_token)

        await asyncio.sleep(1)
        cancellation_token.cancel()

        with pytest.raises(asyncio.CancelledError):
            await code_result_coroutine

        await executor.stop()


@pytest.mark.asyncio
async def test_execute_code_with_image_output(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [
            CodeBlock(
                code=inspect.cleandoc("""
                    from PIL import Image, ImageDraw
                    img = Image.new("RGB", (100, 100), color="white")
                    draw = ImageDraw.Draw(img)
                    draw.rectangle((10, 10, 90, 90), outline="black", fill="blue")
                    display(img)
                """),
                language="python",
            )
        ]

        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())

        assert len(code_result.output_files) == 1
        assert code_result == JupyterCodeResult(
            exit_code=0,
            output="<PIL.Image.Image image mode=RGB size=100x100>",
            output_files=code_result.output_files,
        )
        assert code_result.output_files[0].parent == tmp_path

        await executor.stop()


@pytest.mark.asyncio
async def test_execute_code_with_html_output(tmp_path: Path) -> None:
    async with JupyterCodeExecutor(output_dir=tmp_path) as executor:
        await executor.start()
        code_blocks = [
            CodeBlock(
                code=inspect.cleandoc("""
                    from IPython.core.display import HTML
                    HTML("<div style='color:blue'>Hello, HTML world!</div>")
                """),
                language="python",
            )
        ]

        code_result = await executor.execute_code_blocks(code_blocks, CancellationToken())

        assert len(code_result.output_files) == 1
        assert code_result == JupyterCodeResult(
            exit_code=0,
            output="<IPython.core.display.HTML object>",
            output_files=code_result.output_files,
        )
        assert code_result.output_files[0].parent == tmp_path

        await executor.stop()


@pytest.mark.asyncio
async def test_jupyter_code_executor_serialization(tmp_path: Path) -> None:
    executor = JupyterCodeExecutor(output_dir=tmp_path)
    await executor.start()
    serialized = executor.dump_component()
    loaded_executor = JupyterCodeExecutor.load_component(serialized)
    await loaded_executor.start()

    assert isinstance(loaded_executor, JupyterCodeExecutor)

    await loaded_executor.stop()
    await executor.stop()
