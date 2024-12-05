# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/base.py
# Credit to original authors

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, runtime_checkable

from typing_extensions import deprecated

from ... import CancellationToken


@deprecated("Moved to autogen_core.code_executor.CodeBlock. This alias will be removed in 0.4.0.")
@dataclass
class CodeBlock:
    """A code block extracted fromm an agent message."""

    code: str
    language: str


@deprecated("Moved to autogen_core.code_executor.CodeResult. This alias will be removed in 0.4.0.")
@dataclass
class CodeResult:
    """Result of a code execution."""

    exit_code: int
    output: str


@deprecated("Moved to autogen_core.code_executor.CodeExecutor. This alias will be removed in 0.4.0.")
@runtime_checkable
class CodeExecutor(Protocol):
    """Executes code blocks and returns the result."""

    async def execute_code_blocks(
        self,
        code_blocks: List[CodeBlock],  # type: ignore
        cancellation_token: CancellationToken,  # type: ignore
    ) -> CodeResult:  # type: ignore
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

    async def restart(self) -> None:
        """Restart the code executor.

        This method should be implemented by the code executor.

        This method is called when the agent is reset.
        """
        ...
