from typing import Dict

from autogen.coding.base import CodeExecutor


class CodeExecutorFactory:
    """A factory class for creating code executors."""

    @staticmethod
    def create(code_execution_config: Dict) -> CodeExecutor:
        """Get a code executor based on the code execution config."""
        backend = code_execution_config.get("backend", "commandline")
        if backend == "ipython":
            from autogen.coding.ipython_code_executor import IPythonCodeExecutor

            return IPythonCodeExecutor(code_execution_config)
        elif backend == "commandline":
            # Default to command line code executor.
            from autogen.coding.commandline_code_executor import CommandlineCodeExecutor

            return CommandlineCodeExecutor(code_execution_config)
        else:
            raise ValueError(f"Unknown code executor backend {backend}")
