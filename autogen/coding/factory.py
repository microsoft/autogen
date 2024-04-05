from .base import CodeExecutionConfig, CodeExecutor

__all__ = ("CodeExecutorFactory",)


class CodeExecutorFactory:
    """(Experimental) A factory class for creating code executors."""

    @staticmethod
    def create(code_execution_config: CodeExecutionConfig) -> CodeExecutor:
        """(Experimental) Get a code executor based on the code execution config.

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
        if executor == "ipython-embedded":
            from .jupyter.embedded_ipython_code_executor import EmbeddedIPythonCodeExecutor

            return EmbeddedIPythonCodeExecutor(**code_execution_config.get("ipython-embedded", {}))
        elif executor == "commandline-local":
            from .local_commandline_code_executor import LocalCommandLineCodeExecutor

            return LocalCommandLineCodeExecutor(**code_execution_config.get("commandline-local", {}))
        else:
            raise ValueError(f"Unknown code executor {executor}")
