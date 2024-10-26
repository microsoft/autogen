from dataclasses import dataclass
from typing import Protocol, Sequence

from autogen_core.base import CancellationToken

from ..messages import ChatMessage
from ._termination import TerminationCondition


@dataclass
class TaskResult:
    """Result of running a task."""

    messages: Sequence[ChatMessage]
    """Messages produced by the task."""


class TaskRunner(Protocol):
    """A task runner."""

    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
        termination_condition: TerminationCondition | None = None,
    ) -> TaskResult:
        """Run the task."""
        ...
