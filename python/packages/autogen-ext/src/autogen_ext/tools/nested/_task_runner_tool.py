from abc import ABC, abstractmethod
from typing import Annotated, Any, Mapping

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.messages import (
    ModelClientStreamingChunkEvent,
    ToolCallSummaryMessage,
)
from autogen_agentchat.teams._group_chat._base_group_chat import BaseGroupChat
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel

class TaskRunnerToolInput(BaseModel):
    """Input for the TaskRunnerTool."""

    task: Annotated[str, "The task to be executed by the agent."]


class TaskRunnerTool(BaseTool):
    """Tool that can be used to run a task."""

    component_type = "tool"

    def __init__(self, task_runner: BaseGroupChat | BaseChatAgent, name: str, description: str) -> None:
        self._task_runner = task_runner
        super().__init__(
            args_type=TaskRunnerToolInput,
            return_type=TaskResult,
            name=name,
            description=description,
        )

    async def run(self, args: TaskRunnerToolInput, cancellation_token: CancellationToken) -> TaskResult:
        return await self._task_runner.run(task=args.task, cancellation_token=cancellation_token)
