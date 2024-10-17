import warnings

from ...code_executors import DockerCommandLineCodeExecutor

warnings.warn(
    "DockerCommandLineCodeExecutor moved to autogen_ext.code_executors.DockerCommandLineCodeExecutor",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["DockerCommandLineCodeExecutor"]
