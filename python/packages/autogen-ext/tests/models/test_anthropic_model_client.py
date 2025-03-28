import asyncio
import logging
import os
from typing import List, Sequence

import pytest
from unittest.mock import MagicMock, patch

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


@pytest.mark.parametrize(
    "messages,expected_count,expected_content",
    [
        # 테스트 케이스 1: 연속된 시스템 메시지 - 병합됨
        (
            [
                SystemMessage(content="System instruction 1"),
                SystemMessage(content="System instruction 2"),
                UserMessage(content="User question", source="user"),
            ],
            2,  # 병합 후 예상 메시지 개수: 시스템 1개 + 사용자 1개
            "System instruction 1\nSystem instruction 2",  # 병합된 내용
        ),
        # 테스트 케이스 2: 단일 시스템 메시지 - 변경 없음
        (
            [
                SystemMessage(content="Single system instruction"),
                UserMessage(content="User question", source="user"),
            ],
            2,  # 메시지 개수 변화 없음
            "Single system instruction",  # 원본 내용 유지
        ),
        # 테스트 케이스 3: 시스템 메시지 없음
        (
            [
                UserMessage(content="User question without system", source="user"),
            ],
            1,  # 메시지 개수 변화 없음
            None,  # 시스템 메시지 없음
        ),
        # 테스트 케이스 4: 여러 그룹의 연속된 시스템 메시지
        (
            [
                SystemMessage(content="First group 1"),
                SystemMessage(content="First group 2"),
                UserMessage(content="Middle user message", source="user"),
                SystemMessage(content="Second group 1"),
                SystemMessage(content="Second group 2"),
            ],
            3,  # 병합 후: 시스템(병합) + 사용자 + 시스템(병합)
            None,  # 두 그룹 모두 병합되지만 연속적이지 않아 ValueError 발생 예상
        ),
    ],
)
def test_merge_system_messages(messages, expected_count, expected_content):
    """Test the _merge_system_messages method directly"""
    
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key="fake-api-key"
    )
    
    # 연속되지 않은 시스템 메시지 케이스는 예외가 발생해야 함
    if expected_content is None and len(messages) > 1:
        with pytest.raises(ValueError, match="Multiple and Not continuous system messages are not supported"):
            merged_messages = client._merge_system_messages(messages)
        return
    
    # 그 외 케이스는 정상 병합
    merged_messages = client._merge_system_messages(messages)
    
    # 메시지 개수 확인
    assert len(merged_messages) == expected_count
    
    # 시스템 메시지 내용 확인 (있는 경우)
    if expected_content is not None:
        system_messages = [msg for msg in merged_messages if isinstance(msg, SystemMessage)]
        if system_messages:
            assert system_messages[0].content == expected_content
        else:
            assert expected_content is None

@pytest.mark.asyncio
async def test_anthropic_multiple_system_messages_api_call():
    """Test multiple system messages are correctly merged in API calls"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key
    )
    
    # 시스템 메시지 병합 호출 모킹
    original_merge = client._merge_system_messages
    merge_called = False
    merged_content = None
    
    def mock_merge(messages):
        nonlocal merge_called, merged_content
        merge_called = True
        result = original_merge(messages)
        
        # 병합된 시스템 메시지의 내용 저장
        for msg in result:
            if isinstance(msg, SystemMessage):
                merged_content = msg.content
                break
        
        return result
    
    # 패치 적용
    with patch.object(client, '_merge_system_messages', side_effect=mock_merge):
        messages = [
            SystemMessage(content="First instruction: be concise"),
            SystemMessage(content="Second instruction: use simple words"),
            UserMessage(content="Explain what a computer is", source="user"),
        ]
        
        # API 호출
        result = await client.create(messages=messages)
        
        # 검증
        assert merge_called, "System message merge function was not called"
        assert merged_content == "First instruction: be concise\nSecond instruction: use simple words"
        
        # 응답이 지시사항을 따랐는지 확인 (간결하고 단순한 언어)
        assert isinstance(result.content, str)
        assert len(result.content) < 500  # 간결함 확인 (임의 기준)

@pytest.mark.asyncio
async def test_anthropic_merge_error_propagation():
    """Test that merge errors properly propagate through the create method"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    
    client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=api_key
    )
    
    # 연속되지 않은 시스템 메시지
    messages = [
        SystemMessage(content="System instruction 1"),
        UserMessage(content="User interruption", source="user"),
        SystemMessage(content="System instruction 2"),
    ]
    
    # create 메서드에서도 에러가 발생하는지 확인
    with pytest.raises(ValueError, match="Multiple and Not continuous system messages are not supported"):
        await client.create(messages=messages)

@pytest.mark.asyncio
async def test_anthropic_merge_with_multimodal():
    """Test system message merge with multimodal content"""
    
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
        model="claude-3-sonnet-20240229",  # 비전 지원 모델
        api_key=api_key
    )
    
    # 간단한 이미지 생성
    width, height = 100, 100
    color = (255, 0, 0)  # Red
    pil_image = PILImage.new("RGB", (width, height), color)
    img = Image(pil_image)
    
    # 멀티모달 시스템 메시지와 일반 시스템 메시지 조합
    with pytest.raises(ValueError):  # 멀티모달 시스템 메시지는 지원되지 않을 것임
        await client.create(
            messages=[
                SystemMessage(content="Text system message"),
                SystemMessage(content=[img]),  # 멀티모달 시스템 메시지
                UserMessage(content="What do you see?", source="user"),
            ]
        )