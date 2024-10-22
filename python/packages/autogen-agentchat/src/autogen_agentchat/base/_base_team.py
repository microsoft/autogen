from typing import Protocol

from ._base_task import TaskResult, TaskRunner
from ._base_termination import TerminationCondition


class Team(TaskRunner, Protocol):
    async def run(self, task: str, *, termination_condition: TerminationCondition | None = None) -> TaskResult:
        """Run the team on a given task until the termination condition is met."""
        ...
