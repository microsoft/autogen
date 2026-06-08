"""Tests for McpSessionHost to cover MCP host functionality."""

import atexit
from pathlib import Path
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import FunctionCall
from autogen_core.models import (
    CreateResult,
    ModelInfo,
    RequestUsage,
    UserMessage,
)
from autogen_ext.tools.mcp import (
    ChatCompletionClientSampler,
    McpSessionHost,
    StaticRootsProvider,
    StdioElicitor,
    StreamElicitor,
)
from autogen_ext.tools.mcp._config import StdioServerParams
from autogen_ext.tools.mcp._host._sampling import (
    finish_reason_to_stop_reason,
    parse_sampling_content,
    parse_sampling_message,
)
from mcp import types as mcp_types

# Monkey patch to prevent atexit handlers from being registered during tests
# This prevents the test suite from hanging during shutdown
original_atexit_register = atexit.register


def mock_atexit_register(func: Callable[[], None], *args: Any, **kwargs: Any) -> None:
    """Mock atexit.register to prevent registration during tests."""
    del func, args, kwargs  # Mark as used


# Apply the monkey patch
atexit.register = mock_atexit_register  # type: ignore[assignment]


@pytest.fixture
def mock_model_client() -> MagicMock:
    """Mock model client for testing."""
    model_client = MagicMock()
    model_client.model_info = {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": "test-model",
        "structured_output": False,
    }
    model_client.create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    return model_client


@pytest.fixture
def mock_model_client_with_vision() -> MagicMock:
    """Mock model client with vision support for testing."""
    model_client = MagicMock()
    model_client.model_info = {
        "vision": True,
        "function_calling": False,
        "json_output": False,
        "family": "test-vision-model",
        "structured_output": False,
    }
    model_client.create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    return model_client


def test_parse_sampling_message_assistant_with_string_content() -> None:
    """Test _parse_sampling_message with assistant message containing string content (line 61)."""
    model_info: ModelInfo = {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": "test-model",
        "structured_output": False,
    }
    # Create string content for assistant message
    text_content = mcp_types.TextContent(type="text", text="Hello, I'm an assistant")
    message = mcp_types.SamplingMessage(role="assistant", content=text_content)

    result = parse_sampling_message(message, model_info)

    from autogen_core.models import AssistantMessage

    assert isinstance(result, AssistantMessage)
    assert result.content == "Hello, I'm an assistant"
    assert result.source == "assistant"


def test_finish_reason_to_stop_reason_length() -> None:
    """Test _finish_reason_to_stop_reason with 'length' finish reason (lines 72-75)."""
    result = finish_reason_to_stop_reason("length")
    assert result == "maxTokens"


def test_finish_reason_to_stop_reason_other() -> None:
    """Test _finish_reason_to_stop_reason with other finish reasons (line 75)."""
    # Test with a custom finish reason that should be returned as-is
    result = finish_reason_to_stop_reason("content_filter")
    assert result == "content_filter"


def test_finish_reason_to_stop_reason_stop() -> None:
    """Test _finish_reason_to_stop_reason with 'stop' finish reason."""
    result = finish_reason_to_stop_reason("stop")
    assert result == "endTurn"


# McpSessionHost integration tests
@pytest.mark.asyncio
async def test_mcp_session_host_sampling_request(mock_model_client: Any) -> None:
    """Test McpSessionHost handles sampling requests correctly."""
    sampler = ChatCompletionClientSampler(mock_model_client)
    host = McpSessionHost(sampler=sampler)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.CreateMessageResult)
    assert result.role == "assistant"
    assert isinstance(result.content, mcp_types.TextContent)
    assert result.content.text == "Mock response"
    assert result.model == "test-model"


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_request_no_sampler() -> None:
    """Test McpSessionHost returns error when no sampler available."""
    host = McpSessionHost(sampler=None)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "No model client available for sampling requests" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_request_with_system_prompt(mock_model_client: Any) -> None:
    """Test McpSessionHost handles sampling requests with system prompt."""
    sampler = ChatCompletionClientSampler(mock_model_client)
    host = McpSessionHost(sampler=sampler)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
        systemPrompt="You are a helpful assistant.",
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.CreateMessageResult)
    # Verify that the model client was called with system message
    mock_model_client.create.assert_called_once()
    call_args = mock_model_client.create.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 2  # SystemMessage + UserMessage
    assert messages[0].content == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_request_error_handling(mock_model_client: Any) -> None:
    """Test McpSessionHost handles sampling errors correctly."""
    # Configure model client to raise an exception
    mock_model_client.create = AsyncMock(side_effect=Exception("Model API error"))
    sampler = ChatCompletionClientSampler(mock_model_client)
    host = McpSessionHost(sampler=sampler)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INTERNAL_ERROR
    assert "Sampling request failed" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_elicit_request() -> None:
    """Test McpSessionHost handles elicit requests correctly."""
    # Create a mock elicitor
    mock_elicitor = MagicMock(spec=StdioElicitor)
    mock_elicitor.elicit = AsyncMock(
        return_value=mcp_types.ElicitResult(
            action="accept", content={"reasoning": "Test reasoning", "answer": "Test answer"}
        )
    )

    host = McpSessionHost(elicitor=mock_elicitor)

    params = mcp_types.ElicitRequestParams(message="Test elicitation message", requestedSchema={"type": "object"})

    result = await host.handle_elicit_request(params)

    assert isinstance(result, mcp_types.ElicitResult)
    assert result.action == "accept"
    assert result.content is not None
    assert result.content["reasoning"] == "Test reasoning"
    assert result.content["answer"] == "Test answer"
    mock_elicitor.elicit.assert_called_once_with(params)


@pytest.mark.asyncio
async def test_mcp_session_host_elicit_request_no_elicitor() -> None:
    """Test McpSessionHost returns error when no elicitor available."""
    host = McpSessionHost(elicitor=None)

    params = mcp_types.ElicitRequestParams(message="Test elicitation message", requestedSchema={"type": "object"})

    result = await host.handle_elicit_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "No elicitor configured" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_elicit_request_error_handling() -> None:
    """Test McpSessionHost handles elicit errors correctly."""
    # Create a mock elicitor that raises an exception
    mock_elicitor = MagicMock(spec=StdioElicitor)
    mock_elicitor.elicit = AsyncMock(side_effect=Exception("Elicitor error"))

    host = McpSessionHost(elicitor=mock_elicitor)

    params = mcp_types.ElicitRequestParams(message="Test elicitation message", requestedSchema={"type": "object"})

    result = await host.handle_elicit_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INTERNAL_ERROR
    assert "Elicitation request failed" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_list_roots_request() -> None:
    """Test McpSessionHost handles list roots requests correctly."""
    from pydantic import FileUrl

    test_roots = [
        mcp_types.Root(uri=FileUrl("file:///test1"), name="Test Root 1"),
        mcp_types.Root(uri=FileUrl("file:///test2"), name="Test Root 2"),
    ]

    roots_provider = StaticRootsProvider(test_roots)
    host = McpSessionHost(roots=roots_provider)

    result = await host.handle_list_roots_request()

    assert isinstance(result, mcp_types.ListRootsResult)
    assert len(result.roots) == 2
    assert str(result.roots[0].uri) == "file:///test1"
    assert result.roots[0].name == "Test Root 1"
    assert str(result.roots[1].uri) == "file:///test2"
    assert result.roots[1].name == "Test Root 2"


@pytest.mark.asyncio
async def test_mcp_session_host_list_roots_request_callable() -> None:
    """Test McpSessionHost handles list roots requests with callable roots."""
    from pydantic import FileUrl

    test_roots = [
        mcp_types.Root(uri=FileUrl("file:///dynamic1"), name="Dynamic Root 1"),
        mcp_types.Root(uri=FileUrl("file:///dynamic2"), name="Dynamic Root 2"),
    ]

    roots_provider = StaticRootsProvider(test_roots)
    host = McpSessionHost(roots=roots_provider)

    result = await host.handle_list_roots_request()

    assert isinstance(result, mcp_types.ListRootsResult)
    assert len(result.roots) == 2
    assert str(result.roots[0].uri) == "file:///dynamic1"
    assert result.roots[0].name == "Dynamic Root 1"


@pytest.mark.asyncio
async def test_mcp_session_host_list_roots_request_async_callable() -> None:
    """Test McpSessionHost handles list roots requests with async callable roots (line 292)."""
    from pydantic import FileUrl

    test_roots = [
        mcp_types.Root(uri=FileUrl("file:///async1"), name="Async Root 1"),
    ]

    roots_provider = StaticRootsProvider(test_roots)
    host = McpSessionHost(roots=roots_provider)

    result = await host.handle_list_roots_request()

    assert isinstance(result, mcp_types.ListRootsResult)
    assert len(result.roots) == 1
    assert str(result.roots[0].uri) == "file:///async1"
    assert result.roots[0].name == "Async Root 1"


@pytest.mark.asyncio
async def test_mcp_session_host_list_roots_request_no_roots() -> None:
    """Test McpSessionHost returns error when no roots configured."""
    host = McpSessionHost(roots=None)

    result = await host.handle_list_roots_request()

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "Host does not support listing roots" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_list_roots_request_error_handling() -> None:
    """Test McpSessionHost handles list roots errors correctly."""
    # Create a mock roots provider that raises an exception
    mock_roots_provider = MagicMock(spec=StaticRootsProvider)
    mock_roots_provider.list_roots = AsyncMock(side_effect=Exception("Roots error"))

    host = McpSessionHost(roots=mock_roots_provider)

    result = await host.handle_list_roots_request()

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INTERNAL_ERROR
    assert "Caught error listing roots" in result.message


# Configuration serialization tests removed due to API changes
# The new implementation uses separate Sampler, RootsProvider, and Elicitor components
# These tests would need significant rework to match the new architecture


def test_mcp_session_host_initialization() -> None:
    """Test McpSessionHost initialization."""
    host = McpSessionHost()

    assert host._sampler is None  # type: ignore[reportPrivateUsage]
    assert host._roots is None  # type: ignore[reportPrivateUsage]
    assert host._elicitor is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_mcp_session_host_with_vision_model(mock_model_client_with_vision: Any) -> None:
    """Test McpSessionHost handles image content with vision-enabled model."""
    sampler = ChatCompletionClientSampler(mock_model_client_with_vision)
    host = McpSessionHost(sampler=sampler)

    # Test with image content
    image_content = mcp_types.ImageContent(
        type="image",
        data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        mimeType="image/png",
    )

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=image_content)],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.CreateMessageResult)
    assert result.role == "assistant"
    mock_model_client_with_vision.create.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_with_extra_args(mock_model_client: Any) -> None:
    """Test McpSessionHost handles sampling requests with extra parameters."""
    sampler = ChatCompletionClientSampler(mock_model_client)
    host = McpSessionHost(sampler=sampler)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=200,
        temperature=0.7,
        stopSequences=["STOP", "END"],
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.CreateMessageResult)
    # Verify extra args were passed to model client
    mock_model_client.create.assert_called_once()
    call_args = mock_model_client.create.call_args[1]
    extra_args = call_args["extra_create_args"]
    assert extra_args["max_tokens"] == 200
    assert extra_args["temperature"] == 0.7
    assert extra_args["stop"] == ["STOP", "END"]


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_with_complex_response(mock_model_client: Any) -> None:
    """Test McpSessionHost handles complex/non-string model responses."""
    # Configure model client to return complex content
    mock_model_client.create = AsyncMock(
        return_value=CreateResult(
            content=[FunctionCall(id="test_func_call_1", name="test_func", arguments='{"param": "value"}')],
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    sampler = ChatCompletionClientSampler(mock_model_client)
    host = McpSessionHost(sampler=sampler)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.CreateMessageResult)
    assert result.role == "assistant"
    assert isinstance(result.content, mcp_types.TextContent)
    # Should be JSON serialized version of complex content
    assert "test_func" in result.content.text


@pytest.fixture
def mcp_server_params() -> StdioServerParams:
    """Create server parameters that will launch the real MCP server subprocess."""
    # Get the path to the simple MCP server
    server_path = Path(__file__).parent.parent / "mcp_server_comprehensive.py"
    return StdioServerParams(
        command="uv",
        args=["run", "python", str(server_path)],
        read_timeout_seconds=10,
    )


# Integration test removed due to API changes - GroupChatAgentElicitor no longer exists
# This test would need to be rewritten to use the new elicitor interfaces


# Additional tests to improve coverage


# StreamElicitor tests
@pytest.mark.asyncio
async def test_stream_elicitor_basic_functionality() -> None:
    """Test StreamElicitor basic elicit functionality with schema."""
    import io
    from unittest.mock import patch

    read_stream = io.StringIO("accept\n")
    write_stream = io.StringIO()

    elicitor = StreamElicitor(read_stream, write_stream)

    schema = {"type": "object", "properties": {"response": {"type": "string"}}}
    params = mcp_types.ElicitRequestParams(message="Test message", requestedSchema=schema)

    # Mock asyncio.to_thread to return the read value synchronously
    call_responses = ["accept\n", '{"response": "test"}\n']  # action then content for schema
    call_count = {"count": 0}

    def mock_return(*args: Any, **kwargs: Any) -> str:
        result = call_responses[call_count["count"]]
        call_count["count"] += 1
        return result

    with patch("asyncio.to_thread", side_effect=mock_return):
        result = await elicitor.elicit(params)

        assert isinstance(result, mcp_types.ElicitResult)
        assert result.action == "accept"
        assert result.content == {"response": "test"}

        # Check that prompt was written
        written_text = write_stream.getvalue()
        assert "Test message" in written_text
        assert "Choices:" in written_text
        assert "[a]ccept" in written_text
        assert "Input Schema:" in written_text


@pytest.mark.asyncio
async def test_stream_elicitor_initialization() -> None:
    """Test StreamElicitor initialization and basic properties."""
    import io

    read_stream = io.StringIO()
    write_stream = io.StringIO()
    timeout = 5.0

    elicitor = StreamElicitor(read_stream, write_stream, timeout)

    assert elicitor._read_stream is read_stream  # type: ignore[reportPrivateUsage]
    assert elicitor._write_stream is write_stream  # type: ignore[reportPrivateUsage]
    assert elicitor._timeout == timeout  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_stream_elicitor_with_timeout() -> None:
    """Test StreamElicitor with timeout functionality."""
    import io
    from unittest.mock import patch

    read_stream = io.StringIO("decline\n")
    write_stream = io.StringIO()

    elicitor = StreamElicitor(read_stream, write_stream, timeout=5.0)

    params = mcp_types.ElicitRequestParams(message="Test message", requestedSchema={})

    call_responses = ["decline\n", "{}\n"]  # action then content for schema
    call_count = {"count": 0}

    def mock_return(*args: Any, **kwargs: Any) -> str:
        result = call_responses[call_count["count"]]
        call_count["count"] += 1
        return result

    with (
        patch("asyncio.to_thread", side_effect=mock_return),
        patch("asyncio.wait_for", side_effect=mock_return) as mock_wait_for,
    ):
        result = await elicitor.elicit(params)

        assert result.action == "decline"
        # Verify wait_for was called with timeout (should be called twice - once for action, once for schema)
        assert mock_wait_for.call_count >= 1


@pytest.mark.asyncio
async def test_stream_elicitor_with_schema() -> None:
    """Test StreamElicitor with requestedSchema."""
    import io
    import json
    from unittest.mock import patch

    read_stream = io.StringIO("a\n")
    write_stream = io.StringIO()

    elicitor = StreamElicitor(read_stream, write_stream)

    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    params = mcp_types.ElicitRequestParams(message="Test message", requestedSchema=schema)

    call_count = {"count": 0}

    def side_effect(*args: Any, **kwargs: Any) -> str:
        # First call returns action, second returns JSON content
        if call_count["count"] == 0:
            call_count["count"] += 1
            return "a\n"
        else:
            return '{"name": "test"}\n'

    with patch("asyncio.to_thread", side_effect=side_effect):
        result = await elicitor.elicit(params)

        assert result.action == "accept"
        assert result.content == {"name": "test"}

        # Check that schema was written
        written_text = write_stream.getvalue()
        assert "Input Schema:" in written_text
        assert json.dumps(schema, indent=2) in written_text


@pytest.mark.asyncio
async def test_stream_elicitor_shorthand_mapping() -> None:
    """Test StreamElicitor shorthand choice mapping."""
    import io
    from unittest.mock import patch

    read_stream = io.StringIO("d\n")  # Should map to "decline"
    write_stream = io.StringIO()

    elicitor = StreamElicitor(read_stream, write_stream)

    params = mcp_types.ElicitRequestParams(message="Test", requestedSchema={})

    call_responses = ["d\n", "{}\n"]  # action then content for schema
    call_count = {"count": 0}

    def mock_return(*args: Any, **kwargs: Any) -> str:
        result = call_responses[call_count["count"]]
        call_count["count"] += 1
        return result

    with patch("asyncio.to_thread", side_effect=mock_return):
        result = await elicitor.elicit(params)
        assert result.action == "decline"


# StdioElicitor tests
def test_stdio_elicitor_initialization() -> None:
    """Test StdioElicitor initialization."""
    elicitor = StdioElicitor(timeout=10.0)

    assert elicitor.timeout == 10.0
    # Should use sys.stdin and sys.stdout
    import sys

    assert elicitor._read_stream is sys.stdin  # type: ignore[reportPrivateUsage]
    assert elicitor._write_stream is sys.stdout  # type: ignore[reportPrivateUsage]


def test_stdio_elicitor_config_serialization() -> None:
    """Test StdioElicitor config serialization."""
    elicitor = StdioElicitor(timeout=5.0)

    config = elicitor.dump_component()

    # Config should be a ComponentModel with nested config
    assert config is not None
    assert config.provider == "autogen_ext.tools.mcp.StdioElicitor"
    assert config.component_type == "mcp_elicitor"
    assert config.config["timeout"] == 5.0


def test_stdio_elicitor_from_config() -> None:
    """Test StdioElicitor load_component method."""
    config_dict: dict[str, object] = {
        "provider": "autogen_ext.tools.mcp.StdioElicitor",
        "component_type": "mcp_elicitor",
        "config": {"timeout": 15.0},
    }
    elicitor = StdioElicitor.load_component(config_dict)

    assert isinstance(elicitor, StdioElicitor)
    assert elicitor.timeout == 15.0


# Additional sampling tests for missing coverage
def test_parse_sampling_content_audio_unsupported() -> None:
    """Test parse_sampling_content raises ValueError for audio content."""

    audio_content = mcp_types.AudioContent(type="audio", data="audio_data", mimeType="audio/wav")

    with pytest.raises(ValueError, match="Unsupported content type: audio"):
        parse_sampling_content(audio_content)


def test_parse_sampling_content_image_without_vision() -> None:
    """Test parse_sampling_content raises RuntimeError for image without vision model."""

    image_content = mcp_types.ImageContent(
        type="image",
        data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        mimeType="image/png",
    )

    model_info: ModelInfo = {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": "test-model",
        "structured_output": False,
    }

    with pytest.raises(RuntimeError, match="model test-model does not support vision"):
        parse_sampling_content(image_content, model_info)


def test_parse_sampling_message_user_with_image() -> None:
    """Test parse_sampling_message with user message containing image."""
    from autogen_ext.tools.mcp._host._sampling import parse_sampling_message

    image_content = mcp_types.ImageContent(
        type="image",
        data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        mimeType="image/png",
    )

    message = mcp_types.SamplingMessage(role="user", content=image_content)

    model_info: ModelInfo = {
        "vision": True,
        "function_calling": False,
        "json_output": False,
        "family": "vision-model",
        "structured_output": False,
    }

    result = parse_sampling_message(message, model_info)

    assert isinstance(result, UserMessage)
    assert len(result.content) == 1
    # Should be an Image object
    from autogen_core import Image

    assert isinstance(result.content[0], Image)


def test_parse_sampling_message_invalid_role() -> None:
    """Test parse_sampling_message raises ValueError for invalid role."""
    from autogen_ext.tools.mcp._host._sampling import parse_sampling_message

    # Create a mock message object that bypasses Pydantic validation
    class MockMessage:
        def __init__(self, role: str, content: Any):
            self.role = role
            self.content = content

    text_content = mcp_types.TextContent(type="text", text="Hello")
    message = MockMessage(role="invalid", content=text_content)

    with pytest.raises(ValueError, match="Unrecognized message role: invalid"):
        parse_sampling_message(message)  # type: ignore[arg-type]


# Additional roots provider tests
def test_static_roots_provider_config_serialization() -> None:
    """Test StaticRootsProvider config serialization."""
    from pydantic import FileUrl

    test_roots = [
        mcp_types.Root(uri=FileUrl("file:///test"), name="Test Root"),
    ]

    provider = StaticRootsProvider(test_roots)
    config = provider.dump_component()

    # Config should be a ComponentModel with nested config
    assert config is not None
    assert config.provider == "autogen_ext.tools.mcp.StaticRootsProvider"
    assert config.component_type == "mcp_roots_provider"
    assert len(config.config["roots"]) == 1


def test_static_roots_provider_from_config() -> None:
    """Test StaticRootsProvider load_component method."""
    from pydantic import FileUrl

    test_roots = [
        mcp_types.Root(uri=FileUrl("file:///config_test"), name="Config Root"),
    ]

    # Create a proper ComponentModel-style config
    component_config: dict[str, object] = {
        "provider": "autogen_ext.tools.mcp.StaticRootsProvider",
        "component_type": "mcp_roots_provider",
        "config": {"roots": test_roots},
    }
    provider = StaticRootsProvider.load_component(component_config)

    assert isinstance(provider, StaticRootsProvider)


# ChatCompletionClientSampler config tests
def test_chat_completion_client_sampler_config_serialization(mock_model_client: Any) -> None:
    """Test ChatCompletionClientSampler config serialization."""
    mock_model_client.dump_component = MagicMock(return_value={"type": "mock", "config": {}})

    sampler = ChatCompletionClientSampler(mock_model_client)
    config = sampler.dump_component()

    # Config should be a ComponentModel with nested config
    assert config is not None
    assert config.provider == "autogen_ext.tools.mcp.ChatCompletionClientSampler"
    assert config.component_type == "mcp_sampler"
    assert config.config["client_config"] == {"type": "mock", "config": {}}


def test_chat_completion_client_sampler_from_config() -> None:
    """Test ChatCompletionClientSampler load_component method."""
    from autogen_core.models import ChatCompletionClient

    # Create a proper ComponentModel-style config
    component_config: dict[str, object] = {
        "provider": "autogen_ext.tools.mcp.ChatCompletionClientSampler",
        "component_type": "mcp_sampler",
        "config": {"client_config": {"type": "mock", "config": {}}},
    }

    mock_client = MagicMock()
    with patch.object(ChatCompletionClient, "load_component", return_value=mock_client):
        sampler = ChatCompletionClientSampler.load_component(component_config)

        assert isinstance(sampler, ChatCompletionClientSampler)


# Additional McpSessionHost tests to improve coverage
def test_mcp_session_host_component_attributes() -> None:
    """Test McpSessionHost component configuration attributes (lines 99-101)."""
    from autogen_ext.tools.mcp._host._session_host import McpSessionHostConfig

    assert McpSessionHost.component_type == "mcp_session_host"
    assert McpSessionHost.component_config_schema == McpSessionHostConfig
    assert McpSessionHost.component_provider_override == "autogen_ext.tools.mcp.McpSessionHost"


def test_mcp_session_host_constructor_attributes() -> None:
    """Test McpSessionHost constructor sets attributes correctly (lines 116-118)."""
    mock_sampler = MagicMock()
    mock_roots = MagicMock()
    mock_elicitor = MagicMock()

    host = McpSessionHost(
        sampler=mock_sampler,
        roots=mock_roots,
        elicitor=mock_elicitor,
    )

    assert host._sampler is mock_sampler  # type: ignore[reportPrivateUsage]
    assert host._roots is mock_roots  # type: ignore[reportPrivateUsage]
    assert host._elicitor is mock_elicitor  # type: ignore[reportPrivateUsage]


def test_mcp_session_host_to_config_full() -> None:
    """Test McpSessionHost _to_config method with all components (lines 194-198)."""
    from autogen_ext.tools.mcp._host._session_host import McpSessionHostConfig

    # Create mock components with dump_component methods
    mock_sampler = MagicMock()
    mock_sampler.dump_component = MagicMock(return_value={"type": "sampler", "config": {}})

    mock_roots = MagicMock()
    mock_roots.dump_component = MagicMock(return_value={"type": "roots", "config": {}})

    mock_elicitor = MagicMock()
    mock_elicitor.dump_component = MagicMock(return_value={"type": "elicitor", "config": {}})

    host = McpSessionHost(
        sampler=mock_sampler,
        roots=mock_roots,
        elicitor=mock_elicitor,
    )

    config = host._to_config()  # type: ignore[reportPrivateUsage]

    assert isinstance(config, McpSessionHostConfig)
    assert config.sampler == {"type": "sampler", "config": {}}
    assert config.elicitor == {"type": "elicitor", "config": {}}
    assert config.roots == {"type": "roots", "config": {}}


def test_mcp_session_host_to_config_partial() -> None:
    """Test McpSessionHost _to_config method with some None components."""
    from autogen_ext.tools.mcp._host._session_host import McpSessionHostConfig

    mock_sampler = MagicMock()
    mock_sampler.dump_component = MagicMock(return_value={"type": "sampler", "config": {}})

    host = McpSessionHost(sampler=mock_sampler, roots=None, elicitor=None)

    config = host._to_config()  # type: ignore[reportPrivateUsage]

    assert isinstance(config, McpSessionHostConfig)
    assert config.sampler == {"type": "sampler", "config": {}}
    assert config.elicitor is None
    assert config.roots is None


def test_mcp_session_host_from_config() -> None:
    """Test McpSessionHost _from_config method (lines 201-204)."""
    from autogen_ext.tools.mcp import Elicitor, RootsProvider, Sampler
    from autogen_ext.tools.mcp._host._session_host import McpSessionHostConfig

    # Create mock components
    mock_sampler = MagicMock()
    mock_elicitor = MagicMock()
    mock_roots = MagicMock()

    sampler_config: dict[str, object] = {"type": "mock_sampler", "config": {}}
    elicitor_config: dict[str, object] = {"type": "mock_elicitor", "config": {}}
    roots_config: dict[str, object] = {"type": "mock_roots", "config": {}}

    config = McpSessionHostConfig(
        sampler=sampler_config,
        elicitor=elicitor_config,
        roots=roots_config,
    )

    # Mock the load_component methods
    with (
        patch.object(Sampler, "load_component", return_value=mock_sampler),
        patch.object(Elicitor, "load_component", return_value=mock_elicitor),
        patch.object(RootsProvider, "load_component", return_value=mock_roots),
    ):
        host = McpSessionHost._from_config(config)  # type: ignore[reportPrivateUsage]

        assert host._sampler is mock_sampler  # type: ignore[reportPrivateUsage]
        assert host._elicitor is mock_elicitor  # type: ignore[reportPrivateUsage]
        assert host._roots is mock_roots  # type: ignore[reportPrivateUsage]


def test_mcp_session_host_from_config_with_nones() -> None:
    """Test McpSessionHost _from_config method with None components."""
    from autogen_ext.tools.mcp._host._session_host import McpSessionHostConfig

    config = McpSessionHostConfig(sampler=None, elicitor=None, roots=None)

    host = McpSessionHost._from_config(config)  # type: ignore[reportPrivateUsage]

    assert host._sampler is None  # type: ignore[reportPrivateUsage]
    assert host._elicitor is None  # type: ignore[reportPrivateUsage]
    assert host._roots is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_with_sampler_exception() -> None:
    """Test McpSessionHost handles sampler exceptions (lines 143-147)."""
    mock_sampler = MagicMock()
    mock_sampler.sample = AsyncMock(side_effect=RuntimeError("Sampler failed"))

    host = McpSessionHost(sampler=mock_sampler)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INTERNAL_ERROR
    assert "Sampling request failed" in result.message
    assert "Sampler failed" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_elicit_with_elicitor_exception() -> None:
    """Test McpSessionHost handles elicitor exceptions (lines 169-172)."""
    mock_elicitor = MagicMock()
    mock_elicitor.elicit = AsyncMock(side_effect=ValueError("Elicitor failed"))

    host = McpSessionHost(elicitor=mock_elicitor)

    params = mcp_types.ElicitRequestParams(message="Test", requestedSchema={})

    result = await host.handle_elicit_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INTERNAL_ERROR
    assert "Elicitation request failed" in result.message
    assert "Elicitor failed" in result.message
