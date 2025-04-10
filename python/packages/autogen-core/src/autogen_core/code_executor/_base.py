# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/base.py
# Credit to original authors

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import TracebackType
from typing import List, Optional, Type

from pydantic import BaseModel
from typing_extensions import Self

from .._cancellation_token import CancellationToken
from .._component_config import ComponentBase


@dataclass
class CodeBlock:
    """A code block extracted fromm an agent message."""

    code: str
    language: str


@dataclass
class CodeResult:
    """Result of a code execution."""

    exit_code: int
    output: str


class CodeExecutor(ABC, ComponentBase[BaseModel]):
    """Executes code blocks and returns the result.

    This is an abstract base class for code executors. It defines the interface
    for executing code blocks and returning the result. A concrete implementation
    of this class should be provided to execute code blocks in a specific
    environment. For example, :class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` executes
    code blocks in a command line environment in a Docker container.

    It is recommended for subclass to be used as a context manager to ensure
    that resources are cleaned up properly. To do this, implement the
    :meth:`~autogen_core.code_executor.CodeExecutor.start` and
    :meth:`~autogen_core.code_executor.CodeExecutor.stop` methods
    that will be called when entering and exiting the context manager.

    """

    component_type = "code_executor"

    @abstractmethod
    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CodeResult:
        """Execute code blocks and return the result.

        This method should be implemented by the code executor.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CodeResult: The result of the code execution.

        Raises:
            ValueError: Errors in user inputs
            asyncio.TimeoutError: Code execution timeouts
            asyncio.CancelledError: CancellationToken evoked during execution
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the code executor."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the code executor and release any resources."""
        ...

    @abstractmethod
    async def restart(self) -> None:
        """Restart the code executor.

        This method should be implemented by the code executor.

        This method is called when the agent is reset.
        """
        ...

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> Optional[bool]:
        await self.stop()
        return None
