from typing import Any, Mapping, Protocol

from ._task import TaskRunner


class Team(TaskRunner, Protocol):
    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        ...

    async def save_state(self) -> Mapping[str, Any]:
        """Save the current state of the team."""
        ...

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the state of the team."""
        ...
