import asyncio
import logging
import os
from typing import List, Sequence

import pytest
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.models._types import LLMMessage
from autogen_core.tools import FunctionTool
from autogen_ext.models.anthropic import AnthropicChatCompletionClient


def _pass_function(input: str) -> str:
    """Simple passthrough function."""
    return f"Processed: {input}"


def _add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@pytest.mark.asyncio
async def test_anthropic_basic_completion(caplog: pytest.LogCaptureFixture) -> None:
    """Test basic message completion with Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",  # Use haiku for faster/cheaper testing
        api_key=api_key,
        temperature=0.0,  # Added temperature param to test
        stop_sequences=["STOP"],  # Added stop sequence
    )

    # Test basic completion
    with caplog.at_level(logging.INFO):
        result = await client.create(
            messages=[
                SystemMessage(content="You are a helpful assistant."),
                UserMessage(content="What's 2+2? Answer with just the number.", source="user"),
            ]
        )

        assert isinstance(result.content, str)
        assert "4" in result.content
        assert result.finish_reason == "stop"
        assert "LLMCall" in caplog.text and result.content in caplog.text

    # Test JSON output - add to existing test
    json_result = await client.create(
        messages=[
            UserMessage(content="Return a JSON with key 'value' set to 42", source="user"),
        ],
        json_output=True,
    )
    assert isinstance(json_result.content, str)
    assert "42" in json_result.content

    # Check usage tracking
    usage = client.total_usage()
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0


@pytest.mark.asyncio
async def test_anthropic_streaming(caplog: pytest.LogCaptureFixture) -> None:
    """Test streaming capabilities with Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    # Test streaming completion
    chunks: List[str | CreateResult] = []
    prompt = "Count from 1 to 5. Each number on its own line."
    with caplog.at_level(logging.INFO):
        async for chunk in client.create_stream(
            messages=[
                UserMessage(content=prompt, source="user"),
            ]
        ):
            chunks.append(chunk)
        # Verify we got multiple chunks
        assert len(chunks) > 1

        # Check final result
        final_result = chunks[-1]
        assert isinstance(final_result, CreateResult)
        assert final_result.finish_reason == "stop"

        assert "LLMStreamStart" in caplog.text
        assert "LLMStreamEnd" in caplog.text
        assert isinstance(final_result.content, str)
        for i in range(1, 6):
            assert str(i) in caplog.text
        assert prompt in caplog.text

    # Check content contains numbers 1-5
    assert isinstance(final_result.content, str)
    combined_content = final_result.content
    for i in range(1, 6):
        assert str(i) in combined_content


@pytest.mark.asyncio
async def test_anthropic_tool_calling() -> None:
    """Test tool calling capabilities with Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    # Test tool calling with instruction to use specific tool
    messages: List[LLMMessage] = [
        SystemMessage(content="Use the tools available to help the user."),
        UserMessage(content="Process the text 'hello world' using the process_text tool.", source="user"),
    ]

    result = await client.create(messages=messages, tools=[pass_tool, add_tool])

    # Check that we got a tool call
    assert isinstance(result.content, list)
    assert len(result.content) >= 1
    assert isinstance(result.content[0], FunctionCall)

    # Check that the correct tool was called
    function_call = result.content[0]
    assert function_call.name == "process_text"

    # Test tool response handling
    messages.append(AssistantMessage(content=result.content, source="assistant"))
    messages.append(
        FunctionExecutionResultMessage(
            content=[
                FunctionExecutionResult(
                    content="Processed: hello world",
                    call_id=result.content[0].id,
                    is_error=False,
                    name=result.content[0].name,
                )
            ]
        )
    )

    # Get response after tool execution
    after_tool_result = await client.create(messages=messages)

    # Check we got a text response
    assert isinstance(after_tool_result.content, str)

    # Test multiple tool use
    multi_tool_prompt: List[LLMMessage] = [
        SystemMessage(content="Use the tools as needed to help the user."),
        UserMessage(content="First process the text 'test' and then add 2 and 3.", source="user"),
    ]

    multi_tool_result = await client.create(messages=multi_tool_prompt, tools=[pass_tool, add_tool])

    # We just need to verify we get at least one tool call
    assert isinstance(multi_tool_result.content, list)
    assert len(multi_tool_result.content) > 0
    assert isinstance(multi_tool_result.content[0], FunctionCall)


@pytest.mark.asyncio
async def test_anthropic_token_counting() -> None:
    """Test token counting functionality."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    messages: Sequence[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Hello, how are you?", source="user"),
    ]

    # Test token counting
    num_tokens = client.count_tokens(messages)
    assert num_tokens > 0

    # Test remaining token calculation
    remaining = client.remaining_tokens(messages)
    assert remaining > 0
    assert remaining < 200000  # Claude's max context

    # Test token counting with tools
    tools = [
        FunctionTool(_pass_function, description="Process input text", name="process_text"),
        FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers"),
    ]
    tokens_with_tools = client.count_tokens(messages, tools=tools)
    assert tokens_with_tools > num_tokens  # Should be more tokens with tools


@pytest.mark.asyncio
async def test_anthropic_cancellation() -> None:
    """Test cancellation of requests."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    # Create a cancellation token
    cancellation_token = CancellationToken()

    # Schedule cancellation after a short delay
    async def cancel_after_delay() -> None:
        await asyncio.sleep(0.5)  # Short delay
        cancellation_token.cancel()

    # Start task to cancel request
    asyncio.create_task(cancel_after_delay())

    # Create a request with long output
    with pytest.raises(asyncio.CancelledError):
        await client.create(
            messages=[
                UserMessage(content="Write a detailed 5-page essay on the history of computing.", source="user"),
            ],
            cancellation_token=cancellation_token,
        )


@pytest.mark.asyncio
async def test_anthropic_multimodal() -> None:
    """Test multimodal capabilities with Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    # Skip if PIL is not available
    try:
        from autogen_core import Image
        from PIL import Image as PILImage
    except ImportError:
        pytest.skip("PIL or other dependencies not installed")

    client = AnthropicChatCompletionClient(
        model="claude-3-5-sonnet-latest",  # Use a model that supports vision
        api_key=api_key,
    )

    # Use a simple test image that's reliable
    # 1. Create a simple colored square image
    width, height = 100, 100
    color = (255, 0, 0)  # Red
    pil_image = PILImage.new("RGB", (width, height), color)

    # 2. Convert to autogen_core Image format
    img = Image(pil_image)

    # Test multimodal message
    result = await client.create(
        messages=[
            UserMessage(content=["What color is this square? Answer in one word.", img], source="user"),
        ]
    )

    # Verify we got a response describing the image
    assert isinstance(result.content, str)
    assert len(result.content) > 0
    assert "red" in result.content.lower()
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_anthropic_serialization() -> None:
    """Test serialization and deserialization of component."""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    # Serialize and deserialize
    model_client_config = client.dump_component()
    assert model_client_config is not None
    assert model_client_config.config is not None

    loaded_model_client = AnthropicChatCompletionClient.load_component(model_client_config)
    assert loaded_model_client is not None
    assert isinstance(loaded_model_client, AnthropicChatCompletionClient)
