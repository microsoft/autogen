from abc import ABC
from typing import Annotated, Any, Mapping

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.teams._group_chat._base_group_chat import BaseGroupChat


class TaskRunnerToolArgs(BaseModel):
    """Input for the TaskRunnerTool."""

    task: Annotated[str, "The task to be executed."]


class TaskRunnerTool(BaseTool[TaskRunnerToolArgs, TaskResult], ABC):
    """An base class for tool that can be used to run a task using a team or an agent."""

    component_type = "tool"

    def __init__(self, task_runner: BaseGroupChat | BaseChatAgent, name: str, description: str) -> None:
        self._task_runner = task_runner
        super().__init__(
            args_type=TaskRunnerToolArgs,
            return_type=TaskResult,
            name=name,
            description=description,
        )

    async def run(self, args: TaskRunnerToolArgs, cancellation_token: CancellationToken) -> TaskResult:
        return await self._task_runner.run(task=args.task, cancellation_token=cancellation_token)

    async def save_state_json(self) -> Mapping[str, Any]:
        return await self._task_runner.save_state()

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        await self._task_runner.load_state(state)
