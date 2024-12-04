from typing import List

from autogen_core import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult, RequestUsage
from pydantic import BaseModel, ConfigDict


class BaseMessage(BaseModel):
    """A base message."""

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: str = "BaseMessage"


class TextMessage(BaseMessage):
    """A text message."""

    content: str
    """The content of the message."""

    type: str = "TextMessage"


class MultiModalMessage(BaseMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""

    type: str = "MultiModalMessage"


class StopMessage(BaseMessage):
    """A message requesting stop of a conversation."""

    content: str
    """The content for the stop message."""

    type: str = "StopMessage"


class HandoffMessage(BaseMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    content: str
    """The handoff message to the target agent."""

    type: str = "HandoffMessage"


class ToolCallMessage(BaseMessage):
    """A message signaling the use of tools."""

    content: List[FunctionCall]
    """The tool calls."""

    type: str = "ToolCallMessage"


class ToolCallResultMessage(BaseMessage):
    """A message signaling the results of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""

    type: str = "ToolCallResultMessage"


ChatMessage = TextMessage | MultiModalMessage | StopMessage | HandoffMessage
"""Messages for agent-to-agent communication."""


AgentMessage = TextMessage | MultiModalMessage | StopMessage | HandoffMessage | ToolCallMessage | ToolCallResultMessage
"""All message types."""


__all__ = [
    "BaseMessage",
    "TextMessage",
    "MultiModalMessage",
    "StopMessage",
    "HandoffMessage",
    "ToolCallMessage",
    "ToolCallResultMessage",
    "ChatMessage",
    "AgentMessage",
]
