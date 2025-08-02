import logging
import tempfile

import pytest
from autogen_core import CancellationToken
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.tools.code_execution import CodeExecutionInput, CodeExecutionTool


@pytest.mark.asyncio
async def test_code_execution_tool(caplog: pytest.LogCaptureFixture) -> None:
    """Test basic functionality of CodeExecutionTool."""
    # Create a temporary directory for the executor
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize the executor and tool
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        tool = CodeExecutionTool(executor=executor)

        with caplog.at_level(logging.INFO):
            # Test simple code execution
            code = "print('hello world!')"
            result = await tool.run_json(
                args={"code": code, "language": "python"}, cancellation_token=CancellationToken()
            )
            # Check log output
            assert "hello world!" in caplog.text

        # Verify successful execution
        assert result.success is True
        assert "hello world!" in result.output

        # Test code with computation
        code = """a = 100 + 200 \nprint(f'Result: {a}')
        """
        result = await tool.run(
            args=CodeExecutionInput(language="python", code=code), cancellation_token=CancellationToken()
        )

        # Verify computation result
        assert result.success is True
        assert "Result: 300" in result.output

        # Test error handling
        code = "print(undefined_variable)"
        result = await tool.run(
            args=CodeExecutionInput(language="python", code=code), cancellation_token=CancellationToken()
        )

        # Verify error handling
        assert result.success is False
        assert "NameError" in result.output

        # Test shell command execution
        code = "echo 'hello world!'"
        result = await tool.run(
            args=CodeExecutionInput(language="sh", code=code), cancellation_token=CancellationToken()
        )

        assert result.success is True
        assert "hello world!" in result.output

        code = "fake_command"
        result = await tool.run(
            args=CodeExecutionInput(language="sh", code=code), cancellation_token=CancellationToken()
        )

        assert result.success is False
        assert "fake_command: not found" in result.output


def test_code_execution_tool_serialization() -> None:
    """Test serialization and deserialization of CodeExecutionTool."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create original tool
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        original_tool = CodeExecutionTool(executor=executor)

        # Serialize
        config = original_tool.dump_component()
        assert config.config.get("executor") is not None

        # Deserialize
        loaded_tool = CodeExecutionTool.load_component(config)

        # Verify the loaded tool has the same configuration
        assert isinstance(loaded_tool, CodeExecutionTool)
