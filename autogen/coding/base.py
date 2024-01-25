from __future__ import annotations
from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable

from pydantic import BaseModel


class CodeBlock(BaseModel):
    """A class that represents a code block."""

    """The code to execute."""
    code: str

    """The language of the code."""
    language: str


class CodeResult(BaseModel):
    """A class that represents the result of a code execution."""

    """The exit code of the code execution."""
    exit_code: int

    """The output of the code execution."""
    output: str


class CodeExecutor(Protocol):
    class UserCapability(Protocol):
        """An AgentCapability class that gives agent ability use this code executor."""

        def add_to_agent(self, agent):
            ...  # pragma: no cover

    @property
    def user_capability(self) -> CodeExecutor.UserCapability:
        """Capability to use this code executor.

        The exported capability can be added to an agent to allow it to use this
        code executor:

        ```python
        code_executor = CodeExecutor()
        agent = Agent()
        code_executor.user_capability.add_to_agent(agent)
        ```

        A typical implementation is to update the system message of the agent with
        instructions for how to use this code executor.
        """
        ...  # pragma: no cover

    def extract_code_blocks(self, message: str) -> List[CodeBlock]:
        """Extract code blocks from a message.

        This method should be implemented by the code executor.

        Args:
            message (str): The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks.
        """
        ...  # pragma: no cover

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CodeResult:
        """Execute code blocks and return the result.

        This method should be implemented by the code executor.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CodeResult: The result of the code execution.
        """
        ...  # pragma: no cover

    def reset(self) -> None:
        """Reset the code executor.

        This method should be implemented by the code executor.

        This method is called when the agent is reset.
        """
        ...
