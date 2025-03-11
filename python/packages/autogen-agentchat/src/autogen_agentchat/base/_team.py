from abc import ABC, abstractmethod
from typing import Any, Mapping

from autogen_core import ComponentBase
from pydantic import BaseModel

from ._task import TaskRunner


class Team(ABC, TaskRunner, ComponentBase[BaseModel]):
    def __init__(self, name: str, description: str):
        super().__init__()

    component_type = "team"

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the team. This is used by team to uniquely identify
        the team. It should be unique if it is part of a parent team."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """The description of the team. This is used by the parent team to
        make decisions about which agent or team to use. The description should
        describe the team's capabilities and how to interact with it."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        ...

    @abstractmethod
    async def save_state(self) -> Mapping[str, Any]:
        """Save the current state of the team."""
        ...

    @abstractmethod
    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the state of the team."""
        ...
