"""
This module defines various message types used for agent-to-agent communication.
Each message type inherits either from the BaseChatMessage class or BaseAgentEvent
class and includes specific fields relevant to the type of message being sent.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Mapping, TypeVar

from autogen_core import FunctionCall, Image
from autogen_core.memory import MemoryContent
from autogen_core.models import FunctionExecutionResult, LLMMessage, RequestUsage, UserMessage
from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing_extensions import Annotated


class BaseMessage(BaseModel, ABC):
    """Base class for all message types."""

    content: Any
    """The content of the message."""

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    metadata: Dict[str, str] = {}
    """Additional metadata about the message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def type(self) -> str:
        """Get the class name."""
        return self.__class__.__name__

    @abstractmethod
    def content_to_render(self) -> str:
        """Convert the content of the message to a string-only representation.
        This is used for rendering the message in the UI."""
        ...


class BaseChatMessage(BaseMessage, ABC):
    """Base class for chat messages.

    This class is used for messages that are sent between agents in a chat
    conversation. Agents are expected to use process the content of the
    message using either models or code and return a response as another
    chat message."""

    @abstractmethod
    def content_to_str(self) -> str:
        """Convert the content of the message to a string-only representation.
        This is used for creating a text-only content for models.

        This is not used for rendering the message in the UI. For that, use
        :meth:`content_to_render`.

        The difference between this and :meth:`to_llm_messages` is that this
        is used to construct parts of the a message for the model client,
        while :meth:`to_llm_messages` is used to create complete messages
        for the model client.
        """
        ...

    @abstractmethod
    def to_llm_messages(self) -> List[LLMMessage]:
        """Convert the message to a list of :class:`~autogen_core.models.LLMMessage`
        for use with the model client."""
        ...


class BaseTextChatMessage(BaseChatMessage, ABC):
    """Base class for all text-only chat message types."""

    content: str
    """The content of the message."""

    def content_to_render(self) -> str:
        return self.content

    def content_to_str(self) -> str:
        return self.content

    def to_llm_messages(self) -> List[LLMMessage]:
        return [UserMessage(content=self.content, source=self.source)]


class BaseAgentEvent(BaseMessage, ABC):
    """Base class for agent events.

    Agent events are used to signal actions and thoughts produced by agents
    and teams to user and applications. They are not used for agent-to-agent
    communication and are not expected to be processed by other agents.
    """

    def content_to_render(self) -> str:
        return str(self.content)


StructuredContentType = TypeVar("StructuredContentType", bound=BaseModel, covariant=True)
"""Type variable for structured content types."""


class StructuredMessage(BaseChatMessage, Generic[StructuredContentType]):
    """A structured message with a specific content type."""

    content: StructuredContentType
    """The content of the message. Must be a subclass of
    `Pydantic BaseModel <https://docs.pydantic.dev/latest/concepts/models/>`_."""

    def content_to_render(self) -> str:
        return self.content.model_dump_json(indent=2)

    def content_to_str(self) -> str:
        return self.content.model_dump_json()

    def to_llm_messages(self) -> List[LLMMessage]:
        return [
            UserMessage(
                content=self.content.model_dump_json(),
                source=self.source,
            )
        ]


class TextMessage(BaseTextChatMessage):
    """A text message with string-only content."""

    ...


class MultiModalMessage(BaseChatMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""

    def content_to_str(self, image_placeholder: str | None = None) -> str:
        """Convert the content of the message to a string-only representation.
        If an image is present, it will be replaced with the image placeholder
        if provided, otherwise it will be a base64 string.
        """
        text = ""
        for c in self.content:
            if isinstance(c, str):
                text += c
            elif isinstance(c, Image):
                if image_placeholder is not None:
                    text += f" {image_placeholder}"
                else:
                    text += f" {c.to_base64()}"
        return text

    def content_to_render(self, iterm: bool = False) -> str:
        result: List[str] = []
        for c in self.content:
            if isinstance(c, str):
                result.append(c)
            else:
                if iterm:
                    # iTerm2 image rendering protocol: https://iterm2.com/documentation-images.html
                    image_data = c.to_base64()
                    result.append(f"\033]1337;File=inline=1:{image_data}\a\n")
                else:
                    result.append("<image>")
        return "\n".join(result)

    def to_llm_messages(self) -> List[LLMMessage]:
        return [UserMessage(content=self.content, source=self.source)]


class StopMessage(BaseTextChatMessage):
    """A message requesting stop of a conversation."""

    ...


class HandoffMessage(BaseTextChatMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    context: List[LLMMessage] = []
    """The model context to be passed to the target agent."""

    def to_llm_messages(self) -> List[LLMMessage]:
        return [*self.context, UserMessage(content=self.content, source=self.source)]


class ToolCallSummaryMessage(BaseTextChatMessage):
    """A message signaling the summary of tool call results."""

    ...


class ToolCallRequestEvent(BaseAgentEvent):
    """An event signaling a request to use tools."""

    content: List[FunctionCall]
    """The tool calls."""


class ToolCallExecutionEvent(BaseAgentEvent):
    """An event signaling the execution of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""


class UserInputRequestedEvent(BaseAgentEvent):
    """An event signaling a that the user proxy has requested user input. Published prior to invoking the input callback."""

    request_id: str
    """Identifier for the user input request."""

    content: Literal[""] = ""
    """Empty content for compat with consumers expecting a content field."""


class MemoryQueryEvent(BaseAgentEvent):
    """An event signaling the results of memory queries."""

    content: List[MemoryContent]
    """The memory query results."""


class ModelClientStreamingChunkEvent(BaseAgentEvent):
    """An event signaling a text output chunk from a model client in streaming mode."""

    content: str
    """A string chunk from the model client."""


class ThoughtEvent(BaseAgentEvent):
    """An event signaling the thought process of a model.
    It is used to communicate the reasoning tokens generated by a reasoning model,
    or the extra text content generated by a function call."""

    content: str
    """The thought process of the model."""


ChatMessage = Annotated[
    TextMessage | MultiModalMessage | StopMessage | ToolCallSummaryMessage | HandoffMessage,
    Field(discriminator="type"),
]
"""Builtin chat message types for agent-to-agent communication only."""


AgentEvent = Annotated[
    ToolCallRequestEvent
    | ToolCallExecutionEvent
    | MemoryQueryEvent
    | UserInputRequestedEvent
    | ModelClientStreamingChunkEvent
    | ThoughtEvent,
    Field(discriminator="type"),
]
"""Builtin agent events emitted by agents and teams when they work, not used for agent-to-agent communication."""


class MessageFactory:
    """A factory for creating messages from JSON-serializable dictionaries.

    This is useful for deserializing messages from JSON data.
    """

    def __init__(self) -> None:
        self._message_types: Dict[str, type[BaseMessage]] = {}
        # Register all message types.
        self._message_types[TextMessage.__name__] = TextMessage
        self._message_types[MultiModalMessage.__name__] = MultiModalMessage
        self._message_types[StopMessage.__name__] = StopMessage
        self._message_types[ToolCallSummaryMessage.__name__] = ToolCallSummaryMessage
        self._message_types[HandoffMessage.__name__] = HandoffMessage
        self._message_types[ToolCallRequestEvent.__name__] = ToolCallRequestEvent
        self._message_types[ToolCallExecutionEvent.__name__] = ToolCallExecutionEvent
        self._message_types[MemoryQueryEvent.__name__] = MemoryQueryEvent
        self._message_types[UserInputRequestedEvent.__name__] = UserInputRequestedEvent
        self._message_types[ModelClientStreamingChunkEvent.__name__] = ModelClientStreamingChunkEvent
        self._message_types[ThoughtEvent.__name__] = ThoughtEvent

    def is_registered(self, message_type: type[BaseMessage]) -> bool:
        """Check if a message type is registered with the factory."""
        # Get the class name of the message type.
        class_name = message_type.__name__
        # Check if the class name is already registered.
        return class_name in self._message_types

    def register(self, message_type: type[BaseMessage]) -> None:
        """Register a new message type with the factory."""
        if self.is_registered(message_type):
            raise ValueError(f"Message type {message_type} is already registered.")
        if not issubclass(message_type, BaseMessage):
            raise ValueError(f"Message type {message_type} must be a subclass of BaseMessage.")
        # Get the class name of the
        class_name = message_type.__name__
        # Check if the class name is already registered.
        # Register the message type.
        self._message_types[class_name] = message_type

    def create(self, data: Mapping[str, Any]) -> BaseMessage:
        """Create a message from a dictionary of JSON-serializable data."""
        # Get the type of the message from the dictionary.
        message_type = data.get("type")
        if message_type not in self._message_types:
            raise ValueError(f"Unknown message type: {message_type}")
        if not isinstance(message_type, str):
            raise ValueError(f"Message type must be a string, got {type(message_type)}")

        # Get the class for the message type.
        message_class = self._message_types[message_type]

        # Create an instance of the message class.
        assert issubclass(message_class, BaseMessage)
        return message_class.model_validate(data)


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
    "MessageFactory",
]
