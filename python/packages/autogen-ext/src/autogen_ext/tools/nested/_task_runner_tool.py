from abc import ABC, abstractmethod
from typing import Annotated, Any, Mapping

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.messages import (
    ModelClientStreamingChunkEvent,
    ToolCallSummaryMessage,
)
from autogen_agentchat.teams._group_chat._base_group_chat import BaseGroupChat
from autogen_agentchat.teams._group_chat._events import GroupChatMessage
from autogen_core import CancellationToken, ComponentModel
from autogen_core.tools import BaseToolWithState
from pydantic import BaseModel
from typing import Type
from autogen_agentchat.state import BaseState

class TaskRunnerToolInput(BaseModel):
    """Input for the TaskRunnerTool."""

    task: Annotated[str, "The task to be executed by the agent."]


class TaskRunnerTool(BaseToolWithState):
    """Tool that can be used to run a task."""

    component_type = "tool"

    def __init__(self, task_runner: BaseGroupChat | BaseChatAgent, state_type: Type[BaseState], name: str, description: str) -> None:
        self._task_runner = task_runner
        super().__init__(
            args_type=TaskRunnerToolInput,
            return_type=str,
            state_type=state_type,
            name=name,
            description=description,
        )

    async def run(self, args: TaskRunnerToolInput, cancellation_token: CancellationToken) -> str:
        result = await self._task_runner.run(task=args.task, cancellation_token=cancellation_token)
        return result.model_dump_json()