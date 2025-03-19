"""
This module defines various message types used for agent-to-agent communication.
Each message type inherits either from the BaseChatMessage class or BaseAgentEvent
class and includes specific fields relevant to the type of message being sent.
"""

import importlib
from abc import ABC
from typing import Any, Dict, Generic, List, Literal, Self, TypeVar

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

    metadata: Dict[str, str] = {}
    """Additional metadata about the message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseChatMessage(BaseMessage, ABC):
    """Base class for chat messages."""

    pass


class BaseAgentEvent(BaseMessage, ABC):
    """Base class for agent events."""

    pass


ContentType = TypeVar("ContentType", bound=BaseModel, covariant=True)


class StructuredMessage(BaseChatMessage, Generic[ContentType]):
    """A structured message with a specific content type."""

    content: ContentType
    """The content of the message. Must be a subclass of
    `Pydantic BaseModel <https://docs.pydantic.dev/latest/concepts/models/>`_."""

    content_class_path: str | None = None
    """The path to the content class. This is set automatically when the message is created."""

    type: Literal["StructuredMessage"] = "StructuredMessage"

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        module_name = self.content.__class__.__module__
        class_name = self.content.__class__.__qualname__
        self.content_class_path = f"{module_name}.{class_name}"

    def dump(self) -> Dict[str, Any]:
        """Dump the message to a dictionary. This is used for serialization
        and ensures that the content is serialized correctly."""
        data = super().model_dump()
        data["content"] = self.content.model_dump()
        return data

    @classmethod
    def load(cls, obj: Dict[str, Any]) -> Self:
        """Load the message from a dictionary. This is used for deserialization
        and ensures that the content is deserialized correctly."""
        content_class_path = obj["content_class_path"]
        module_name, class_name = content_class_path.rsplit(".", 1)
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(
                f"Could not import module {module_name} when loading content class {class_name} for StructuredMessage. Ensure it is installed."
            ) from e
        if not hasattr(module, class_name):
            raise ValueError(
                f"Could not find class {class_name} in module {module_name} when loading content class for StructuredMessage."
            )
        content_class = getattr(module, class_name)
        if not issubclass(content_class, BaseModel):
            raise ValueError(f"Invalid content class: {content_class}, must be a subclass of BaseModel")
        content = content_class.model_validate(obj["content"])
        instance = super().model_validate(obj)
        instance.content = content  # type: ignore
        instance.content_class_path = content_class_path
        return instance


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


class ThoughtEvent(BaseAgentEvent):
    """An event signaling the thought process of an agent.
    It is used to communicate the reasoning tokens generated by a reasoning model,
    or the extra text content generated by a function call."""

    content: str
    """The thought process."""

    type: Literal["ThoughtEvent"] = "ThoughtEvent"


ChatMessage = Annotated[
    StructuredMessage[BaseModel]
    | TextMessage
    | MultiModalMessage
    | StopMessage
    | ToolCallSummaryMessage
    | HandoffMessage,
    Field(discriminator="type"),
]
"""Messages for agent-to-agent communication only."""


AgentEvent = Annotated[
    ToolCallRequestEvent
    | ToolCallExecutionEvent
    | MemoryQueryEvent
    | UserInputRequestedEvent
    | ModelClientStreamingChunkEvent
    | ThoughtEvent,
    Field(discriminator="type"),
]
"""Events emitted by agents and teams when they work, not used for agent-to-agent communication."""


__all__ = [
    "AgentEvent",
    "BaseMessage",
    "ChatMessage",
    "StructuredMessage",
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
    "ThoughtEvent",
]
