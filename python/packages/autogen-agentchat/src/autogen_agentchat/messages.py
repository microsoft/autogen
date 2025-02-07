"""
This module defines various message types used for agent-to-agent communication.
Each message type inherits either from the BaseChatMessage class or BaseAgentEvent
class and includes specific fields relevant to the type of message being sent.
"""

from abc import ABC
from typing import List, Literal

from autogen_core import FunctionCall, Image
from autogen_core.memory import MemoryContent
from autogen_core.models import FunctionExecutionResult, LLMMessage, RequestUsage
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


class BaseMessage(BaseModel, ABC):
    """Base class for all message types."""

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseChatMessage(BaseMessage, ABC):
    """Base class for chat messages."""

    pass


class BaseAgentEvent(BaseMessage, ABC):
    """Base class for agent events."""

    pass


class TextMessage(BaseChatMessage):
    """A text message."""

    content: str
    """The content of the message."""

    type: Literal["TextMessage"] = "TextMessage"


class MultiModalMessage(BaseChatMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""

    type: Literal["MultiModalMessage"] = "MultiModalMessage"


class StopMessage(BaseChatMessage):
    """A message requesting stop of a conversation."""

    content: str
    """The content for the stop message."""

    type: Literal["StopMessage"] = "StopMessage"


class HandoffMessage(BaseChatMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    content: str
    """The handoff message to the target agent."""

    context: List[LLMMessage] = []
    """The model context to be passed to the target agent."""

    type: Literal["HandoffMessage"] = "HandoffMessage"


class ToolCallRequestEvent(BaseAgentEvent):
    """An event signaling a request to use tools."""

    content: List[FunctionCall]
    """The tool calls."""

    type: Literal["ToolCallRequestEvent"] = "ToolCallRequestEvent"


class ToolCallExecutionEvent(BaseAgentEvent):
    """An event signaling the execution of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""

    type: Literal["ToolCallExecutionEvent"] = "ToolCallExecutionEvent"


class ToolCallSummaryMessage(BaseChatMessage):
    """A message signaling the summary of tool call results."""

    content: str
    """Summary of the the tool call results."""

    type: Literal["ToolCallSummaryMessage"] = "ToolCallSummaryMessage"


class UserInputRequestedEvent(BaseAgentEvent):
    """An event signaling a that the user proxy has requested user input. Published prior to invoking the input callback."""

    request_id: str
    """Identifier for the user input request."""

    content: Literal[""] = ""
    """Empty content for compat with consumers expecting a content field."""

    type: Literal["UserInputRequestedEvent"] = "UserInputRequestedEvent"


class MemoryQueryEvent(BaseAgentEvent):
    """An event signaling the results of memory queries."""

    content: List[MemoryContent]
    """The memory query results."""

    type: Literal["MemoryQueryEvent"] = "MemoryQueryEvent"


class ModelClientStreamingChunkEvent(BaseAgentEvent):
    """An event signaling a text output chunk from a model client in streaming mode."""

    content: str
    """The partial text chunk."""

    type: Literal["ModelClientStreamingChunkEvent"] = "ModelClientStreamingChunkEvent"


ChatMessage = Annotated[
    TextMessage | MultiModalMessage | StopMessage | ToolCallSummaryMessage | HandoffMessage, Field(discriminator="type")
]
"""Messages for agent-to-agent communication only."""


AgentEvent = Annotated[
    ToolCallRequestEvent
    | ToolCallExecutionEvent
    | MemoryQueryEvent
    | UserInputRequestedEvent
    | ModelClientStreamingChunkEvent,
    Field(discriminator="type"),
]
"""Events emitted by agents and teams when they work, not used for agent-to-agent communication."""


__all__ = [
    "AgentEvent",
    "BaseMessage",
    "ChatMessage",
    "HandoffMessage",
    "MultiModalMessage",
    "StopMessage",
    "TextMessage",
    "ToolCallExecutionEvent",
    "ToolCallRequestEvent",
    "ToolCallSummaryMessage",
    "MemoryQueryEvent",
    "UserInputRequestedEvent",
    "ModelClientStreamingChunkEvent",
]
