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
async def test_anthropic_serialization_api_key() -> None:
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


def test_merge_continuous_system_messages() -> None:
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


def test_merge_single_system_message() -> None:
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


def test_merge_no_system_messages() -> None:
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


def test_merge_non_continuous_system_messages() -> None:
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


def test_merge_system_messages_empty() -> None:
    """Tests that empty message list is handled properly."""
    client = AnthropicChatCompletionClient(model="claude-3-haiku-20240307", api_key="fake-api-key")

    merged_messages = client._merge_system_messages([])  # pyright: ignore[reportPrivateUsage]
    # The method is protected, but we need to test it
    assert len(merged_messages) == 0


def test_merge_system_messages_with_special_characters() -> None:
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


def test_merge_system_messages_with_whitespace() -> None:
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


def test_merge_system_messages_message_order() -> None:
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


def test_merge_system_messages_multiple_groups() -> None:
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


def test_merge_system_messages_no_duplicates() -> None:
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
async def test_empty_assistant_content_string_with_anthropic() -> None:
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
