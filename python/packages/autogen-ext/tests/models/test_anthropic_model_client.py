import asyncio
import json
import logging
import os
from typing import List, Sequence
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
from autogen_ext.models.anthropic import (
    AnthropicBedrockChatCompletionClient,
    AnthropicChatCompletionClient,
    BaseAnthropicChatCompletionClient,
    BedrockInfo,
)


def _pass_function(input: str) -> str:
    """Simple passthrough function."""
    return f"Processed: {input}"


def _add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def _ask_for_input() -> str:
    """Function that asks for user input. Used to test empty input handling, such as in `pass_to_user` tool."""
    return "Further input from user"


@pytest.mark.asyncio
async def test_mock_tool_choice_specific_tool() -> None:
    """Test tool_choice parameter with a specific tool using mocks."""
    # Create mock client and response
    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="tool_use", name="process_text", input={"input": "hello"}, id="call_123")]
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5

    mock_client.messages.create.return_value = mock_message

    # Create real client but patch the underlying Anthropic client
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key="test-key",
    )

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages: List[LLMMessage] = [
        UserMessage(content="Process the text 'hello'.", source="user"),
    ]

    with patch.object(client, "_client", mock_client):
        await client.create(
            messages=messages,
            tools=[pass_tool, add_tool],
            tool_choice=pass_tool,  # Force use of specific tool
        )

    # Verify the correct API call was made
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args

    # Check that tool_choice was set correctly
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == {"type": "tool", "name": "process_text"}


@pytest.mark.asyncio
async def test_mock_tool_choice_auto() -> None:
    """Test tool_choice parameter with 'auto' setting using mocks."""
    # Create mock client and response
    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="tool_use", name="add_numbers", input={"a": 1, "b": 2}, id="call_123")]
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5

    mock_client.messages.create.return_value = mock_message

    # Create real client but patch the underlying Anthropic client
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key="test-key",
    )

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages: List[LLMMessage] = [
        UserMessage(content="Add 1 and 2.", source="user"),
    ]

    with patch.object(client, "_client", mock_client):
        await client.create(
            messages=messages,
            tools=[pass_tool, add_tool],
            tool_choice="auto",  # Let model choose
        )

    # Verify the correct API call was made
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args

    # Check that tool_choice was set correctly
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == {"type": "auto"}


@pytest.mark.asyncio
async def test_mock_tool_choice_none() -> None:
    """Test tool_choice parameter when no tools are provided - tool_choice should not be included."""
    # Create mock client and response
    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="text", text="I can help you with that.")]
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5

    mock_client.messages.create.return_value = mock_message

    # Create real client but patch the underlying Anthropic client
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key="test-key",
    )

    messages: List[LLMMessage] = [
        UserMessage(content="Hello there.", source="user"),
    ]

    with patch.object(client, "_client", mock_client):
        await client.create(
            messages=messages,
            # No tools provided - tool_choice should not be included in API call
        )

    # Verify the correct API call was made
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args

    # Check that tool_choice was not set when no tools are provided
    assert "tool_choice" not in call_args.kwargs


@pytest.mark.asyncio
async def test_mock_tool_choice_validation_error() -> None:
    """Test tool_choice validation with invalid tool reference."""
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key="test-key",
    )

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")
    different_tool = FunctionTool(_pass_function, description="Different tool", name="different_tool")

    messages: List[LLMMessage] = [
        UserMessage(content="Hello there.", source="user"),
    ]

    # Test with a tool that's not in the tools list
    with pytest.raises(ValueError, match="tool_choice references 'different_tool' but it's not in the available tools"):
        await client.create(
            messages=messages,
            tools=[pass_tool, add_tool],
            tool_choice=different_tool,  # This tool is not in the tools list
        )


@pytest.mark.asyncio
async def test_mock_serialization_api_key() -> None:
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",  # Use haiku for faster/cheaper testing
        api_key="sk-password",
        temperature=0.0,  # Added temperature param to test
        stop_sequences=["STOP"],  # Added stop sequence
    )
    assert client
    config = client.dump_component()
    assert config
    assert "sk-password" not in str(config)
    serialized_config = config.model_dump_json()
    assert serialized_config
    assert "sk-password" not in serialized_config
    client2 = AnthropicChatCompletionClient.load_component(config)
    assert client2

    bedrock_client = AnthropicBedrockChatCompletionClient(
        model="claude-3-haiku-20240307",  # Use haiku for faster/cheaper testing
        api_key="sk-password",
        model_info=ModelInfo(
            vision=False, function_calling=True, json_output=False, family="unknown", structured_output=True
        ),
        bedrock_info=BedrockInfo(
            aws_access_key="<aws_access_key>",
            aws_secret_key="<aws_secret_key>",
            aws_session_token="<aws_session_token>",
            aws_region="<aws_region>",
        ),
    )
    assert bedrock_client
    bedrock_config = bedrock_client.dump_component()
    assert bedrock_config
    assert "sk-password" not in str(bedrock_config)
    serialized_bedrock_config = bedrock_config.model_dump_json()
    assert serialized_bedrock_config
    assert "sk-password" not in serialized_bedrock_config
    bedrock_client2 = AnthropicBedrockChatCompletionClient.load_component(bedrock_config)
    assert bedrock_client2


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
async def test_mock_serialization() -> None:
    """Test serialization and deserialization of component."""

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key="api-key",
    )

    # Serialize and deserialize
    model_client_config = client.dump_component()
    assert model_client_config is not None
    assert model_client_config.config is not None

    loaded_model_client = AnthropicChatCompletionClient.load_component(model_client_config)
    assert loaded_model_client is not None
    assert isinstance(loaded_model_client, AnthropicChatCompletionClient)


@pytest.mark.asyncio
async def test_anthropic_message_serialization_with_tools(caplog: pytest.LogCaptureFixture) -> None:
    """Test that complex messages with tool calls are properly serialized in logs."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    # Use existing tools from the test file
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    # Set up logging capture - capture all loggers
    with caplog.at_level(logging.INFO):
        # Make a request that should trigger a tool call
        await client.create(
            messages=[
                SystemMessage(content="Use the tools available to help the user."),
                UserMessage(content="Process the text 'hello world' using the process_text tool.", source="user"),
            ],
            tools=[pass_tool, add_tool],
        )

        # Look for any log containing serialized messages, not just with 'LLMCallEvent'
        serialized_message_logs = [
            record for record in caplog.records if '"messages":' in str(record.msg) or "messages" in str(record.msg)
        ]

        # Verify we have at least one log with serialized messages
        assert len(serialized_message_logs) > 0, "No logs with serialized messages found"


@pytest.mark.asyncio
async def test_anthropic_muliple_system_message() -> None:
    """Test multiple system messages in a single request."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )
    # Test multiple system messages
    messages: List[LLMMessage] = [
        SystemMessage(content="When you say anything Start with 'FOO'"),
        SystemMessage(content="When you say anything End with 'BAR'"),
        UserMessage(content="Just say '.'", source="user"),
    ]

    result = await client.create(messages=messages)
    result_content = result.content
    assert isinstance(result_content, str)
    result_content = result_content.strip()
    assert result_content[:3] == "FOO"
    assert result_content[-3:] == "BAR"


def test_mock_merge_continuous_system_messages() -> None:
    """Tests merging of continuous system messages."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        SystemMessage(content="System instruction 1"),
        SystemMessage(content="System instruction 2"),
        UserMessage(content="User question", source="user"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it

    # 병합 후 2개 메시지만 남아야 함 (시스템 1개, 사용자 1개)
    assert len(merged_messages) == 2

    # 첫 번째 메시지는 병합된 시스템 메시지여야 함
    assert isinstance(merged_messages[0], SystemMessage)
    assert merged_messages[0].content == "System instruction 1\nSystem instruction 2"

    # 두 번째 메시지는 사용자 메시지여야 함
    assert isinstance(merged_messages[1], UserMessage)
    assert merged_messages[1].content == "User question"


def test_mock_merge_single_system_message() -> None:
    """Tests that a single system message remains unchanged."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        SystemMessage(content="Single system instruction"),
        UserMessage(content="User question", source="user"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it

    # 메시지 개수는 변하지 않아야 함
    assert len(merged_messages) == 2

    # 시스템 메시지 내용은 변하지 않아야 함
    assert isinstance(merged_messages[0], SystemMessage)
    assert merged_messages[0].content == "Single system instruction"


def test_mock_merge_no_system_messages() -> None:
    """Tests behavior when there are no system messages."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        UserMessage(content="User question without system", source="user"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it

    # 메시지 개수는 변하지 않아야 함
    assert len(merged_messages) == 1

    # 유일한 메시지는 사용자 메시지여야 함
    assert isinstance(merged_messages[0], UserMessage)
    assert merged_messages[0].content == "User question without system"


def test_mock_merge_non_continuous_system_messages() -> None:
    """Tests that an error is raised for non-continuous system messages."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        SystemMessage(content="First group 1"),
        SystemMessage(content="First group 2"),
        UserMessage(content="Middle user message", source="user"),
        SystemMessage(content="Second group 1"),
        SystemMessage(content="Second group 2"),
    ]

    # 연속적이지 않은 시스템 메시지는 에러를 발생시켜야 함
    with pytest.raises(ValueError, match="Multiple and Not continuous system messages are not supported"):
        client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it


def test_mock_merge_system_messages_empty() -> None:
    """Tests that empty message list is handled properly."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    merged_messages = client._merge_system_messages([])  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it
    assert len(merged_messages) == 0


def test_mock_merge_system_messages_with_special_characters() -> None:
    """Tests system message merging with special characters and formatting."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        SystemMessage(content="Line 1\nWith newline"),
        SystemMessage(content="Line 2 with *formatting*"),
        SystemMessage(content="Line 3 with `code`"),
        UserMessage(content="Question", source="user"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it
    assert len(merged_messages) == 2

    system_message = merged_messages[0]
    assert isinstance(system_message, SystemMessage)
    assert system_message.content == "Line 1\nWith newline\nLine 2 with *formatting*\nLine 3 with `code`"


def test_mock_merge_system_messages_with_whitespace() -> None:
    """Tests system message merging with extra whitespace."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        SystemMessage(content="  Message with leading spaces  "),
        SystemMessage(content="\nMessage with leading newline\n"),
        UserMessage(content="Question", source="user"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it
    assert len(merged_messages) == 2

    system_message = merged_messages[0]
    assert isinstance(system_message, SystemMessage)
    # strip()은 내부에서 발생하지 않지만 최종 결과에서는 줄바꿈이 유지됨
    assert system_message.content == "  Message with leading spaces  \n\nMessage with leading newline"


def test_mock_merge_system_messages_message_order() -> None:
    """Tests that message order is preserved after merging."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        UserMessage(content="Question 1", source="user"),
        SystemMessage(content="Instruction 1"),
        SystemMessage(content="Instruction 2"),
        UserMessage(content="Question 2", source="user"),
        AssistantMessage(content="Answer", source="assistant"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it
    assert len(merged_messages) == 4

    # 첫 번째 메시지는 UserMessage여야 함
    assert isinstance(merged_messages[0], UserMessage)
    assert merged_messages[0].content == "Question 1"

    # 두 번째 메시지는 병합된 SystemMessage여야 함
    assert isinstance(merged_messages[1], SystemMessage)
    assert merged_messages[1].content == "Instruction 1\nInstruction 2"

    # 나머지 메시지는 순서대로 유지되어야 함
    assert isinstance(merged_messages[2], UserMessage)
    assert merged_messages[2].content == "Question 2"
    assert isinstance(merged_messages[3], AssistantMessage)
    assert merged_messages[3].content == "Answer"


def test_mock_merge_system_messages_multiple_groups() -> None:
    """Tests that multiple separate groups of system messages raise an error."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    # 연속되지 않은 시스템 메시지: 사용자 메시지로 분리된 두 그룹
    messages: List[LLMMessage] = [
        SystemMessage(content="Group 1 - message 1"),
        UserMessage(content="Interrupting user message", source="user"),
        SystemMessage(content="Group 2 - message 1"),
    ]

    with pytest.raises(ValueError, match="Multiple and Not continuous system messages are not supported"):
        client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it


def test_mock_merge_system_messages_no_duplicates() -> None:
    """Tests that identical system messages are still merged properly."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    messages: List[LLMMessage] = [
        SystemMessage(content="Same instruction"),
        SystemMessage(content="Same instruction"),  # 중복된 내용
        UserMessage(content="Question", source="user"),
    ]

    merged_messages = client._merge_system_messages(messages)  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it
    assert len(merged_messages) == 2

    # 첫 번째 메시지는 병합된 시스템 메시지여야 함
    assert isinstance(merged_messages[0], SystemMessage)
    # 중복된 내용도 그대로 병합됨
    assert merged_messages[0].content == "Same instruction\nSame instruction"


@pytest.mark.asyncio
async def test_anthropic_empty_assistant_content_string() -> None:
    """Test that an empty assistant content string is handled correctly."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    # Test empty assistant content string
    result = await client.create(
        messages=[
            UserMessage(content="Say something", source="user"),
            AssistantMessage(content="", source="assistant"),
        ]
    )

    # Verify we got a response
    assert isinstance(result.content, str)
    assert len(result.content) > 0


@pytest.mark.asyncio
async def test_anthropic_trailing_whitespace_at_last_assistant_content() -> None:
    """Test that an empty assistant content string is handled correctly."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    messages: list[LLMMessage] = [
        UserMessage(content="foo", source="user"),
        UserMessage(content="bar", source="user"),
        AssistantMessage(content="foobar ", source="assistant"),
    ]

    result = await client.create(messages=messages)
    assert isinstance(result.content, str)


def test_mock_rstrip_trailing_whitespace_at_last_assistant_content() -> None:
    messages: list[LLMMessage] = [
        UserMessage(content="foo", source="user"),
        UserMessage(content="bar", source="user"),
        AssistantMessage(content="foobar ", source="assistant"),
    ]

    # This will crash if _rstrip_railing_whitespace_at_last_assistant_content is not applied to "content"
    dummy_client = AnthropicChatCompletionClient(model="claude-3-5-haiku-20241022", api_key="dummy-key")
    result = dummy_client._rstrip_last_assistant_message(messages)  # pyright: ignore[reportPrivateUsage]

    assert isinstance(result[-1].content, str)
    assert result[-1].content == "foobar"


@pytest.mark.asyncio
async def test_anthropic_tool_choice_with_actual_api() -> None:
    """Test tool_choice parameter with actual Anthropic API endpoints."""
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

    # Test 1: tool_choice with specific tool
    messages: List[LLMMessage] = [
        SystemMessage(content="Use the tools as needed to help the user."),
        UserMessage(content="Process the text 'hello world' using the process_text tool.", source="user"),
    ]

    result = await client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice=pass_tool,  # Force use of specific tool
    )

    # Verify we got a tool call for the specified tool
    assert isinstance(result.content, list)
    assert len(result.content) >= 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "process_text"

    # Test 2: tool_choice="auto" with tools
    auto_messages: List[LLMMessage] = [
        SystemMessage(content="Use the tools as needed to help the user."),
        UserMessage(content="Add the numbers 5 and 3.", source="user"),
    ]

    auto_result = await client.create(
        messages=auto_messages,
        tools=[pass_tool, add_tool],
        tool_choice="auto",  # Let model choose
    )

    # Should get a tool call, likely for add_numbers
    assert isinstance(auto_result.content, list)
    assert len(auto_result.content) >= 1
    assert isinstance(auto_result.content[0], FunctionCall)
    # Model should choose add_numbers for addition task
    assert auto_result.content[0].name == "add_numbers"

    # Test 3: No tools provided - should not include tool_choice in API call
    no_tools_messages: List[LLMMessage] = [
        UserMessage(content="What is the capital of France?", source="user"),
    ]

    no_tools_result = await client.create(messages=no_tools_messages)

    # Should get a text response without tool calls
    assert isinstance(no_tools_result.content, str)
    assert "paris" in no_tools_result.content.lower()

    # Test 4: tool_choice="required" with tools
    required_messages: List[LLMMessage] = [
        SystemMessage(content="You must use one of the available tools to help the user."),
        UserMessage(content="Help me with something.", source="user"),
    ]

    required_result = await client.create(
        messages=required_messages,
        tools=[pass_tool, add_tool],
        tool_choice="required",  # Force tool usage
    )

    # Should get a tool call (model forced to use a tool)
    assert isinstance(required_result.content, list)
    assert len(required_result.content) >= 1
    assert isinstance(required_result.content[0], FunctionCall)


@pytest.mark.asyncio
async def test_anthropic_tool_choice_streaming_with_actual_api() -> None:
    """Test tool_choice parameter with streaming using actual Anthropic API endpoints."""
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

    # Test streaming with tool_choice
    messages: List[LLMMessage] = [
        SystemMessage(content="Use the tools as needed to help the user."),
        UserMessage(content="Process the text 'streaming test' using the process_text tool.", source="user"),
    ]

    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice=pass_tool,  # Force use of specific tool
    ):
        chunks.append(chunk)

    # Verify we got chunks and a final result
    assert len(chunks) > 0
    final_result = chunks[-1]
    assert isinstance(final_result, CreateResult)

    # Should get a tool call for the specified tool
    assert isinstance(final_result.content, list)
    assert len(final_result.content) >= 1
    assert isinstance(final_result.content[0], FunctionCall)
    assert final_result.content[0].name == "process_text"

    # Test streaming without tools - should not include tool_choice
    no_tools_messages: List[LLMMessage] = [
        UserMessage(content="Tell me a short fact about cats.", source="user"),
    ]

    no_tools_chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(messages=no_tools_messages):
        no_tools_chunks.append(chunk)

    # Should get text response
    assert len(no_tools_chunks) > 0
    final_no_tools_result = no_tools_chunks[-1]
    assert isinstance(final_no_tools_result, CreateResult)
    assert isinstance(final_no_tools_result.content, str)
    assert len(final_no_tools_result.content) > 0


@pytest.mark.asyncio
async def test_anthropic_tool_choice_none_value_with_actual_api() -> None:
    """Test tool_choice="none" with actual Anthropic API endpoints."""
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

    # Test tool_choice="none" - should not use tools even when available
    messages: List[LLMMessage] = [
        SystemMessage(content="Answer the user's question directly without using tools."),
        UserMessage(content="What is 2 + 2?", source="user"),
    ]

    result = await client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice="none",  # Disable tool usage
    )

    # Should get a text response, not tool calls
    assert isinstance(result.content, str)


def get_client_or_skip(provider: str) -> BaseAnthropicChatCompletionClient:
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not found in environment variables")

        return AnthropicChatCompletionClient(
            model="claude-3-haiku-20240307",
            api_key=api_key,
        )
    else:
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION")
        if not access_key or not secret_key or not region:
            pytest.skip("AWS credentials not found in environment variables")

        model = os.getenv("ANTHROPIC_BEDROCK_MODEL", "us.anthropic.claude-3-haiku-20240307-v1:0")
        return AnthropicBedrockChatCompletionClient(
            model=model,
            bedrock_info=BedrockInfo(
                aws_access_key=access_key,
                aws_secret_key=secret_key,
                aws_region=region,
                aws_session_token=os.getenv("AWS_SESSION_TOKEN", ""),
            ),
            model_info=ModelInfo(
                vision=False, function_calling=True, json_output=False, family="unknown", structured_output=True
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["anthropic", "bedrock"])
async def test_streaming_tool_usage_with_no_arguments(provider: str) -> None:
    """
    Test reading streaming tool usage response with no arguments.
    In that case `input` in initial `tool_use` chunk is `{}` and subsequent `partial_json` chunks are empty.
    """
    client = get_client_or_skip(provider)

    # Define tools
    ask_for_input_tool = FunctionTool(
        _ask_for_input, description="Ask user for more input", name="ask_for_input", strict=True
    )

    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(
        messages=[
            SystemMessage(content="When user intent is unclear, ask for more input"),
            UserMessage(content="Erm...", source="user"),
        ],
        tools=[ask_for_input_tool],
        tool_choice="required",
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    result: CreateResult = chunks[-1]
    assert len(result.content) == 1
    content = result.content[-1]
    assert isinstance(content, FunctionCall)
    assert content.name == "ask_for_input"
    assert json.loads(content.arguments) is not None


@pytest.mark.parametrize("provider", ["anthropic", "bedrock"])
@pytest.mark.asyncio
async def test_streaming_tool_usage_with_arguments(provider: str) -> None:
    """
    Test reading streaming tool usage response with arguments.
    In that case `input` in initial `tool_use` chunk is `{}` but subsequent `partial_json` chunks make up the actual
    complete input value.
    """
    client = get_client_or_skip(provider)

    # Define tools
    add_numbers = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(
        messages=[
            SystemMessage(content="Use the tools to evaluate calculations"),
            UserMessage(content="2 + 2", source="user"),
        ],
        tools=[add_numbers],
        tool_choice="required",
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    result: CreateResult = chunks[-1]
    assert len(result.content) == 1
    content = result.content[-1]
    assert isinstance(content, FunctionCall)
    assert content.name == "add_numbers"
    assert json.loads(content.arguments) is not None


def test_mock_thinking_config_validation() -> None:
    """Test thinking configuration handling logic."""
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",  # Known model for basic validation
        api_key="fake-key"
    )
    
    # Test valid enabled thinking config
    valid_config = {"thinking": {"type": "enabled", "budget_tokens": 2000}}
    result = client._get_thinking_config(valid_config)  # pyright: ignore[reportPrivateUsage]
    assert result == valid_config
    
    # Test thinking config with any budget_tokens (API will validate)
    any_budget_config = {"thinking": {"type": "enabled", "budget_tokens": 500}}
    result = client._get_thinking_config(any_budget_config)  # pyright: ignore[reportPrivateUsage]
    assert result == any_budget_config
    
    # Test valid disabled thinking config
    disabled_config = {"thinking": {"type": "disabled"}}
    result = client._get_thinking_config(disabled_config)  # pyright: ignore[reportPrivateUsage]
    assert result == disabled_config
    
    # Test no thinking config
    result = client._get_thinking_config({})
    assert result == {}
    
    # Test thinking config from base create_args
    from autogen_core.models import ModelInfo
    client_with_thinking = AnthropicChatCompletionClient(
        model="claude-sonnet-4-20250514",
        api_key="fake-key",
        model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="anthropic"),
        thinking={"type": "enabled", "budget_tokens": 3000}
    )
    result = client_with_thinking._get_thinking_config({})  # pyright: ignore[reportPrivateUsage]
    assert result == {"thinking": {"type": "enabled", "budget_tokens": 3000}}
    
    # Test extra_create_args takes priority over base create_args
    override_config = {"thinking": {"type": "enabled", "budget_tokens": 4000}}
    result = client_with_thinking._get_thinking_config(override_config)  # pyright: ignore[reportPrivateUsage]
    assert result == override_config


@pytest.mark.asyncio
async def test_anthropic_thinking_mode_basic() -> None:
    """Test basic thinking mode functionality."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    
    client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-20250514",  # Use a model that supports thinking
        api_key=api_key,
        temperature=0.7  # Should be overridden to 1.0
    )
    
    messages = [UserMessage(content="Calculate 17 * 23 step by step.", source="test")]
    
    # Test WITHOUT thinking mode
    result_no_thinking = await client.create(messages)
    assert isinstance(result_no_thinking.content, str)
    assert result_no_thinking.thought is None
    
    # Test WITH thinking mode
    thinking_config = {
        "thinking": {
            "type": "enabled",
            "budget_tokens": 2000
        }
    }
    
    result_with_thinking = await client.create(messages, extra_create_args=thinking_config)
    assert isinstance(result_with_thinking.content, str)
    # Should have thinking content
    assert result_with_thinking.thought is not None
    assert len(result_with_thinking.thought) > 10
    # Main content should contain the final answer
    assert "391" in result_with_thinking.content or "17" in result_with_thinking.content


@pytest.mark.asyncio
async def test_anthropic_thinking_mode_streaming() -> None:
    """Test thinking mode with streaming."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    
    client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-20250514",  # Use a model that supports thinking
        api_key=api_key
    )
    
    messages = [UserMessage(content="What is 15 + 27? Think through it step by step.", source="test")]
    
    thinking_config = {
        "thinking": {
            "type": "enabled",
            "budget_tokens": 1500
        }
    }
    
    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(messages, extra_create_args=thinking_config):
        chunks.append(chunk)
    
    # Should have received chunks
    assert len(chunks) > 1
    
    # Final result should have thinking content
    final_result = chunks[-1]
    assert isinstance(final_result, CreateResult)
    assert isinstance(final_result.content, str)
    assert final_result.thought is not None
    assert len(final_result.thought) > 10
    # Should contain the answer
    assert "42" in final_result.content


@pytest.mark.asyncio
async def test_anthropic_thinking_mode_with_tools() -> None:
    """Test thinking mode combined with tool calling."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    
    client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-20250514",  # Use a model that supports thinking
        api_key=api_key
    )
    
    # Define tool
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")
    
    messages = [UserMessage(content="I need to add 25 and 17. Use the add tool after thinking about it.", source="test")]
    
    thinking_config = {
        "thinking": {
            "type": "enabled",
            "budget_tokens": 2000
        }
    }
    
    result = await client.create(messages, tools=[add_tool], extra_create_args=thinking_config)
    
    # Should get tool calls
    assert isinstance(result.content, list)
    assert len(result.content) >= 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "add_numbers"
    
    # Should have thinking content even with tool calls
    assert result.thought is not None
    assert len(result.thought) > 10


