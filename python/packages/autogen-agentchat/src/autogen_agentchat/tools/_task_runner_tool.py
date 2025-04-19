from abc import ABC
from typing import Annotated, Any, List, Mapping

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel

from ..agents import BaseChatAgent
from ..base import TaskResult
from ..messages import BaseChatMessage
from ..teams import BaseGroupChat


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

    def return_value_as_string(self, value: TaskResult) -> str:
        """Convert the task result to a string."""
        parts: List[str] = []
        for message in value.messages:
            if isinstance(message, BaseChatMessage):
                if message.source == "user":
                    continue
                parts.append(f"{message.source}: {message.to_model_text()}")
        return "\n\n".join(parts)

    async def save_state_json(self) -> Mapping[str, Any]:
        return await self._task_runner.save_state()

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        await self._task_runner.load_state(state)
