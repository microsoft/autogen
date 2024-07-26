# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_commandline_code_executor.py
# Credit to original authors

import sys
import tempfile
from pathlib import Path

import pytest
from agnext.components.code_executor import CodeBlock, LocalCommandLineCodeExecutor

UNIX_SHELLS = ["bash", "sh", "shell"]
WINDOWS_SHELLS = ["ps1", "pwsh", "powershell"]
PYTHON_VARIANTS = ["python", "Python", "py"]

@pytest.mark.asyncio
async def test_execute_code() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)


        # Test single code block.
        code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

        # Test multiple code blocks.
        code_blocks = [
            CodeBlock(code="import sys; print('hello world!')", language="python"),
            CodeBlock(code="a = 100 + 100; print(a)", language="python"),
        ]
        code_result = await executor.execute_code_blocks(code_blocks)
        assert (
            code_result.exit_code == 0
            and "hello world!" in code_result.output
            and "200" in code_result.output
            and code_result.code_file is not None
        )

        # Test bash script.
        if sys.platform not in ["win32"]:
            code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
            code_result = await executor.execute_code_blocks(code_blocks)
            assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

        # Test running code.
        file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
        code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
        code_result = await executor.execute_code_blocks(code_blocks)
        assert (
            code_result.exit_code == 0
            and "hello world!" in code_result.output
            and "200" in code_result.output
            and code_result.code_file is not None
        )

        # Check saved code file.
        with open(code_result.code_file) as f:
            code_lines = f.readlines()
            for file_line, code_line in zip(file_lines, code_lines):
                assert file_line.strip() == code_line.strip()

@pytest.mark.asyncio
async def test_commandline_code_executor_timeout() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(timeout=1, work_dir=temp_dir)
        code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
        code_result = await executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code and "Timeout" in code_result.output


def test_local_commandline_code_executor_restart() -> None:
    executor = LocalCommandLineCodeExecutor()
    with pytest.warns(UserWarning, match=r".*No action is taken."):
        executor.restart()



@pytest.mark.asyncio
async def test_invalid_relative_path() -> None:
    executor = LocalCommandLineCodeExecutor()
    code = """# filename: /tmp/test.py

print("hello world")
"""
    result = await executor.execute_code_blocks([CodeBlock(code=code, language="python")])
    assert result.exit_code == 1 and "Filename is not in the workspace" in result.output

@pytest.mark.asyncio
async def test_valid_relative_path() -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        code = """# filename: test.py

print("hello world")
"""
        result = await executor.execute_code_blocks([CodeBlock(code=code, language="python")])
        assert result.exit_code == 0
        assert "hello world" in result.output
        assert result.code_file is not None
        assert "test.py" in result.code_file
        assert (temp_dir / Path("test.py")).resolve() == Path(result.code_file).resolve()
        assert (temp_dir / Path("test.py")).exists()

