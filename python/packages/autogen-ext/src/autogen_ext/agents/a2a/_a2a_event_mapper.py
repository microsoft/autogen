import base64
import json
from typing import Self

from a2a.types import Message, Role, TextPart, AgentCard, DataPart, FilePart, FileWithBytes, FileWithUri, Artifact
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent, TextMessage, StructuredMessage, \
    StructuredMessageFactory, MultiModalMessage, ModelClientStreamingChunkEvent
from autogen_core import Image, ComponentBase
from pydantic import BaseModel
from slugify import slugify


def convert_file_to_image(file_part: FilePart) -> Image:
    if isinstance(file_part.file, FileWithBytes):
        return Image.from_base64(file_part.file.bytes)
    elif isinstance(file_part.file, FileWithUri):
        return Image.from_uri(file_part.file.uri)
    else:
        raise ValueError(f"Unsupported file type: {type(file_part.file)}")


def convert_file_to_str(file_part: FilePart) -> str:
    if isinstance(file_part.file, FileWithBytes):
        return base64.b64decode(file_part.file.bytes).decode(encoding="utf-8")
    elif isinstance(file_part.file, FileWithUri):
        return file_part.file.uri
    else:
        raise ValueError(f"Unsupported file type: {type(file_part.file)}")


def handle_file_part(file_part: FilePart) -> Image | str:
    try:
        return convert_file_to_image(file_part)
    except Exception as e:
        # If conversion to Image fails, try converting to string
        return convert_file_to_str(file_part)

class A2aEventMapperConfig(BaseModel):
    agent_name: str
    output_content_type: type[BaseModel] | None = None
    output_content_type_format: str | None = None


class A2aEventMapper(BaseModel, ComponentBase[A2aEventMapperConfig]):
    """
    A2aEventMapper is a class that provides methods to deserialize data.
    """
    def __init__(self, agent_name: str, output_content_type: type[BaseModel] | None = None,
                 output_content_type_format: str | None = None):
        super().__init__()
        self._config = A2aEventMapperConfig(agent_name=agent_name, output_content_type=output_content_type, output_content_type_format=output_content_type_format)
        self._agent_name = slugify(agent_name)
        self._output_content_type = output_content_type
        self._format_string = output_content_type_format
        self._structured_message_factory: StructuredMessageFactory | None = None
        if output_content_type is not None:
            self._structured_message_factory = StructuredMessageFactory(
                input_model=output_content_type, format_string=output_content_type_format
            )

    def handle_message(self, message: Message) -> BaseChatMessage | None:
        """
        Deserialize the given data.
        This method is currently not implemented.
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
                metadata=message.metadata or dict()
            )

        is_only_data = all(isinstance(part.root, DataPart) for part in message.parts) and len(message.parts) == 1
        if is_only_data:
            if self._output_content_type is not None:
                content = self._output_content_type.model_validate_json(json.dumps(message.parts[0].root.data))
                return StructuredMessage(
                    content=content,
                    source=self._agent_name,
                    format_string=self._format_string,
                    metadata=message.metadata or dict()
                )
        contents = []
        for part in message.parts:
            if isinstance(part.root, TextPart):
                contents.append(part.root.text)
            elif isinstance(part.root, DataPart):
                contents.append(json.dumps(part.root.data))
            elif isinstance(part.root, FilePart):
                contents.append(handle_file_part(part.root))
            else:
                raise ValueError(f"Unsupported part type: {type(part.root)}")
        return MultiModalMessage(
            source=self._agent_name,
            content=contents,
            metadata=message.metadata or dict()
        )

    def handle_artifact(self, artifact: Artifact) -> BaseAgentEvent | BaseChatMessage |None:
        """
        Deserialize the given artifact data.
        This method is currently not implemented.
        """
        if not artifact.parts or len(artifact.parts) == 0:
            return None

        has_file_parts = any(isinstance(part.root, FilePart) for part in artifact.parts)
        if has_file_parts:
            return self.handle_message(Message(
                parts=artifact.parts,
                role=Role.agent,
                messageId=artifact.artifactId,
                metadata=artifact.metadata or dict()
            ))
        content = []

        for part in artifact.parts:
            if isinstance(part.root, TextPart):
                content.append(part.root.text)
            elif isinstance(part.root, DataPart):
                content.append(json.dumps(part.root.data))
            else:
                raise ValueError(f"Unsupported part type: {type(part.root)}")
        return ModelClientStreamingChunkEvent(
            content="\n".join(content),
            metadata=artifact.metadata or dict(),
            source=self._agent_name
        )

    def _to_config(self) -> A2aEventMapperConfig:
        return self._config

    @classmethod
    def _from_config(cls, config: A2aEventMapperConfig) -> Self:
        return cls(config.agent_name, config.output_content_type, config.output_content_type_format)