from dataclasses import dataclass
from typing import Protocol


@dataclass
class TeamRunResult:
    result: str


class BaseTeam(Protocol):
    async def run(self, task: str) -> TeamRunResult:
        """Run the team and return the result."""
        ...
