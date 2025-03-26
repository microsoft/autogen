from abc import ABC, abstractmethod
from typing import Annotated, Any, Mapping

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.messages import (
    ModelClientStreamingChunkEvent,
    ToolCallSummaryMessage,
)
from autogen_agentchat.teams import AgentChatRuntimeContext
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
        try:
            runtime = AgentChatRuntimeContext.current_runtime()
        except RuntimeError as e:
            raise RuntimeError("TaskRunnerTool must be used within an AgentChatRuntimeContext.") from e
        response: TaskResult | None = None
        async for event in self._task_runner.run_stream(task=args.task, cancellation_token=cancellation_token):
            print(f"Received event: {event}")
            if isinstance(event, TaskResult):
                response = event
                break
            # Way too noisy
            if isinstance(event, ModelClientStreamingChunkEvent):
                continue
            # We've already got the events
            elif isinstance(event, ToolCallSummaryMessage):
                continue
            else:
                print(f"Publishing event: {event}")
                await runtime.publish_message(GroupChatMessage(message=event), AgentChatRuntimeContext.output_channel())

        assert response is not None
        return response.model_dump_json()
