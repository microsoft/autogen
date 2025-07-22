"""Tests for McpSessionHost to cover MCP host functionality."""

import atexit
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
from autogen_ext.tools.mcp.host import (
    ChatCompletionClientElicitor,
    GroupChatAgentElicitor,
    McpSessionHost,
)
from autogen_ext.tools.mcp.host._utils import (
    finish_reason_to_stop_reason,
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


@pytest.mark.asyncio
async def test_agent_elicitor_initialization() -> None:
    """Test GroupChatAgentElicitor initialization."""
    mock_model_client = MagicMock()
    recipient = "test_agent"

    elicitor = GroupChatAgentElicitor(recipient=recipient, model_client=mock_model_client)

    assert elicitor._recipient == recipient  # type: ignore[reportPrivateUsage]
    assert elicitor._model_client == mock_model_client  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_agent_elicitor_elicit_method() -> None:
    """Test GroupChatAgentElicitor elicit method requires group chat setup."""
    mock_model_client = MagicMock()
    recipient = "test_agent"
    elicitor = GroupChatAgentElicitor(recipient=recipient, model_client=mock_model_client)
    params = mcp_types.ElicitRequestParams(message="Test elicitation message", requestedSchema={"type": "object"})

    # Should raise RuntimeError when group chat is not set
    with pytest.raises(RuntimeError, match="Group chat must be set"):
        await elicitor.elicit(params)


@pytest.mark.asyncio
async def test_agent_elicitor_set_group_chat() -> None:
    """Test GroupChatAgentElicitor set_group_chat method."""
    mock_model_client = MagicMock()
    recipient = "test_agent"
    elicitor = GroupChatAgentElicitor(recipient=recipient, model_client=mock_model_client)

    # Initially no group chat set
    assert elicitor._group_chat is None  # type: ignore[reportPrivateUsage]

    # Set group chat
    mock_group_chat = MagicMock()
    elicitor.set_group_chat(mock_group_chat)

    # Verify group chat was set
    assert elicitor._group_chat == mock_group_chat  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_agent_elicitor_full_elicit_flow() -> None:
    """Test GroupChatAgentElicitor complete elicit flow with mocked group chat."""
    from autogen_agentchat.base._chat_agent import Response
    from autogen_agentchat.messages import TextMessage

    # Set up mocks
    mock_model_client = MagicMock()
    mock_model_client.create = AsyncMock(
        return_value=CreateResult(
            content='{"action": "accept", "content": {"test": "response"}}',
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )

    recipient = "test_agent"
    elicitor = GroupChatAgentElicitor(recipient=recipient, model_client=mock_model_client)

    # Mock group chat and runtime
    mock_response_message = TextMessage(content="User provided test response", source="agent")
    mock_agent_response = Response(chat_message=mock_response_message)

    mock_runtime = MagicMock()
    mock_runtime.publish_message = AsyncMock()
    mock_runtime.send_message = AsyncMock(return_value=mock_agent_response)

    mock_group_chat = MagicMock()
    mock_group_chat._runtime = mock_runtime
    mock_group_chat._team_id = "test_team"
    mock_group_chat._group_chat_manager_topic_type = "test_manager"

    # Set group chat
    elicitor.set_group_chat(mock_group_chat)

    # Test elicit
    params = mcp_types.ElicitRequestParams(
        message="Test elicitation message",
        requestedSchema={"type": "object", "properties": {"test": {"type": "string"}}},
    )

    result = await elicitor.elicit(params)

    # Verify result
    assert isinstance(result, mcp_types.ElicitResult)
    assert result.action == "accept"
    assert result.content == {"test": "response"}

    # Verify runtime interactions
    assert mock_runtime.publish_message.call_count == 2  # Elicit message + response message
    mock_runtime.send_message.assert_called_once()

    # Verify model client was called with proper messages
    mock_model_client.create.assert_called_once()
    call_args = mock_model_client.create.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 3  # SystemMessage, AssistantMessage, UserMessage

    # Check message types and content
    from autogen_core.models import AssistantMessage, SystemMessage, UserMessage

    assert isinstance(messages[0], SystemMessage)
    assert "Convert all user messages to the following json format" in messages[0].content
    assert isinstance(messages[1], AssistantMessage)
    assert messages[1].content == "Test elicitation message"
    assert messages[1].source == recipient
    assert isinstance(messages[2], UserMessage)
    assert messages[2].content == "User provided test response"


def test_agent_elicitor_to_config() -> None:
    """Test GroupChatAgentElicitor _to_config method."""
    mock_model_client = MagicMock()
    mock_model_client.dump_component = MagicMock(return_value={"type": "mock_model", "config": {}})
    recipient = "test_agent"
    elicitor = GroupChatAgentElicitor(recipient=recipient, model_client=mock_model_client)

    config = elicitor._to_config()  # type: ignore[reportPrivateUsage]

    from autogen_ext.tools.mcp.host._elicitors import GroupChatAgentElicitorConfig

    assert isinstance(config, GroupChatAgentElicitorConfig)
    assert config.recipient == recipient
    assert config.model_client == {"type": "mock_model", "config": {}}


def test_agent_elicitor_from_config() -> None:
    """Test GroupChatAgentElicitor _from_config method."""
    from autogen_core.models import ChatCompletionClient
    from autogen_ext.tools.mcp.host._elicitors import GroupChatAgentElicitorConfig

    recipient = "test_agent"
    model_config = MagicMock()
    config = GroupChatAgentElicitorConfig(recipient=recipient, model_client=model_config)

    # Mock the ChatCompletionClient.load_component method
    mock_model_client = MagicMock()
    mock_load_component = MagicMock(return_value=mock_model_client)
    with patch.object(ChatCompletionClient, "load_component", mock_load_component):
        elicitor = GroupChatAgentElicitor._from_config(config)  # type: ignore[reportPrivateUsage]

        assert elicitor._recipient == recipient  # type: ignore[reportPrivateUsage]
        assert elicitor._model_client == mock_model_client  # type: ignore[reportPrivateUsage]
        # Verify the load_component was called with the right config
        mock_load_component.assert_called_once_with(model_config)


def test_model_elicitor_initialization() -> None:
    """Test ChatCompletionClientElicitor initialization (lines 133-134)."""
    mock_model_client = MagicMock()
    system_prompt = "You are a helpful assistant"

    elicitor = ChatCompletionClientElicitor(model_client=mock_model_client, system_prompt=system_prompt)

    assert elicitor.model_client == mock_model_client
    assert elicitor.system_prompt == system_prompt


@pytest.mark.asyncio
async def test_model_elicitor_elicit_with_system_prompt() -> None:
    """Test ChatCompletionClientElicitor elicit method with system prompt (lines 137-147)."""
    # Mock the model client to return the expected CreateResult format for structured output
    mock_create_result = MagicMock(spec=CreateResult)
    mock_create_result.content = '{"action": "accept", "content": {"reasoning": "test"}}'
    mock_create_result.finish_reason = "stop"
    mock_create_result.usage = RequestUsage(prompt_tokens=10, completion_tokens=5)
    mock_create_result.cached = False

    mock_model_client = MagicMock()
    mock_model_client.create = AsyncMock(return_value=mock_create_result)

    system_prompt = "You are a helpful assistant"
    elicitor = ChatCompletionClientElicitor(model_client=mock_model_client, system_prompt=system_prompt)

    params = mcp_types.ElicitRequestParams(message="Test elicitation message", requestedSchema={"type": "object"})

    result = await elicitor.elicit(params)

    assert isinstance(result, mcp_types.ElicitResult)
    assert result.action == "accept"
    assert result.content == {"reasoning": "test"}

    # Verify that system message was included
    mock_model_client.create.assert_called_once()
    call_args = mock_model_client.create.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 2  # SystemMessage + UserMessage
    from autogen_core.models import SystemMessage

    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == system_prompt
    assert isinstance(messages[1], UserMessage)
    # The user message should contain the original message plus JSON schema instructions
    assert "Test elicitation message" in messages[1].content
    assert "Respond in this json format:" in messages[1].content


@pytest.mark.asyncio
async def test_model_elicitor_elicit_without_system_prompt() -> None:
    """Test ChatCompletionClientElicitor elicit method without system prompt."""
    mock_model_client = MagicMock()
    mock_model_client.create = AsyncMock(
        return_value=CreateResult(
            content='{"action": "decline", "content": {"reason": "not interested"}}',
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=5, completion_tokens=3),
            cached=False,
        )
    )

    # No system prompt provided
    elicitor = ChatCompletionClientElicitor(model_client=mock_model_client, system_prompt=None)

    params = mcp_types.ElicitRequestParams(message="Test message", requestedSchema={"type": "object"})

    result = await elicitor.elicit(params)

    assert isinstance(result, mcp_types.ElicitResult)
    assert result.action == "decline"
    assert result.content == {"reason": "not interested"}

    # Verify that only UserMessage was included (no system message)
    mock_model_client.create.assert_called_once()
    call_args = mock_model_client.create.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 1  # Only UserMessage
    from autogen_core.models import UserMessage

    assert isinstance(messages[0], UserMessage)
    assert "Test message" in messages[0].content
    assert "Respond in this json format:" in messages[0].content


def test_model_elicitor_to_config() -> None:
    """Test ChatCompletionClientElicitor _to_config method (line 150)."""
    mock_model_client = MagicMock()
    mock_model_client.dump_component = MagicMock(return_value={"type": "mock_model", "config": {}})
    system_prompt = "You are a helpful assistant"

    elicitor = ChatCompletionClientElicitor(model_client=mock_model_client, system_prompt=system_prompt)

    config = elicitor._to_config()  # type: ignore[reportPrivateUsage]

    from autogen_ext.tools.mcp.host._elicitors import ChatCompletionClientElicitorConfig

    assert isinstance(config, ChatCompletionClientElicitorConfig)
    assert config.model_client == {"type": "mock_model", "config": {}}
    assert config.system_prompt == system_prompt


def test_model_elicitor_from_config() -> None:
    """Test ChatCompletionClientElicitor _from_config method (line 154)."""
    from autogen_core.models import ChatCompletionClient
    from autogen_ext.tools.mcp.host._elicitors import ChatCompletionClientElicitorConfig

    model_config = MagicMock()
    system_prompt = "Test system prompt"
    config = ChatCompletionClientElicitorConfig(model_client=model_config, system_prompt=system_prompt)

    # Mock the ChatCompletionClient.load_component method
    mock_model_client = MagicMock()
    mock_load_component = MagicMock(return_value=mock_model_client)
    with patch.object(ChatCompletionClient, "load_component", mock_load_component):
        elicitor = ChatCompletionClientElicitor._from_config(config)  # type: ignore[reportPrivateUsage]

        assert elicitor.model_client == mock_model_client
        assert elicitor.system_prompt == system_prompt
        # Verify the load_component was called with the right config
        mock_load_component.assert_called_once_with(model_config)


# McpSessionHost integration tests
@pytest.mark.asyncio
async def test_mcp_session_host_sampling_request(mock_model_client: Any) -> None:
    """Test McpSessionHost handles sampling requests correctly."""
    host = McpSessionHost(model_client=mock_model_client)

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
async def test_mcp_session_host_sampling_request_no_model() -> None:
    """Test McpSessionHost returns error when no model client available."""
    host = McpSessionHost(model_client=None)

    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await host.handle_sampling_request(params)

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "No model client available" in result.message


@pytest.mark.asyncio
async def test_mcp_session_host_sampling_request_with_system_prompt(mock_model_client: Any) -> None:
    """Test McpSessionHost handles sampling requests with system prompt."""
    host = McpSessionHost(model_client=mock_model_client)

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

    host = McpSessionHost(model_client=mock_model_client)

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
    mock_elicitor = MagicMock(spec=ChatCompletionClientElicitor)
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
    mock_elicitor = MagicMock(spec=ChatCompletionClientElicitor)
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

    host = McpSessionHost(roots=test_roots)

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

    def get_roots() -> list[mcp_types.Root]:
        return test_roots

    host = McpSessionHost(roots=get_roots)

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

    async def get_roots_async() -> list[mcp_types.Root]:
        return test_roots

    # Cast to the expected type since async callable is supported
    host = McpSessionHost(roots=get_roots_async)  # type: ignore[arg-type]

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

    def failing_get_roots() -> list[mcp_types.Root]:
        raise Exception("Roots error")

    host = McpSessionHost(roots=failing_get_roots)

    result = await host.handle_list_roots_request()

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INTERNAL_ERROR
    assert "Caught error listing roots" in result.message


def test_mcp_session_host_config_serialization(mock_model_client: Any) -> None:
    """Test McpSessionHost config serialization/deserialization."""
    # Create a mock elicitor with proper dump_component method
    mock_elicitor = MagicMock(spec=ChatCompletionClientElicitor)
    mock_elicitor.dump_component = MagicMock(return_value={"type": "mock_elicitor", "config": {}})

    # Mock the model client's dump_component method
    mock_model_client.dump_component = MagicMock(return_value={"type": "mock_model", "config": {}})

    from pydantic import FileUrl

    test_roots = [
        mcp_types.Root(uri=FileUrl("file:///config_test"), name="Config Test Root"),
    ]

    host = McpSessionHost(model_client=mock_model_client, roots=test_roots, elicitor=mock_elicitor)

    # Test config serialization
    config = host._to_config()  # type: ignore[reportPrivateUsage]
    from autogen_ext.tools.mcp.host._session_host import McpSessionHostConfig

    assert isinstance(config, McpSessionHostConfig)
    assert config.model_client is not None
    assert config.elicitor is not None
    assert config.roots is not None
    assert len(config.roots) == 1
    assert str(config.roots[0].uri) == "file:///config_test"


def test_mcp_session_host_from_config() -> None:
    """Test McpSessionHost _from_config method (line 309)."""
    from autogen_core.models import ChatCompletionClient
    from autogen_ext.tools.mcp.host._elicitors import Elicitor
    from autogen_ext.tools.mcp.host._session_host import McpSessionHostConfig
    from pydantic import FileUrl

    # Create mock components
    mock_model_client = MagicMock()
    mock_elicitor = MagicMock()

    model_config = MagicMock()
    elicitor_config = MagicMock()
    test_roots = [mcp_types.Root(uri=FileUrl("file:///config_test"), name="Config Test Root")]

    config = McpSessionHostConfig(model_client=model_config, elicitor=elicitor_config, roots=test_roots)

    # Mock the load_component methods
    mock_model_load = MagicMock(return_value=mock_model_client)
    mock_elicitor_load = MagicMock(return_value=mock_elicitor)

    with (
        patch.object(ChatCompletionClient, "load_component", mock_model_load),
        patch.object(Elicitor, "load_component", mock_elicitor_load),
    ):
        host = McpSessionHost._from_config(config)  # type: ignore[reportPrivateUsage]

        assert host._model_client == mock_model_client  # type: ignore[reportPrivateUsage]
        assert host._elicitor == mock_elicitor  # type: ignore[reportPrivateUsage]
        assert host._roots == test_roots  # type: ignore[reportPrivateUsage]

        # Verify the load_component calls were made with correct configs
        mock_model_load.assert_called_once_with(model_config)
        mock_elicitor_load.assert_called_once_with(elicitor_config)


def test_mcp_session_host_initialization() -> None:
    """Test McpSessionHost initialization."""
    host = McpSessionHost()

    assert host._model_client is None  # type: ignore[reportPrivateUsage]
    assert host._roots is None  # type: ignore[reportPrivateUsage]
    assert host._elicitor is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_mcp_session_host_with_vision_model(mock_model_client_with_vision: Any) -> None:
    """Test McpSessionHost handles image content with vision-enabled model."""
    host = McpSessionHost(model_client=mock_model_client_with_vision)

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
    host = McpSessionHost(model_client=mock_model_client)

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

    host = McpSessionHost(model_client=mock_model_client)

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
