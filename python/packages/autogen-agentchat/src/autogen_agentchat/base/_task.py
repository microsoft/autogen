from dataclasses import dataclass
from typing import AsyncGenerator, Protocol, Sequence

from autogen_core.base import CancellationToken

from ..messages import AgentMessage


@dataclass
class TaskResult:
    """Result of running a task."""

    messages: Sequence[AgentMessage]
    """Messages produced by the task."""

    stop_reason: str | None = None
    """The reason the task stopped."""


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
    ) -> AsyncGenerator[AgentMessage | TaskResult, None]:
        """Run the task and produces a stream of messages and the final result
        :class:`TaskResult` as the last item in the stream."""
        ...
