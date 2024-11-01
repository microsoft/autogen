from dataclasses import dataclass
from typing import AsyncGenerator, Protocol, Sequence

from autogen_core.base import CancellationToken

from ..messages import ChatMessage, InnerMessage


@dataclass
class TaskResult:
    """Result of running a task."""

    messages: Sequence[InnerMessage | ChatMessage]
    """Messages produced by the task."""


class TaskRunner(Protocol):
    """A task runner."""

    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> TaskResult:
        """Run the task."""
        ...

    def run_stream(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[InnerMessage | ChatMessage | TaskResult, None]:
        """Run the task and produces a stream of messages and the final result
        as the last item in the stream."""
        ...
