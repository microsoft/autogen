"""Tests for Cohere chat completion client."""

import asyncio
import logging
import os
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    ModelInfo,
    SystemMessage,
    UserMessage,
)
from autogen_core.models._types import LLMMessage
from autogen_core.tools import FunctionTool
from autogen_ext.models.cohere import CohereChatCompletionClient


def _pass_function(input: str) -> str:
    """Simple passthrough function."""
    return f"Processed: {input}"


def _add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@pytest.mark.asyncio
async def test_mock_basic_completion() -> None:
    """Test basic completion with mocks."""
    # Create mock client and response
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.message.content = "Hello! I'm here to help."
    mock_response.finish_reason = "COMPLETE"
    mock_response.usage.tokens.input_tokens = 10
    mock_response.usage.tokens.output_tokens = 5

    mock_client.chat = AsyncMock(return_value=mock_response)

    # Create real client but patch the underlying Cohere client
    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key="test-key",
    )

    messages: List[LLMMessage] = [
        UserMessage(content="Hello", source="user"),
    ]

    with patch.object(client, "_client", mock_client):
        result = await client.create(messages=messages)

    # Verify the result
    assert isinstance(result.content, str)
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5


@pytest.mark.asyncio
async def test_mock_tool_calling() -> None:
    """Test tool calling with mocks."""
    # Create mock client and response
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Mock tool call response
    mock_tool_call = MagicMock()
    mock_tool_call.type = "tool_call"
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "add_numbers"
    mock_tool_call.function.arguments = '{"a": 1, "b": 2}'

    mock_response.message.content = [mock_tool_call]
    mock_response.finish_reason = "TOOL_CALL"
    mock_response.usage.tokens.input_tokens = 15
    mock_response.usage.tokens.output_tokens = 10

    mock_client.chat = AsyncMock(return_value=mock_response)

    # Create real client but patch the underlying Cohere client
    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key="test-key",
    )

    # Define tools
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages: List[LLMMessage] = [
        UserMessage(content="Add 1 and 2", source="user"),
    ]

    with patch.object(client, "_client", mock_client):
        result = await client.create(
            messages=messages,
            tools=[add_tool],
        )

    # Verify the result
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "add_numbers"
    assert result.finish_reason == "function_calls"


@pytest.mark.asyncio
async def test_model_info() -> None:
    """Test that model info is correctly set."""
    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key="test-key",
    )

    capabilities = client.capabilities
    assert capabilities["function_calling"] is True
    assert capabilities["json_output"] is True
    assert capabilities["structured_output"] is True
    assert capabilities["vision"] is False


@pytest.mark.asyncio
async def test_token_counting() -> None:
    """Test token counting methods."""
    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key="test-key",
    )

    messages: List[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Hello!", source="user"),
    ]

    # Test count_tokens (approximation)
    token_count = client.count_tokens(messages)
    assert token_count > 0

    # Test remaining_tokens
    remaining = client.remaining_tokens(messages)
    assert remaining > 0


@pytest.mark.skipif(
    "COHERE_API_KEY" not in os.environ,
    reason="COHERE_API_KEY not set",
)
@pytest.mark.asyncio
async def test_cohere_basic_completion(caplog: pytest.LogCaptureFixture) -> None:
    """Test basic completion with actual Cohere API."""
    caplog.set_level(logging.INFO)

    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key=os.environ["COHERE_API_KEY"],
    )

    messages: List[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="What is 2+2? Answer with just the number.", source="user"),
    ]

    result = await client.create(messages=messages)

    # Verify response
    assert isinstance(result.content, str)
    assert len(result.content) > 0
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.finish_reason in ["stop", "length"]

    # Check logging
    assert any("LLMCallEvent" in record.message for record in caplog.records)


@pytest.mark.skipif(
    "COHERE_API_KEY" not in os.environ,
    reason="COHERE_API_KEY not set",
)
@pytest.mark.asyncio
async def test_cohere_streaming(caplog: pytest.LogCaptureFixture) -> None:
    """Test streaming with actual Cohere API."""
    caplog.set_level(logging.INFO)

    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key=os.environ["COHERE_API_KEY"],
    )

    messages: List[LLMMessage] = [
        UserMessage(content="Count from 1 to 5.", source="user"),
    ]

    chunks: List[str] = []
    final_result = None

    async for chunk in client.create_stream(messages=messages):
        if isinstance(chunk, str):
            chunks.append(chunk)
        else:
            final_result = chunk

    # Verify streaming response
    assert len(chunks) > 0
    assert final_result is not None
    assert isinstance(final_result, CreateResult)
    assert final_result.usage.prompt_tokens > 0
    assert final_result.usage.completion_tokens > 0


@pytest.mark.skipif(
    "COHERE_API_KEY" not in os.environ,
    reason="COHERE_API_KEY not set",
)
@pytest.mark.asyncio
async def test_cohere_tool_calling() -> None:
    """Test tool calling with actual Cohere API."""
    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key=os.environ["COHERE_API_KEY"],
    )

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages: List[LLMMessage] = [
        UserMessage(content="Add the numbers 5 and 7 together.", source="user"),
    ]

    result = await client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
    )

    # Verify tool call
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "add_numbers"


@pytest.mark.asyncio
async def test_serialization() -> None:
    """Test client serialization."""
    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key="test-key",
    )

    # Test config serialization
    config = client._to_config()
    assert config.model == "command-r-08-2024"

    # Test creating from config
    new_client = CohereChatCompletionClient._from_config(config)
    assert new_client._create_args["model"] == "command-r-08-2024"


@pytest.mark.asyncio
async def test_usage_tracking() -> None:
    """Test usage tracking."""
    # Create mock client and response
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.message.content = "Test response"
    mock_response.finish_reason = "COMPLETE"
    mock_response.usage.tokens.input_tokens = 10
    mock_response.usage.tokens.output_tokens = 5

    mock_client.chat = AsyncMock(return_value=mock_response)

    client = CohereChatCompletionClient(
        model="command-r-08-2024",
        api_key="test-key",
    )

    messages: List[LLMMessage] = [
        UserMessage(content="Hello", source="user"),
    ]

    # Initial usage should be zero
    assert client.total_usage().prompt_tokens == 0
    assert client.total_usage().completion_tokens == 0

    with patch.object(client, "_client", mock_client):
        await client.create(messages=messages)

    # After one call
    assert client.actual_usage().prompt_tokens == 10
    assert client.actual_usage().completion_tokens == 5
    assert client.total_usage().prompt_tokens == 10
    assert client.total_usage().completion_tokens == 5

    with patch.object(client, "_client", mock_client):
        await client.create(messages=messages)

    # After two calls
    assert client.actual_usage().prompt_tokens == 10
    assert client.actual_usage().completion_tokens == 5
    assert client.total_usage().prompt_tokens == 20
    assert client.total_usage().completion_tokens == 10
