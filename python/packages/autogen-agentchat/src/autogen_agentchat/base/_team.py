from abc import abstractmethod
from typing import Protocol

from ..state import BaseTeamState
from ._task import TaskRunner


class Team(TaskRunner, Protocol):
    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        ...

    @abstractmethod
    async def save_state(self) -> BaseTeamState:
        """Save the current state of the group chat manager."""
        pass

    @abstractmethod
    async def load_state(self, state: BaseTeamState) -> None:
        """Load the state of the group chat manager."""
        pass
