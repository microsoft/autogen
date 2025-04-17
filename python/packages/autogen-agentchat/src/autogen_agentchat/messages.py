"""
This module defines various message types used for agent-to-agent communication.
Each message type inherits either from the BaseChatMessage class or BaseAgentEvent
class and includes specific fields relevant to the type of message being sent.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Mapping, Optional, Type, TypeVar

from autogen_core import Component, ComponentBase, FunctionCall, Image
from autogen_core.code_executor import CodeBlock, CodeResult
from autogen_core.memory import MemoryContent
from autogen_core.models import (
    FunctionExecutionResult,
    LLMMessage,
    RequestUsage,
    UserMessage,
)
from autogen_core.utils import schema_to_pydantic_model
from pydantic import BaseModel, Field, computed_field
from typing_extensions import Annotated, Self


class BaseMessage(BaseModel, ABC):
    """Abstract base class for all message types in AgentChat.

    .. warning::

        If you want to create a new message type, do not inherit from this class.
        Instead, inherit from :class:`BaseChatMessage` or :class:`BaseAgentEvent`
        to clarify the purpose of the message type.

    """

    @abstractmethod
    def to_text(self) -> str:
        """Convert the message content to a string-only representation
        that can be rendered in the console and inspected by the user or conditions.
        This is not used for creating text-only content for models.
        For :class:`BaseChatMessage` types, use :meth:`to_model_text` instead."""
        ...

    def dump(self) -> Mapping[str, Any]:
        """Convert the message to a JSON-serializable dictionary.

        The default implementation uses the Pydantic model's
        :meth:`model_dump` method to convert the message to a dictionary.
        Override this method if you want to customize the serialization
        process or add additional fields to the output.
        """
        return self.model_dump()

    @classmethod
    def load(cls, data: Mapping[str, Any]) -> Self:
        """Create a message from a dictionary of JSON-serializable data.

        The default implementation uses the Pydantic model's
        :meth:`model_validate` method to create the message from the data.
        Override this method if you want to customize the deserialization
        process or add additional fields to the input data."""
        return cls.model_validate(data)


class BaseChatMessage(BaseMessage, ABC):
    """Abstract base class for chat messages.

    .. note::

        If you want to create a new message type that is used for agent-to-agent
        communication, inherit from this class, or simply use
        :class:`StructuredMessage` if your content type is a subclass of
        Pydantic BaseModel.

    This class is used for messages that are sent between agents in a chat
    conversation. Agents are expected to process the content of the
    message using models and return a response as another :class:`BaseChatMessage`.
    """

    source: str
    """The name of the agent that sent this message."""

    models_usage: RequestUsage | None = None
    """The model client usage incurred when producing this message."""

    metadata: Dict[str, str] = {}
    """Additional metadata about the message."""

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
        for use with model client, e.g., :class:`~autogen_core.models.ChatCompletionClient`.
        """
        ...


class BaseTextChatMessage(BaseChatMessage, ABC):
    """Base class for all text-only :class:`BaseChatMessage` types.
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


class BaseAgentEvent(BaseMessage, ABC):
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


StructuredContentType = TypeVar("StructuredContentType", bound=BaseModel, covariant=True)
"""Type variable for structured content types."""


class StructuredMessage(BaseChatMessage, Generic[StructuredContentType]):
    """A :class:`BaseChatMessage` type with an unspecified content type.

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

    .. code-block:: python

        from pydantic import BaseModel
        from autogen_agentchat.messages import StructuredMessage


        class MyMessageContent(BaseModel):
            text: str
            number: int


        message = StructuredMessage[MyMessageContent](
            content=MyMessageContent(text="Hello", number=42),
            source="agent",
            format_string="Hello, {text} {number}!",
        )

        print(message.to_text())  # Hello, agent 42!

    """

    content: StructuredContentType
    """The content of the message. Must be a subclass of
    `Pydantic BaseModel <https://docs.pydantic.dev/latest/concepts/models/>`_."""

    format_string: Optional[str] = None
    """(Experimental) An optional format string to render the content into a human-readable format.
    The format string can use the fields of the content model as placeholders.
    For example, if the content model has a field `name`, you can use
    `{name}` in the format string to include the value of that field.
    The format string is used in the :meth:`to_text` method to create a
    human-readable representation of the message.
    This setting is experimental and will change in the future.
    """

    @computed_field
    def type(self) -> str:
        return self.__class__.__name__

    def to_text(self) -> str:
        if self.format_string is not None:
            return self.format_string.format(**self.content.model_dump())
        else:
            return self.content.model_dump_json()

    def to_model_text(self) -> str:
        if self.format_string is not None:
            return self.format_string.format(**self.content.model_dump())
        else:
            return self.content.model_dump_json()

    def to_model_message(self) -> UserMessage:
        return UserMessage(
            content=self.content.model_dump_json(),
            source=self.source,
        )


class StructureMessageConfig(BaseModel):
    """The declarative configuration for the structured output."""

    json_schema: Dict[str, Any]
    format_string: Optional[str] = None
    content_model_name: str


class StructuredMessageFactory(ComponentBase[StructureMessageConfig], Component[StructureMessageConfig]):
    """:meta private:

    A component that creates structured chat messages from Pydantic models or JSON schemas.

    This component helps you generate strongly-typed chat messages with content defined using a Pydantic model.
    It can be used in declarative workflows where message structure must be validated, formatted, and serialized.

    You can initialize the component directly using a `BaseModel` subclass, or dynamically from a configuration
    object (e.g., loaded from disk or a database).

    ### Example 1: Create from a Pydantic Model

    .. code-block:: python

        from pydantic import BaseModel
        from autogen_agentchat.messages import StructuredMessageFactory


        class TestContent(BaseModel):
            field1: str
            field2: int


        format_string = "This is a string {field1} and this is an int {field2}"
        sm_component = StructuredMessageFactory(input_model=TestContent, format_string=format_string)

        message = sm_component.StructuredMessage(
            source="test_agent", content=TestContent(field1="Hello", field2=42), format_string=format_string
        )

        print(message.to_model_text())  # Output: This is a string Hello and this is an int 42

        config = sm_component.dump_component()

        s_m_dyn = StructuredMessageFactory.load_component(config)
        message = s_m_dyn.StructuredMessage(
            source="test_agent",
            content=s_m_dyn.ContentModel(field1="dyn agent", field2=43),
            format_string=s_m_dyn.format_string,
        )
        print(type(message))  # StructuredMessage[GeneratedModel]
        print(message.to_model_text())  # Output: This is a string dyn agent and this is an int 43

    Attributes:
        component_config_schema (StructureMessageConfig): Defines the configuration structure for this component.
        component_provider_override (str): Path used to reference this component in external tooling.
        component_type (str): Identifier used for categorization (e.g., "structured_message").

    Raises:
        ValueError: If neither `json_schema` nor `input_model` is provided.

    Args:
        json_schema (Optional[str]): JSON schema to dynamically create a Pydantic model.
        input_model (Optional[Type[BaseModel]]): A subclass of `BaseModel` that defines the expected message structure.
        format_string (Optional[str]): Optional string to render content into a human-readable format.
        content_model_name (Optional[str]): Optional name for the generated Pydantic model.
    """

    component_config_schema = StructureMessageConfig
    component_provider_override = "autogen_agentchat.messages.StructuredMessageFactory"
    component_type = "structured_message"

    def __init__(
        self,
        json_schema: Optional[Dict[str, Any]] = None,
        input_model: Optional[Type[BaseModel]] = None,
        format_string: Optional[str] = None,
        content_model_name: Optional[str] = None,
    ) -> None:
        self.format_string = format_string

        if json_schema:
            self.ContentModel = schema_to_pydantic_model(
                json_schema, model_name=content_model_name or "GeneratedContentModel"
            )
        elif input_model:
            self.ContentModel = input_model
        else:
            raise ValueError("Either `json_schema` or `input_model` must be provided.")

        self.StructuredMessage = StructuredMessage[self.ContentModel]  # type: ignore[name-defined]

    def _to_config(self) -> StructureMessageConfig:
        return StructureMessageConfig(
            json_schema=self.ContentModel.model_json_schema(),
            format_string=self.format_string,
            content_model_name=self.ContentModel.__name__,
        )

    @classmethod
    def _from_config(cls, config: StructureMessageConfig) -> "StructuredMessageFactory":
        return cls(
            json_schema=config.json_schema,
            format_string=config.format_string,
            content_model_name=config.content_model_name,
        )


class TextMessage(BaseTextChatMessage):
    """A text message with string-only content."""

    type: Literal["TextMessage"] = "TextMessage"


class MultiModalMessage(BaseChatMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""

    type: Literal["MultiModalMessage"] = "MultiModalMessage"

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


class StopMessage(BaseTextChatMessage):
    """A message requesting stop of a conversation."""

    type: Literal["StopMessage"] = "StopMessage"


class HandoffMessage(BaseTextChatMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    context: List[LLMMessage] = []
    """The model context to be passed to the target agent."""

    type: Literal["HandoffMessage"] = "HandoffMessage"


class ToolCallSummaryMessage(BaseTextChatMessage):
    """A message signaling the summary of tool call results."""

    type: Literal["ToolCallSummaryMessage"] = "ToolCallSummaryMessage"


class ToolCallRequestEvent(BaseAgentEvent):
    """An event signaling a request to use tools."""

    content: List[FunctionCall]
    """The tool calls."""

    type: Literal["ToolCallRequestEvent"] = "ToolCallRequestEvent"

    def to_text(self) -> str:
        return str(self.content)


class CodeGenerationEvent(BaseAgentEvent):
    """An event signaling code generation for execution."""

    content: str
    "The complete content as string."

    type: Literal["CodeGenerationEvent"] = "CodeGenerationEvent"

    code_blocks: List[CodeBlock]

    def to_text(self) -> str:
        return self.content


class CodeExecutionEvent(BaseAgentEvent):
    type: Literal["CodeExecutionEvent"] = "CodeExecutionEvent"
    result: CodeResult

    def to_text(self) -> str:
        return self.result.output


class ToolCallExecutionEvent(BaseAgentEvent):
    """An event signaling the execution of tool calls."""

    content: List[FunctionExecutionResult]
    """The tool call results."""

    type: Literal["ToolCallExecutionEvent"] = "ToolCallExecutionEvent"

    def to_text(self) -> str:
        return str(self.content)


class UserInputRequestedEvent(BaseAgentEvent):
    """An event signaling a that the user proxy has requested user input. Published prior to invoking the input callback."""

    request_id: str
    """Identifier for the user input request."""

    content: Literal[""] = ""
    """Empty content for compat with consumers expecting a content field."""

    type: Literal["UserInputRequestedEvent"] = "UserInputRequestedEvent"

    def to_text(self) -> str:
        return str(self.content)


class MemoryQueryEvent(BaseAgentEvent):
    """An event signaling the results of memory queries."""

    content: List[MemoryContent]
    """The memory query results."""

    type: Literal["MemoryQueryEvent"] = "MemoryQueryEvent"

    def to_text(self) -> str:
        return str(self.content)


class ModelClientStreamingChunkEvent(BaseAgentEvent):
    """An event signaling a text output chunk from a model client in streaming mode."""

    content: str
    """A string chunk from the model client."""

    type: Literal["ModelClientStreamingChunkEvent"] = "ModelClientStreamingChunkEvent"

    def to_text(self) -> str:
        return self.content


class ThoughtEvent(BaseAgentEvent):
    """An event signaling the thought process of a model.
    It is used to communicate the reasoning tokens generated by a reasoning model,
    or the extra text content generated by a function call."""

    content: str
    """The thought process of the model."""

    type: Literal["ThoughtEvent"] = "ThoughtEvent"

    def to_text(self) -> str:
        return self.content


class SelectSpeakerEvent(BaseAgentEvent):
    """An event signaling the selection of speakers for a conversation."""

    content: List[str]
    """The names of the selected speakers."""

    type: Literal["SelectSpeakerEvent"] = "SelectSpeakerEvent"

    def to_text(self) -> str:
        return str(self.content)


class MessageFactory:
    """:meta private:

    A factory for creating messages from JSON-serializable dictionaries.

    This is useful for deserializing messages from JSON data.
    """

    def __init__(self) -> None:
        self._message_types: Dict[str, type[BaseAgentEvent | BaseChatMessage]] = {}
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
        self._message_types[SelectSpeakerEvent.__name__] = SelectSpeakerEvent
        self._message_types[CodeGenerationEvent.__name__] = CodeGenerationEvent
        self._message_types[CodeExecutionEvent.__name__] = CodeExecutionEvent

    def is_registered(self, message_type: type[BaseAgentEvent | BaseChatMessage]) -> bool:
        """Check if a message type is registered with the factory."""
        # Get the class name of the message type.
        class_name = message_type.__name__
        # Check if the class name is already registered.
        return class_name in self._message_types

    def register(self, message_type: type[BaseAgentEvent | BaseChatMessage]) -> None:
        """Register a new message type with the factory."""
        if self.is_registered(message_type):
            raise ValueError(f"Message type {message_type} is already registered.")
        if not issubclass(message_type, BaseChatMessage) and not issubclass(message_type, BaseAgentEvent):
            raise ValueError(f"Message type {message_type} must be a subclass of BaseChatMessage or BaseAgentEvent.")
        # Get the class name of the
        class_name = message_type.__name__
        # Check if the class name is already registered.
        # Register the message type.
        self._message_types[class_name] = message_type

    def create(self, data: Mapping[str, Any]) -> BaseAgentEvent | BaseChatMessage:
        """Create a message from a dictionary of JSON-serializable data."""
        # Get the type of the message from the dictionary.
        message_type = data.get("type")
        if message_type is None:
            raise ValueError("Field 'type' is required in the message data to recover the message type.")
        if message_type not in self._message_types:
            raise ValueError(f"Unknown message type: {message_type}")
        if not isinstance(message_type, str):
            raise ValueError(f"Message type must be a string, got {type(message_type)}")

        # Get the class for the message type.
        message_class = self._message_types[message_type]

        # Create an instance of the message class.
        assert issubclass(message_class, BaseChatMessage) or issubclass(message_class, BaseAgentEvent)
        return message_class.load(data)


ChatMessage = Annotated[
    TextMessage | MultiModalMessage | StopMessage | ToolCallSummaryMessage | HandoffMessage,
    Field(discriminator="type"),
]
"""The union type of all built-in concrete subclasses of :class:`BaseChatMessage`.
It does not include :class:`StructuredMessage` types."""

AgentEvent = Annotated[
    ToolCallRequestEvent
    | ToolCallExecutionEvent
    | MemoryQueryEvent
    | UserInputRequestedEvent
    | ModelClientStreamingChunkEvent
    | ThoughtEvent
    | SelectSpeakerEvent
    | CodeGenerationEvent
    | CodeExecutionEvent,
    Field(discriminator="type"),
]
"""The union type of all built-in concrete subclasses of :class:`BaseAgentEvent`."""

__all__ = [
    "AgentEvent",
    "BaseMessage",
    "ChatMessage",
    "BaseChatMessage",
    "BaseAgentEvent",
    "BaseTextChatMessage",
    "StructuredContentType",
    "StructuredMessage",
    "StructuredMessageFactory",
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
    "SelectSpeakerEvent",
    "MessageFactory",
    "CodeGenerationEvent",
    "CodeExecutionEvent",
]
