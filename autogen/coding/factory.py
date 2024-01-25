from typing import Dict

from autogen.coding.base import CodeExecutor


class CodeExecutorFactory:
    """A factory class for creating code executors."""

    @staticmethod
    def create(code_execution_config: Dict) -> CodeExecutor:
        """Get a code executor based on the code execution config."""
        executor_name = code_execution_config.get("executor")
        if executor_name == "ipython":
            from autogen.coding.ipython_code_executor import IPythonCodeExecutor

            return IPythonCodeExecutor(**code_execution_config.get("ipython", {}))
        elif executor_name == "commandline":
            from autogen.coding.commandline_code_executor import CommandlineCodeExecutor

            return CommandlineCodeExecutor(**code_execution_config.get("commandline", {}))
        else:
            raise ValueError(f"Unknown code executor {executor_name}")
