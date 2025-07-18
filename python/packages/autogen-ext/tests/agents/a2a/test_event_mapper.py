import uuid
import io

import pytest
import base64
import json
from unittest.mock import MagicMock, patch

from PIL import Image as PILImage
from autogen_ext.agents.a2a._a2a_event_mapper import (
    convert_file_to_image,
    convert_file_to_str,
    handle_file_part,
    A2aEventMapper,
    A2aEventMapperConfig,
)

from a2a.types import Part, Message, Role, TextPart, AgentCard, DataPart, FilePart, FileWithBytes, FileWithUri, Artifact
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent, TextMessage, StructuredMessage, \
    StructuredMessageFactory, MultiModalMessage, ModelClientStreamingChunkEvent
from autogen_core import Image, ComponentBase
from pydantic import BaseModel

def to_base64(img: PILImage):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    content = buffered.getvalue()
    return base64.b64encode(content).decode("utf-8")

img = PILImage.new("RGB", (100, 100), color="red")
b64_img = to_base64(img)
img_data_uri = f"data:image/png;base64,{b64_img}"
img_object = Image.from_uri(img_data_uri)


# Dummy Pydantic Model for testing StructuredMessage
class MyPydanticModel(BaseModel):
    name: str
    value: int


# --- Test Cases for Utility Functions ---

def test_convert_file_to_image_file_with_bytes():
    """Test convert_file_to_image with FileWithBytes."""
    file_with_bytes = FileWithBytes(bytes=b64_img, mime_type="image/png")
    file_part = FilePart(file=file_with_bytes)

    image = convert_file_to_image(file_part)
    assert isinstance(image, Image)


def test_convert_file_to_image_file_with_uri():
    """Test convert_file_to_image with FileWithUri."""
    uri = img_data_uri
    file_with_uri = FileWithUri(uri=uri, mime_type="image/png")
    file_part = FilePart(file=file_with_uri)

    image = convert_file_to_image(file_part)
    assert isinstance(image, Image)


def test_convert_file_to_str_file_with_bytes():
    """Test convert_file_to_str with FileWithBytes."""
    original_text = "Hello, world!"
    b64_text_data = base64.b64encode(original_text.encode('utf-8')).decode('utf-8')
    file_with_bytes = FileWithBytes(bytes=b64_text_data, mime_type="text/plain")
    file_part = FilePart(file=file_with_bytes)

    result_str = convert_file_to_str(file_part)
    assert result_str == original_text


def test_convert_file_to_str_file_with_uri():
    """Test convert_file_to_str with FileWithUri."""
    uri = "https://example.com/document.pdf"
    file_with_uri = FileWithUri(uri=uri, mime_type="application/pdf")
    file_part = FilePart(file=file_with_uri)

    result_str = convert_file_to_str(file_part)
    assert result_str == uri


@patch('autogen_ext.agents.a2a._a2a_event_mapper.convert_file_to_image')
@patch('autogen_ext.agents.a2a._a2a_event_mapper.convert_file_to_str')
def test_handle_file_part_successful_image_conversion(mock_convert_to_str, mock_convert_to_image):
    """Test handle_file_part when image conversion succeeds."""
    mock_image_obj = img_object
    mock_convert_to_image.return_value = mock_image_obj
    file_part = MagicMock(spec=FilePart)

    result = handle_file_part(file_part)
    assert result == mock_image_obj
    mock_convert_to_image.assert_called_once_with(file_part)
    mock_convert_to_str.assert_not_called()


@patch('autogen_ext.agents.a2a._a2a_event_mapper.convert_file_to_image')
@patch('autogen_ext.agents.a2a._a2a_event_mapper.convert_file_to_str')
def test_handle_file_part_image_fails_string_succeeds(mock_convert_to_str, mock_convert_to_image):
    """Test handle_file_part when image conversion fails, but string conversion succeeds."""
    mock_convert_to_image.side_effect = ValueError("Not an image")
    mock_convert_to_str.return_value = "decoded_string"
    file_part = MagicMock(spec=FilePart)

    result = handle_file_part(file_part)
    assert result == "decoded_string"
    mock_convert_to_image.assert_called_once_with(file_part)
    mock_convert_to_str.assert_called_once_with(file_part)


@patch('autogen_ext.agents.a2a._a2a_event_mapper.convert_file_to_image')
@patch('autogen_ext.agents.a2a._a2a_event_mapper.convert_file_to_str')
def test_handle_file_part_both_conversions_fail(mock_convert_to_str, mock_convert_to_image):
    """Test handle_file_part when both image and string conversions fail."""
    mock_convert_to_image.side_effect = ValueError("Not an image")
    mock_convert_to_str.side_effect = ValueError("Unsupported file type")
    file_part = MagicMock(spec=FilePart)

    with pytest.raises(ValueError, match="Unsupported file type"):
        handle_file_part(file_part)
    mock_convert_to_image.assert_called_once_with(file_part)
    mock_convert_to_str.assert_called_once_with(file_part)


# --- Test Cases for A2aEventMapper ---

def test_a2a_event_mapper_init_basic():
    """Test A2aEventMapper initialization with basic parameters."""
    mapper = A2aEventMapper(agent_name="My-Agent")
    assert mapper._config.agent_name == "My-Agent"
    assert mapper._agent_name == "my-agent"
    assert mapper._output_content_type is None
    assert mapper._structured_message_factory is None


def test_a2a_event_mapper_init_with_output_content_type():
    """Test A2aEventMapper initialization with output_content_type."""
    mapper = A2aEventMapper(
        agent_name="Test-Agent",
        output_content_type=MyPydanticModel,
        output_content_type_format="{content.name}"
    )
    assert mapper._config.agent_name == "Test-Agent"
    assert mapper._agent_name == "test-agent"
    assert mapper._output_content_type == MyPydanticModel
    assert isinstance(mapper._structured_message_factory, StructuredMessageFactory)
    assert mapper._structured_message_factory.ContentModel == MyPydanticModel
    assert mapper._structured_message_factory.format_string == "{content.name}"


def test_a2a_event_mapper_handle_message_user_role():
    """Test handle_message with a user role message."""
    mapper = A2aEventMapper(agent_name="Agent")
    user_message = Message(role=Role.user, parts=[TextPart(text="Hello")], messageId=str(uuid.uuid4()))
    result = mapper.handle_message(user_message)
    assert result is None


def test_a2a_event_mapper_handle_message_empty_parts():
    """Test handle_message with an empty parts list."""
    mapper = A2aEventMapper(agent_name="Agent")
    empty_message = Message(role=Role.agent, parts=[], messageId=str(uuid.uuid4()))
    result = mapper.handle_message(empty_message)
    assert result is None


def test_a2a_event_mapper_handle_message_all_text_parts():
    """Test handle_message with multiple text parts."""
    mapper = A2aEventMapper(agent_name="Agent")
    message = Message(
        role=Role.agent,
        parts=[Part(root=TextPart(text="Part 1")), Part(root=TextPart(text="Part 2"))],
        metadata={"key": "value"},
        messageId = str(uuid.uuid4())
    )
    result = mapper.handle_message(message)
    assert isinstance(result, TextMessage)
    assert result.content == "Part 1\nPart 2"
    assert result.source == "agent"
    assert result.metadata == {"key": "value"}


def test_a2a_event_mapper_handle_message_single_data_part_with_output_type():
    """Test handle_message with a single data part and configured output type."""
    mapper = A2aEventMapper(
        agent_name="Agent",
        output_content_type=MyPydanticModel,
        output_content_type_format="{content.name}"
    )
    json_data = {"name": "Test", "value": 123}
    message = Message(
        role=Role.agent,
        parts=[Part(root=DataPart(data=json_data))],
        metadata={"id": "1"},
        messageId = str(uuid.uuid4())
    )
    result = mapper.handle_message(message)
    assert isinstance(result, StructuredMessage)
    assert isinstance(result.content, MyPydanticModel)
    assert result.content.name == "Test"
    assert result.content.value == 123
    assert result.source == "agent"
    assert result.format_string == "{content.name}"
    assert result.metadata == {"id": "1"}


def test_a2a_event_mapper_handle_message_single_data_part_no_output_type():
    """Test handle_message with a single data part and no output type configured."""
    mapper = A2aEventMapper(agent_name="Agent")
    json_data = {"key": "value"}
    message = Message(
        role=Role.agent,
        parts=[DataPart(data=json_data)],
        messageId=str(uuid.uuid4())
    )
    result = mapper.handle_message(message)
    assert isinstance(result, MultiModalMessage)
    assert len(result.content) == 1
    assert result.content[0] == json.dumps(json_data)
    assert result.source == "agent"


def test_a2a_event_mapper_handle_message_mixed_parts_with_image_file():
    """Test handle_message with mixed parts including an image file."""
    mapper = A2aEventMapper(agent_name="Agent")
    file_with_uri = FileWithUri(uri=img_data_uri, mime_type="image/png")
    file_part = FilePart(file=file_with_uri)

    message = Message(
        role=Role.agent,
        parts=[
            TextPart(text="Hello"),
            DataPart(data={"data_key": "data_value"}),
            file_part
        ],
        messageId=str(uuid.uuid4())
    )
    result = mapper.handle_message(message)
    print(result)
    assert isinstance(result, MultiModalMessage)
    assert len(result.content) == 3
    assert result.content[0] == "Hello"
    assert result.content[1] == json.dumps({"data_key": "data_value"})
    assert isinstance(result.content[2], Image)
    assert result.source == "agent"


@patch('autogen_ext.agents.a2a._a2a_event_mapper.handle_file_part')
def test_a2a_event_mapper_handle_message_mixed_parts_with_string_file(mock_handle_file_part):
    """Test handle_message with mixed parts including a string file (non-image)."""
    mapper = A2aEventMapper(agent_name="Agent")
    mock_handle_file_part.return_value = "file_content_as_string"

    file_with_bytes = FileWithBytes(bytes="b64_string", mime_type="text/plain")
    file_part = FilePart(file=file_with_bytes)

    message = Message(
        role=Role.agent,
        parts=[
            TextPart(text="Introduction"),
            file_part
        ],
        messageId=str(uuid.uuid4())
    )
    result = mapper.handle_message(message)
    assert isinstance(result, MultiModalMessage)
    assert len(result.content) == 2
    assert result.content[0] == "Introduction"
    assert result.content[1] == "file_content_as_string"
    mock_handle_file_part.assert_called_once_with(file_part)


def test_a2a_event_mapper_handle_artifact_empty_parts():
    """Test handle_artifact with an empty parts list."""
    mapper = A2aEventMapper(agent_name="Agent")
    empty_artifact = Artifact(artifactId="123", parts=[])
    result = mapper.handle_artifact(empty_artifact)
    assert result is None


@patch('autogen_ext.agents.a2a._a2a_event_mapper.A2aEventMapper.handle_message')
def test_a2a_event_mapper_handle_artifact_with_file_parts(mock_handle_message):
    """Test handle_artifact when it contains file parts (delegates to handle_message)."""
    mapper = A2aEventMapper(agent_name="Agent")
    mock_message_result = MagicMock(spec=MultiModalMessage)
    mock_handle_message.return_value = mock_message_result

    file_part = Part(root=FilePart(file=FileWithBytes(bytes="b64_data", mime_type="image/jpeg")))
    text_part = Part(root=TextPart(text="Some text"))
    artifact = Artifact(
        artifactId="art1",
        parts=[text_part, file_part],
        metadata={"test_meta": "artifact_value"}
    )

    result = mapper.handle_artifact(artifact)
    assert result == mock_message_result
    mock_handle_message.assert_called_once()
    # Verify handle_message was called with a Message object constructed from the artifact
    called_message = mock_handle_message.call_args[0][0]
    assert isinstance(called_message, Message)
    assert called_message.parts == [text_part, file_part]
    assert called_message.role == Role.agent
    assert called_message.messageId == "art1"
    assert called_message.metadata == {"test_meta": "artifact_value"}


def test_a2a_event_mapper_handle_artifact_only_text_parts():
    """Test handle_artifact with only text parts."""
    mapper = A2aEventMapper(agent_name="Agent")
    artifact = Artifact(
        artifactId="art2",
        parts=[TextPart(text="Line one"), TextPart(text="Line two")],
        metadata={"source": "artifact"}
    )
    result = mapper.handle_artifact(artifact)
    assert isinstance(result, ModelClientStreamingChunkEvent)
    assert result.content == "Line one\nLine two"
    assert result.source == "agent"
    assert result.metadata == {"source": "artifact"}


def test_a2a_event_mapper_handle_artifact_only_data_parts():
    """Test handle_artifact with only data parts."""
    mapper = A2aEventMapper(agent_name="Agent")
    json_data1 = {"id": 1}
    json_data2 = {"status": "ok"}
    artifact = Artifact(
        artifactId="art3",
        parts=[Part(root=DataPart(data=json_data1)), Part(root=DataPart(data=json_data2))]
    )
    result = mapper.handle_artifact(artifact)
    assert isinstance(result, ModelClientStreamingChunkEvent)
    assert result.content == f'{json.dumps(json_data1)}\n{json.dumps(json_data2)}'
    assert result.source == "agent"


def test_a2a_event_mapper_handle_artifact_mixed_text_and_data_parts_no_files():
    """Test handle_artifact with mixed text and data parts, but no files."""
    mapper = A2aEventMapper(agent_name="Agent")
    json_data = {"command": "execute"}
    artifact = Artifact(
        artifactId="art4",
        parts=[Part(root=TextPart(text="Processing")), Part(root=DataPart(data=json_data)), Part(root=TextPart(text="Done"))]
    )
    result = mapper.handle_artifact(artifact)
    assert isinstance(result, ModelClientStreamingChunkEvent)
    assert result.content == f'Processing\n{json.dumps(json_data)}\nDone'
    assert result.source == "agent"

def test_a2a_event_mapper_to_config_basic():
    """Test _to_config method with basic initialization."""
    mapper = A2aEventMapper(agent_name="ConfigAgent")
    config = mapper._to_config()
    assert isinstance(config, A2aEventMapperConfig)
    assert config.agent_name == "ConfigAgent"
    assert config.output_content_type is None
    assert config.output_content_type_format is None


def test_a2a_event_mapper_to_config_with_output_type():
    """Test _to_config method with output_content_type configured."""
    mapper = A2aEventMapper(
        agent_name="ConfigAgent2",
        output_content_type=MyPydanticModel,
        output_content_type_format="format_str"
    )
    config = mapper._to_config()
    assert isinstance(config, A2aEventMapperConfig)
    assert config.agent_name == "ConfigAgent2"
    assert config.output_content_type == MyPydanticModel
    assert config.output_content_type_format == "format_str"


def test_a2a_event_mapper_from_config_basic():
    """Test _from_config method with basic config."""
    config = A2aEventMapperConfig(agent_name="Reconstructed-Agent")
    mapper = A2aEventMapper._from_config(config)
    assert isinstance(mapper, A2aEventMapper)
    assert mapper._agent_name == "reconstructed-agent"
    assert mapper._output_content_type is None
    assert mapper._structured_message_factory is None


def test_a2a_event_mapper_from_config_with_output_type():
    """Test _from_config method with output_content_type in config."""
    config = A2aEventMapperConfig(
        agent_name="Reconstructed-Agent2",
        output_content_type=MyPydanticModel,
        output_content_type_format="re_format"
    )
    mapper = A2aEventMapper._from_config(config)
    assert isinstance(mapper, A2aEventMapper)
    assert mapper._agent_name == "reconstructed-agent2"
    assert mapper._output_content_type == MyPydanticModel
    assert isinstance(mapper._structured_message_factory, StructuredMessageFactory)
    assert mapper._structured_message_factory.ContentModel == MyPydanticModel
    assert mapper._structured_message_factory.format_string == "re_format"