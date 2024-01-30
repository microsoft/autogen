from typing import Any, Dict

from .base import CodeExecutor

__all__ = ("CodeExecutorFactory",)


class CodeExecutorFactory:
    """A factory class for creating code executors."""

    @staticmethod
    def create(code_execution_config: Dict[str, Any]) -> CodeExecutor:
        """Get a code executor based on the code execution config.

        Args:
            code_execution_config (Dict): The code execution config,
                which is a dictionary that must contain the key "executor".
                The value of the key "executor" can be either a string
                or an instance of CodeExecutor, in which case the code
                executor is returned directly.

        Returns:
            CodeExecutor: The code executor.

        Raises:
            ValueError: If the code executor is unknown or not specified.
        """
        executor = code_execution_config.get("executor")
        if isinstance(executor, CodeExecutor):
            # If the executor is already an instance of CodeExecutor, return it.
            return executor
        if executor == "ipython":
            from .ipython_code_executor import IPythonCodeExecutor

            return IPythonCodeExecutor(**code_execution_config.get("ipython", {}))
        elif executor == "commandline":
            from .commandline_code_executor import CommandlineCodeExecutor

            return CommandlineCodeExecutor(**code_execution_config.get("commandline", {}))
        else:
            raise ValueError(f"Unknown code executor {executor}")
