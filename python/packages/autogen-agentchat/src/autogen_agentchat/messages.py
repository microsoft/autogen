"""
This module defines various message types used for agent-to-agent communication.
Each message type inherits either from the BaseChatMessage class or BaseAgentEvent
class and includes specific fields relevant to the type of message being sent.
"""

from abc import ABC
from typing import List, Literal

from autogen_core import FunctionCall, Image
from autogen_core.models import FunctionExecutionResult, RequestUsage
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


ChatMessage = Annotated[
    TextMessage | MultiModalMessage | StopMessage | ToolCallSummaryMessage | HandoffMessage, Field(discriminator="type")
]
"""Messages for agent-to-agent communication only."""


AgentEvent = Annotated[ToolCallRequestEvent | ToolCallExecutionEvent, Field(discriminator="type")]
"""Events emitted by agents and teams when they work, not used for agent-to-agent communication."""


__all__ = [
    "BaseMessage",
    "TextMessage",
    "MultiModalMessage",
    "StopMessage",
    "HandoffMessage",
    "ToolCallRequestEvent",
    "ToolCallExecutionEvent",
    "ToolCallSummaryMessage",
    "ChatMessage",
    "AgentEvent",
]
