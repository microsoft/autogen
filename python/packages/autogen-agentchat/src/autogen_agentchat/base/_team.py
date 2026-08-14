from abc import ABC, abstractmethod
from typing import Any, Mapping

from autogen_core import ComponentBase
from pydantic import BaseModel

from ._task import TaskRunner


class Team(ABC, TaskRunner, ComponentBase[BaseModel]):
    component_type = "team"

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the team. This is used by team to uniquely identify itself
        in a larger team of teams."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of the team. This is used to provide context about the
        team and its purpose to its parent orchestrator."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        ...

    @abstractmethod
    async def pause(self) -> None:
        """Pause the team and all its participants. This is useful for
        pausing the :meth:`autogen_agentchat.base.TaskRunner.run` or
        :meth:`autogen_agentchat.base.TaskRunner.run_stream` methods from
        concurrently, while keeping them alive."""
        ...

    @abstractmethod
    async def resume(self) -> None:
        """Resume the team and all its participants from a pause after
        :meth:`pause` was called."""
        ...

    @abstractmethod
    async def save_state(self) -> Mapping[str, Any]:
        """Save the current state of the team."""
        ...

    @abstractmethod
    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the state of the team."""
        ...
