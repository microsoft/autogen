from typing import Protocol

from ._task import TaskRunner


class Team(TaskRunner, Protocol):
    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        ...
