"""
This module defines various message types used for agent-to-agent communication.
Each message type inherits either from the ChatMessage class or BaseAgentEvent
class and includes specific fields relevant to the type of message being sent.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Mapping, TypeVar

from autogen_core import FunctionCall, Image
from autogen_core.memory import MemoryContent
from autogen_core.models import FunctionExecutionResult, LLMMessage, RequestUsage, UserMessage
from pydantic import BaseModel, ConfigDict, computed_field
from typing_extensions import Self


class BaseMessage(BaseModel, ABC):
    """Base class for all message types in AgentChat. This is an abstract class
    with default implementations for serialization and deserialization.

    .. warning::

        If you want to create a new message type, do not inherit from this class.
        Instead, inherit from :class:`ChatMessage` or :class:`AgentEvent`
        to clarify the purpose of the message type.

    """

    @computed_field
    def type(self) -> str:
        """The class name of this message."""
        return self.__class__.__name__

    def dump(self) -> Mapping[str, Any]:
        """Convert the message to a JSON-serializable dictionary.

        The default implementation uses the Pydantic model's `model_dump` method.

        If you want to customize the serialization, override this method.
        """
        return self.model_dump()

    @classmethod
    def load(cls, data: Mapping[str, Any]) -> Self:
        """Create a message from a dictionary of JSON-serializable data.

        The default implementation uses the Pydantic model's `model_validate` method.
        If you want to customize the deserialization, override this method.
        """
        return cls.model_validate(data)


class ChatMessage(BaseMessage, ABC):
    """Base class for chat messages.

    .. note::

        If you want to create a new message type that is used for agent-to-agent
        communication, inherit from this class, or simply use
        :class:`StructuredMessage` if your content type is a subclass of
        Pydantic BaseModel.

    This class is used for messages that are sent between agents in a chat
    conversation. Agents are expected to process the content of the
    message using models and return a response as another :class:`ChatMessage`.
    """

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    metadata: Dict[str, str] = {}
    """Additional metadata about the message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def to_text(self) -> str:
        """Convert the content of the message to a string-only representation
        that can be rendered in the console and inspected by the user or conditions.

        This is not used for creating text-only content for models.
        For :class:`ChatMessage` types, use :meth:`to_model_text` instead."""
        ...

    @abstractmethod
    def to_model_text(self) -> str:
        """Convert the content of the message to text-only representation.
        This is used for creating text-only content for models.

        This is not used for rendering the message in console. For that, use
        :meth:`~BaseMessage.to_text`.

        The difference between this and :meth:`to_model_message` is that this
        is used to construct parts of the a message for the model client,
        while :meth:`to_model_message` is used to create a complete message
        for the model client.
        """
        ...

    @abstractmethod
    def to_model_message(self) -> UserMessage:
        """Convert the message content to a :class:`~autogen_core.models.UserMessage`
        for use with model client, e.g., :class:`~autogen_core.models.ChatCompletionClient`."""
        ...


class TextChatMessage(ChatMessage, ABC):
    """Base class for all text-only :class:`ChatMessage` types.
    It has implementations for :meth:`to_text`, :meth:`to_model_text`,
    and :meth:`to_model_message` methods.

    Inherit from this class if your message content type is a string.
    """

    content: str
    """The content of the message."""

    def to_text(self) -> str:
        return self.content

    def to_model_text(self) -> str:
        return self.content

    def to_model_message(self) -> UserMessage:
        return UserMessage(content=self.content, source=self.source)


class AgentEvent(BaseMessage, ABC):
    """Base class for agent events.

    .. note::

        If you want to create a new message type for signaling observable events
        to user and application, inherit from this class.

    Agent events are used to signal actions and thoughts produced by agents
    and teams to user and applications. They are not used for agent-to-agent
    communication and are not expected to be processed by other agents.

    You should override the :meth:`to_text` method if you want to provide
    a custom rendering of the content.
    """

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    metadata: Dict[str, str] = {}
    """Additional metadata about the message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def to_text(self) -> str:
        """Convert the content of the message to a string-only representation
        that can be rendered in the console and inspected by the user.

        This is not used for creating text-only content for models.
        For :class:`ChatMessage` types, use :meth:`to_model_text` instead."""
        ...


StructuredContentType = TypeVar("StructuredContentType", bound=BaseModel, covariant=True)
"""Type variable for structured content types."""


class StructuredMessage(ChatMessage, Generic[StructuredContentType]):
    """A :class:`ChatMessage` type with an unspecified content type.

    To create a new structured message type, specify the content type
    as a subclass of `Pydantic BaseModel <https://docs.pydantic.dev/latest/concepts/models/>`_.

    .. code-block:: python

        from pydantic import BaseModel
        from autogen_agentchat.messages import StructuredMessage


        class MyMessageContent(BaseModel):
            text: str
            number: int


        message = StructuredMessage[MyMessageContent](
            content=MyMessageContent(text="Hello", number=42),
            source="agent1",
        )

        print(message.to_text())  # {"text": "Hello", "number": 42}

    """

    content: StructuredContentType
    """The content of the message. Must be a subclass of
    `Pydantic BaseModel <https://docs.pydantic.dev/latest/concepts/models/>`_."""

    def to_text(self) -> str:
        return self.content.model_dump_json(indent=2)

    def to_model_text(self) -> str:
        return self.content.model_dump_json()

    def to_model_message(self) -> UserMessage:
        return UserMessage(
            content=self.content.model_dump_json(),
            source=self.source,
        )


class TextMessage(TextChatMessage):
    """A text message with string-only content."""

    ...


class MultiModalMessage(ChatMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""

    def to_model_text(self, image_placeholder: str | None = "[image]") -> str:
        """Convert the content of the message to a string-only representation.
        If an image is present, it will be replaced with the image placeholder
        by default, otherwise it will be a base64 string when set to None.
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

    def to_text(self, iterm: bool = False) -> str:
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

    def to_model_message(self) -> UserMessage:
        return UserMessage(content=self.content, source=self.source)


class StopMessage(TextChatMessage):
    """A message requesting stop of a conversation."""

    ...


class HandoffMessage(TextChatMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    context: List[LLMMessage] = []
    """The model context to be passed to the target agent."""


class ToolCallSummaryMessage(TextChatMessage):
    """A message signaling the summary of tool call results."""

    ...


class ToolCallRequestEvent(AgentEvent):
    """An event signaling a request to use tools."""

    content: List[FunctionCall]
    """The tool calls."""

    def to_text(self) -> str:
        return str(self.content)


class ToolCallExecutionEvent(AgentEvent):
    """An event signaling the execution of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""

    def to_text(self) -> str:
        return str(self.content)


class UserInputRequestedEvent(AgentEvent):
    """An event signaling a that the user proxy has requested user input. Published prior to invoking the input callback."""

    request_id: str
    """Identifier for the user input request."""

    content: Literal[""] = ""
    """Empty content for compat with consumers expecting a content field."""

    def to_text(self) -> str:
        return str(self.content)


class MemoryQueryEvent(AgentEvent):
    """An event signaling the results of memory queries."""

    content: List[MemoryContent]
    """The memory query results."""

    def to_text(self) -> str:
        return str(self.content)


class ModelClientStreamingChunkEvent(AgentEvent):
    """An event signaling a text output chunk from a model client in streaming mode."""

    content: str
    """A string chunk from the model client."""

    def to_text(self) -> str:
        return self.content


class ThoughtEvent(AgentEvent):
    """An event signaling the thought process of a model.
    It is used to communicate the reasoning tokens generated by a reasoning model,
    or the extra text content generated by a function call."""

    content: str
    """The thought process of the model."""

    def to_text(self) -> str:
        return self.content


class MessageFactory:
    """:meta private:

    A factory for creating messages from JSON-serializable dictionaries.

    This is useful for deserializing messages from JSON data.
    """

    def __init__(self) -> None:
        self._message_types: Dict[str, type[AgentEvent | ChatMessage]] = {}
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

    def is_registered(self, message_type: type[AgentEvent | ChatMessage]) -> bool:
        """Check if a message type is registered with the factory."""
        # Get the class name of the message type.
        class_name = message_type.__name__
        # Check if the class name is already registered.
        return class_name in self._message_types

    def register(self, message_type: type[AgentEvent | ChatMessage]) -> None:
        """Register a new message type with the factory."""
        if self.is_registered(message_type):
            raise ValueError(f"Message type {message_type} is already registered.")
        if not issubclass(message_type, ChatMessage) and not issubclass(message_type, AgentEvent):
            raise ValueError(f"Message type {message_type} must be a subclass of ChatMessage or AgentEvent.")
        # Get the class name of the
        class_name = message_type.__name__
        # Check if the class name is already registered.
        # Register the message type.
        self._message_types[class_name] = message_type

    def create(self, data: Mapping[str, Any]) -> AgentEvent | ChatMessage:
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
        assert issubclass(message_class, ChatMessage) or issubclass(message_class, AgentEvent)
        return message_class.load(data)


# For backward compatibility
BaseAgentEvent = AgentEvent
BaseChatMessage = ChatMessage


__all__ = [
    "AgentEvent",
    "BaseMessage",
    "ChatMessage",
    "BaseChatMessage",
    "BaseAgentEvent",
    "AgentEvent",
    "TextChatMessage",
    "ChatMessage",
    "StructuredContentType",
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
