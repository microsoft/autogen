from typing import List

from autogen_core.components import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult, RequestUsage
from pydantic import BaseModel


class BaseMessage(BaseModel):
    """A base message."""

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""


class TextMessage(BaseMessage):
    """A text message."""

    content: str
    """The content of the message."""


class MultiModalMessage(BaseMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""


class StopMessage(BaseMessage):
    """A message requesting stop of a conversation."""

    content: str
    """The content for the stop message."""


class HandoffMessage(BaseMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    content: str
    """The handoff message to the target agent."""


class ResetMessage(BaseMessage):
    """A message requesting reset of the recipient's state in the current conversation."""

    content: str
    """The content for the reset message."""


class ToolCallMessage(BaseMessage):
    """A message signaling the use of tools."""

    content: List[FunctionCall]
    """The tool calls."""


class ToolCallResultMessage(BaseMessage):
    """A message signaling the results of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""


InnerMessage = ToolCallMessage | ToolCallResultMessage
"""Messages for intra-agent monologues."""


ChatMessage = TextMessage | MultiModalMessage | StopMessage | HandoffMessage | ResetMessage
"""Messages for agent-to-agent communication."""


__all__ = [
    "BaseMessage",
    "TextMessage",
    "MultiModalMessage",
    "StopMessage",
    "HandoffMessage",
    "ResetMessage",
    "ToolCallMessage",
    "ToolCallResultMessage",
    "ChatMessage",
]
