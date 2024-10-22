from typing import List

from autogen_core.components import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult
from pydantic import BaseModel


class BaseMessage(BaseModel):
    """A base message."""

    source: str
    """The name of the agent that sent this message."""


class TextMessage(BaseMessage):
    """A text message."""

    content: str
    """The content of the message."""


class MultiModalMessage(BaseMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""


class ToolCallMessage(BaseMessage):
    """A message containing a list of function calls."""

    content: List[FunctionCall]
    """The list of function calls."""


class ToolCallResultMessage(BaseMessage):
    """A message containing the results of function calls."""

    content: List[FunctionExecutionResult]
    """The list of function execution results."""


class StopMessage(BaseMessage):
    """A message requesting stop of a conversation."""

    content: str
    """The content for the stop message."""


ChatMessage = TextMessage | MultiModalMessage | StopMessage | ToolCallMessage | ToolCallResultMessage
"""A message used by agents in a team."""


__all__ = [
    "BaseMessage",
    "TextMessage",
    "MultiModalMessage",
    "ToolCallMessage",
    "ToolCallResultMessage",
    "StopMessage",
    "ChatMessage",
]
