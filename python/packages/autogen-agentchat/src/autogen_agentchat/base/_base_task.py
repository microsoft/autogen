from dataclasses import dataclass
from typing import Protocol, Sequence

from ..messages import ChatMessage


@dataclass
class TaskResult:
    """Result of running a task."""

    messages: Sequence[ChatMessage]
    """Messages produced by the task."""


class TaskRunner(Protocol):
    """A task runner."""

    async def run(self, task: str) -> TaskResult:
        """Run the task."""
        ...
