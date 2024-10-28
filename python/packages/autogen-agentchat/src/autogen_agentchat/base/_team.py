from typing import Protocol

from autogen_core.base import CancellationToken

from ._task import TaskResult, TaskRunner
from ._termination import TerminationCondition


class Team(TaskRunner, Protocol):
    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
        termination_condition: TerminationCondition | None = None,
    ) -> TaskResult:
        """Run the team on a given task until the termination condition is met."""
        ...
