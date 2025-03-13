from typing import Annotated, Any, Mapping

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.conditions import TextMessageTermination
from autogen_agentchat.messages import (
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ThoughtEvent,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
    UserInputRequestedEvent,
)
from autogen_agentchat.teams import TeamRuntimeContext
from autogen_agentchat.teams._group_chat._events import GroupChatMessage
from autogen_core import CancellationToken, Component, ComponentModel
from autogen_core.tools import BaseToolWithState
from pydantic import BaseModel
from typing_extensions import Self


class TaskRunnerToolState(BaseModel):
    """State for the TaskRunnerTool."""

    task_runner_state: Mapping[str, Any]


class TaskRunnerToolConfig(BaseModel):
    """Configuration for the TaskRunnerTool."""

    agent: ComponentModel


class TaskRunnerToolInput(BaseModel):
    """Input for the TaskRunnerTool."""

    task: Annotated[str, "The task to be executed by the agent."]


class TaskRunnerTool(BaseToolWithState, Component[TaskRunnerToolConfig]):
    """Tool that can be used to run a task."""

    component_type = "tool"
    component_config_schema = TaskRunnerToolConfig
    component_provider_override = "autogen_ext.tools.TaskRunnerTool"

    def __init__(self, agent: BaseChatAgent) -> None:
        self._agent = agent
        super().__init__(
            args_type=TaskRunnerToolInput,
            return_type=str,
            state_type=TaskRunnerToolState,
            name=self._agent.name,
            description=self._agent.description,
        )

    async def run(self, args: TaskRunnerToolInput, cancellation_token: CancellationToken) -> str:
        response = None
        async for event in self._agent.run_stream(task=args.task, cancellation_token=cancellation_token):
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
                await TeamRuntimeContext.current_runtime().publish_message(
                    GroupChatMessage(message=event), TeamRuntimeContext.output_channel()
                )

        assert response is not None
        return self._format_response(response)

    def _format_response(self, response: TaskResult) -> str:
        formatted_response: list[str] = []
        for message in response.messages:
            if isinstance(message, TextMessage):
                formatted_response += message.content
            elif isinstance(message, MultiModalMessage):
                raise NotImplementedError("MultiModalMessage is not supported yet.")
            elif isinstance(message, HandoffMessage):
                raise NotImplementedError("HandoffMessage is not supported yet.")
            elif isinstance(message, ToolCallSummaryMessage):
                formatted_response += message.content
            elif isinstance(message, StopMessage):
                continue
            elif isinstance(message, UserInputRequestedEvent):
                continue
            elif isinstance(message, ThoughtEvent):
                formatted_response += message.content
            elif isinstance(message, MemoryQueryEvent):
                raise NotImplementedError("MemoryQueryEvent is not supported yet.")
            elif isinstance(message, ModelClientStreamingChunkEvent):
                continue
            elif isinstance(message, ToolCallRequestEvent):
                continue
            elif isinstance(message, ToolCallExecutionEvent):
                continue

        return "\n".join(formatted_response)

    def _to_config(self) -> TaskRunnerToolConfig:
        return TaskRunnerToolConfig(agent=self._agent.dump_component())

    @classmethod
    def _from_config(cls, config: TaskRunnerToolConfig) -> Self:
        return cls(
            agent=BaseChatAgent.load_component(config.agent),
        )

    async def save_state(self) -> TaskRunnerToolState:
        return TaskRunnerToolState(task_runner_state=await self._agent.save_state())

    async def load_state(self, state: TaskRunnerToolState) -> None:
        await self._agent.load_state(state.task_runner_state)
