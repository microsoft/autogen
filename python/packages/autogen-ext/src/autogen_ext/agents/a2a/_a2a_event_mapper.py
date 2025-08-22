import base64
import json

from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StructuredMessage,
    StructuredMessageFactory,
    TextMessage,
)
from autogen_core import ComponentBase, Image
from pydantic import BaseModel
from slugify import slugify
from typing_extensions import List, Self

from a2a.types import AgentCard, Artifact, DataPart, FilePart, FileWithBytes, FileWithUri, Message, Role, TextPart


def convert_file_to_image(file_part: FilePart) -> Image:
    """Convert a FilePart to an AutoGen Image object.

    Args:
        file_part (FilePart): The file part containing image data

    Returns:
        Image: The converted AutoGen Image object

    Raises:
        ValueError: If the file type is not supported
    """
    if isinstance(file_part.file, FileWithBytes):
        return Image.from_base64(file_part.file.bytes)
    elif isinstance(file_part.file, FileWithUri):
        return Image.from_uri(file_part.file.uri)
    else:
        raise ValueError(f"Unsupported file type: {type(file_part.file)}")


def convert_file_to_str(file_part: FilePart) -> str:
    """Convert a FilePart to a string.

    Args:
        file_part (FilePart): The file part to convert

    Returns:
        str: The string representation of the file content

    Raises:
        ValueError: If the file type is not supported
    """
    if isinstance(file_part.file, FileWithBytes):
        return base64.b64decode(file_part.file.bytes).decode(encoding="utf-8")
    elif isinstance(file_part.file, FileWithUri):
        return file_part.file.uri
    else:
        raise ValueError(f"Unsupported file type: {type(file_part.file)}")


def handle_file_part(file_part: FilePart) -> Image | str:
    """Handle a FilePart by attempting to convert it to either an Image or string.

    This function first tries to convert the file part to an Image object. If that fails,
    it falls back to converting it to a string representation.

    Args:
        file_part (FilePart): The file part to handle

    Returns:
        Image | str: Either an AutoGen Image object or a string representation of the file

    Example:
        ```python
        # For an image file
        image_part = FilePart(file=FileWithBytes(bytes=image_data))
        result = handle_file_part(image_part)  # Returns Image

        # For a text file
        text_part = FilePart(file=FileWithBytes(bytes=text_data))
        result = handle_file_part(text_part)  # Returns str
        ```
    """
    try:
        return convert_file_to_image(file_part)
    except Exception:
        # If conversion to Image fails, try converting to string
        return convert_file_to_str(file_part)


class A2aEventMapperConfig(BaseModel):
    agent_name: str
    output_content_type: type[BaseModel] | None = None
    output_content_type_format: str | None = None


class A2aEventMapper(BaseModel, ComponentBase[A2aEventMapperConfig]):
    """A2aEventMapper handles conversion between A2A messages and AutoGen chat messages.

    This class provides functionality to:
        - Convert A2A messages to AutoGen chat messages
        - Handle different types of message parts (text, data, files)
        - Support structured message formats
        - Process artifacts and streaming events

    Args:
        agent_name (str): Name of the agent, used as source in generated messages
        output_content_type (type[BaseModel] | None): Optional Pydantic model for structured output
        output_content_type_format (str | None): Optional format string for structured messages

    Example:
        Basic usage:
        ```python
        mapper = A2aEventMapper(agent_name="food_agent")
        chat_message = mapper.handle_message(a2a_message)
        ```

        With structured output:
        ```python
        class RecipeResponse(BaseModel):
            name: str
            ingredients: list[str]


        mapper = A2aEventMapper(
            agent_name="recipe_agent",
            output_content_type=RecipeResponse,
            output_content_type_format="Recipe for {name}",
        )
        ```
    """

    def __init__(
        self,
        agent_name: str,
        output_content_type: type[BaseModel] | None = None,
        output_content_type_format: str | None = None,
    ):
        super().__init__()
        self._config = A2aEventMapperConfig(
            agent_name=agent_name,
            output_content_type=output_content_type,
            output_content_type_format=output_content_type_format,
        )
        self._agent_name = slugify(agent_name)
        self._output_content_type = output_content_type
        self._format_string = output_content_type_format
        self._structured_message_factory: StructuredMessageFactory | None = None
        if output_content_type is not None:
            self._structured_message_factory = StructuredMessageFactory(
                input_model=output_content_type, format_string=output_content_type_format
            )

    def handle_message(self, message: Message) -> BaseChatMessage | None:
        """Convert an A2A message to an AutoGen chat message.

        This method handles different types of message parts and converts them into appropriate
        AutoGen message types based on their content.

        Args:
            message (Message): The A2A message to convert

        Returns:
            BaseChatMessage | None: The converted AutoGen message, or None for user messages
                - TextMessage: For messages containing only text parts
                - StructuredMessage: For data parts when output_content_type is specified
                - MultiModalMessage: For messages with mixed content types or files

        Example:
            ```python
            # Text message
            message = Message(parts=[Part(root=TextPart(text="Hello"))])
            chat_msg = mapper.handle_message(message)  # Returns TextMessage

            # Data message with structured output
            data_msg = Message(parts=[Part(root=DataPart(data={"name": "Pizza"}))])
            chat_msg = mapper.handle_message(data_msg)  # Returns StructuredMessage

            # Mixed content
            mixed_msg = Message(parts=[Part(root=TextPart(text="Recipe")), Part(root=FilePart(file=image_file))])
            chat_msg = mapper.handle_message(mixed_msg)  # Returns MultiModalMessage
            ```
        """
        if message.role == Role.user:
            # User messages are not deserialized, they are just passed through
            return None

        if not message.parts or len(message.parts) == 0:
            return None

        is_all_text = all(isinstance(part.root, TextPart) for part in message.parts)
        if is_all_text:
            return TextMessage(
                content="\n".join(part.root.text for part in message.parts),
                source=self._agent_name,
                metadata=message.metadata or dict(),
            )

        is_only_data = all(isinstance(part.root, DataPart) for part in message.parts) and len(message.parts) == 1
        if is_only_data:
            if self._output_content_type is not None:
                content = self._output_content_type.model_validate_json(json.dumps(message.parts[0].root.data))
                return StructuredMessage(
                    content=content,
                    source=self._agent_name,
                    format_string=self._format_string,
                    metadata=message.metadata or dict(),
                )
        contents: List[str | Image] = []
        for part in message.parts:
            if isinstance(part.root, TextPart):
                contents.append(part.root.text)
            elif isinstance(part.root, DataPart):
                contents.append(json.dumps(part.root.data))
            elif isinstance(part.root, FilePart):
                contents.append(handle_file_part(part.root))
            else:
                raise ValueError(f"Unsupported part type: {type(part.root)}")
        return MultiModalMessage(source=self._agent_name, content=contents, metadata=message.metadata or dict())

    def handle_artifact(self, artifact: Artifact) -> BaseAgentEvent | BaseChatMessage | None:
        """Convert an A2A artifact to an AutoGen event or message.

        This method processes artifacts from A2A protocol and converts them into appropriate
        AutoGen events or messages. It's particularly useful for handling streaming content
        and file-based artifacts.

        Args:
            artifact (Artifact): The A2A artifact to convert

        Returns:
            BaseAgentEvent | BaseChatMessage | None: The converted AutoGen event/message
                - ModelClientStreamingChunkEvent: For text/data streaming artifacts
                - MultiModalMessage: For artifacts containing files
                - None: If the artifact has no parts

        Example:
            ```python
            # Streaming text artifact
            artifact = Artifact(parts=[Part(root=TextPart(text="Processing..."))])
            event = mapper.handle_artifact(artifact)  # Returns ModelClientStreamingChunkEvent

            # File artifact
            artifact = Artifact(parts=[Part(root=FilePart(file=image_file))])
            msg = mapper.handle_artifact(artifact)  # Returns MultiModalMessage
            ```
        """
        if not artifact.parts or len(artifact.parts) == 0:
            return None

        has_file_parts = any(isinstance(part.root, FilePart) for part in artifact.parts)
        if has_file_parts:
            return self.handle_message(
                Message(
                    parts=artifact.parts,
                    role=Role.agent,
                    message_id=artifact.artifactId,
                    metadata=artifact.metadata or dict(),
                )
            )
        content = []

        for part in artifact.parts:
            if isinstance(part.root, TextPart):
                content.append(part.root.text)
            elif isinstance(part.root, DataPart):
                content.append(json.dumps(part.root.data))
            else:
                raise ValueError(f"Unsupported part type: {type(part.root)}")
        return ModelClientStreamingChunkEvent(
            content="\n".join(content), metadata=artifact.metadata or dict(), source=self._agent_name
        )

    def _to_config(self) -> A2aEventMapperConfig:
        return self._config

    @classmethod
    def _from_config(cls, config: A2aEventMapperConfig) -> Self:
        return cls(config.agent_name, config.output_content_type, config.output_content_type_format)
