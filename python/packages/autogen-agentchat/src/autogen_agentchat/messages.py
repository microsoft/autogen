from typing import List, Literal

from autogen_core import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult, RequestUsage
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


class BaseMessage(BaseModel):
    """A base message."""

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TextMessage(BaseMessage):
    """A text message."""

    content: str
    """The content of the message."""

    type: Literal["TextMessage"] = "TextMessage"


class MultiModalMessage(BaseMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""

    type: Literal["MultiModalMessage"] = "MultiModalMessage"


class StopMessage(BaseMessage):
    """A message requesting stop of a conversation."""

    content: str
    """The content for the stop message."""

    type: Literal["StopMessage"] = "StopMessage"


class HandoffMessage(BaseMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    content: str
    """The handoff message to the target agent."""

    type: Literal["HandoffMessage"] = "HandoffMessage"


class ToolCallMessage(BaseMessage):
    """A message signaling the use of tools."""

    content: List[FunctionCall]
    """The tool calls."""

    type: Literal["ToolCallMessage"] = "ToolCallMessage"


class ToolCallResultMessage(BaseMessage):
    """A message signaling the results of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""

    type: Literal["ToolCallResultMessage"] = "ToolCallResultMessage"


ChatMessage = Annotated[TextMessage | MultiModalMessage | StopMessage | HandoffMessage, Field(discriminator="type")]
"""Messages for agent-to-agent communication."""


AgentMessage = Annotated[
    TextMessage | MultiModalMessage | StopMessage | HandoffMessage | ToolCallMessage | ToolCallResultMessage,
    Field(discriminator="type"),
]
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
