import asyncio
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, List, Type, Union
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import CancellationToken, FunctionCall, Image
from autogen_core.models import CreateResult, ModelFamily, UserMessage
from autogen_core.tools import FunctionTool
from autogen_ext.models.azure import AzureAIChatCompletionClient
from autogen_ext.models.azure.config import GITHUB_MODELS_ENDPOINT
from azure.ai.inference.aio import (
    ChatCompletionsClient,
)
from azure.ai.inference.models import (
    ChatChoice,
    ChatCompletions,
    ChatCompletionsToolCall,
    ChatResponseMessage,
    CompletionsFinishReason,
    CompletionsUsage,
    StreamingChatChoiceUpdate,
    StreamingChatCompletionsUpdate,
    StreamingChatResponseMessageUpdate,
)
from azure.ai.inference.models import (
    FunctionCall as AzureFunctionCall,
)
from azure.core.credentials import AzureKeyCredential


async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[StreamingChatCompletionsUpdate, None]:
    mock_chunks_content = ["Hello", " Another Hello", " Yet Another Hello"]

    mock_chunks = [
        StreamingChatChoiceUpdate(
            index=0,
            finish_reason="stop",
            delta=StreamingChatResponseMessageUpdate(role="assistant", content=chunk_content),
        )
        for chunk_content in mock_chunks_content
    ]

    for mock_chunk in mock_chunks:
        await asyncio.sleep(0.1)
        yield StreamingChatCompletionsUpdate(
            id="id",
            choices=[mock_chunk],
            created=datetime.now(),
            model="model",
            usage=CompletionsUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )


async def _mock_create(
    *args: Any, **kwargs: Any
) -> ChatCompletions | AsyncGenerator[StreamingChatCompletionsUpdate, None]:
    stream = kwargs.get("stream", False)

    if not stream:
        await asyncio.sleep(0.1)
        return ChatCompletions(
            id="id",
            created=datetime.now(),
            model="model",
            choices=[
                ChatChoice(
                    index=0, finish_reason="stop", message=ChatResponseMessage(content="Hello", role="assistant")
                )
            ],
            usage=CompletionsUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )
    else:
        return _mock_create_stream(*args, **kwargs)


@pytest.fixture
def azure_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    endpoint = os.getenv("AZURE_AI_INFERENCE_ENDPOINT")
    api_key = os.getenv("AZURE_AI_INFERENCE_API_KEY")

    if endpoint and api_key:
        return AzureAIChatCompletionClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
            model_info={
                "json_output": False,
                "function_calling": False,
                "vision": False,
                "family": "unknown",
                "structured_output": False,
            },
            model="model",
        )

    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create)
    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": False,
            "vision": False,
            "family": "unknown",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_validation() -> None:
    with pytest.raises(ValueError, match="endpoint is required"):
        AzureAIChatCompletionClient(
            model="model",
            credential=AzureKeyCredential("api_key"),
            model_info={
                "json_output": False,
                "function_calling": False,
                "vision": False,
                "family": "unknown",
                "structured_output": False,
            },
        )

    with pytest.raises(ValueError, match="credential is required"):
        AzureAIChatCompletionClient(
            model="model",
            endpoint="endpoint",
            model_info={
                "json_output": False,
                "function_calling": False,
                "vision": False,
                "family": "unknown",
                "structured_output": False,
            },
        )

    with pytest.raises(ValueError, match="model is required"):
        AzureAIChatCompletionClient(
            endpoint=GITHUB_MODELS_ENDPOINT,
            credential=AzureKeyCredential("api_key"),
            model_info={
                "json_output": False,
                "function_calling": False,
                "vision": False,
                "family": "unknown",
                "structured_output": False,
            },
        )

    with pytest.raises(ValueError, match="model_info is required"):
        AzureAIChatCompletionClient(
            model="model",
            endpoint="endpoint",
            credential=AzureKeyCredential("api_key"),
        )

    with pytest.raises(ValueError, match="Missing required field 'family'"):
        AzureAIChatCompletionClient(
            model="model",
            endpoint="endpoint",
            credential=AzureKeyCredential("api_key"),
            model_info={
                "json_output": False,
                "function_calling": False,
                "vision": False,
                # Missing family.
            },  # type: ignore
        )


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client(azure_client: AzureAIChatCompletionClient) -> None:
    assert azure_client


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create(
    azure_client: AzureAIChatCompletionClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        result = await azure_client.create(messages=[UserMessage(content="Hello", source="user")])
        assert result.content == "Hello"
        assert "LLMCall" in caplog.text and "Hello" in caplog.text


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create_stream(
    azure_client: AzureAIChatCompletionClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        chunks: List[str | CreateResult] = []
        async for chunk in azure_client.create_stream(messages=[UserMessage(content="Hello", source="user")]):
            chunks.append(chunk)

        assert "LLMStreamStart" in caplog.text
        assert "LLMStreamEnd" in caplog.text

        final_result: str | CreateResult = chunks[-1]
        assert isinstance(final_result, CreateResult)
        assert isinstance(final_result.content, str)
        assert final_result.content in caplog.text

    assert chunks[0] == "Hello"
    assert chunks[1] == " Another Hello"
    assert chunks[2] == " Yet Another Hello"


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create_cancel(azure_client: AzureAIChatCompletionClient) -> None:
    cancellation_token = CancellationToken()
    task = asyncio.create_task(
        azure_client.create(
            messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token
        )
    )
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create_stream_cancel(azure_client: AzureAIChatCompletionClient) -> None:
    cancellation_token = CancellationToken()
    stream = azure_client.create_stream(
        messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token
    )
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        async for _ in stream:
            pass


@pytest.fixture
def function_calling_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    """
    Returns a client that supports function calling.
    """

    async def _mock_function_call_create(*args: Any, **kwargs: Any) -> ChatCompletions:
        await asyncio.sleep(0.01)
        return ChatCompletions(
            id="id",
            created=datetime.now(),
            model="model",
            choices=[
                ChatChoice(
                    index=0,
                    finish_reason=CompletionsFinishReason.TOOL_CALLS,
                    message=ChatResponseMessage(
                        role="assistant",
                        content="",
                        tool_calls=[
                            ChatCompletionsToolCall(
                                id="tool_call_id",
                                function=AzureFunctionCall(name="some_function", arguments='{"foo": "bar"}'),
                            )
                        ],
                    ),
                )
            ],
            usage=CompletionsUsage(prompt_tokens=5, completion_tokens=2, total_tokens=7),
        )

    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_function_call_create)
    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": True,
            "vision": False,
            "family": "function_calling_model",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_function_calling_not_supported(azure_client: AzureAIChatCompletionClient) -> None:
    """
    Ensures error is raised if we pass tools but the model_info doesn't support function calling.
    """
    with pytest.raises(ValueError) as exc:
        await azure_client.create(
            messages=[UserMessage(content="Hello", source="user")],
            tools=[{"name": "dummy_tool"}],
        )
    assert "Model does not support function calling" in str(exc.value)


@pytest.mark.asyncio
async def test_function_calling_success(function_calling_client: AzureAIChatCompletionClient) -> None:
    """
    Ensures function calling works and returns FunctionCall content.
    """
    result = await function_calling_client.create(
        messages=[UserMessage(content="Please call a function", source="user")],
        tools=[{"name": "test_tool"}],
    )
    assert result.finish_reason == "function_calls"
    assert isinstance(result.content, list)
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "some_function"
    assert result.content[0].arguments == '{"foo": "bar"}'


@pytest.mark.asyncio
async def test_multimodal_unsupported_raises_error(azure_client: AzureAIChatCompletionClient) -> None:
    """
    If model does not support vision, providing an image should raise ValueError.
    """
    with pytest.raises(ValueError) as exc:
        await azure_client.create(
            messages=[
                UserMessage(
                    content=[  # type: ignore
                        Image.from_base64(
                            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAen6L8YAAAAASUVORK5CYII="
                        )
                    ],
                    source="user",
                )
            ]
        )
    assert "does not support vision and image was provided" in str(exc.value)


@pytest.mark.asyncio
async def test_multimodal_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    If model supports vision, providing an image should not raise.
    """

    async def _mock_create_noop(*args: Any, **kwargs: Any) -> ChatCompletions:
        await asyncio.sleep(0.01)
        return ChatCompletions(
            id="id",
            created=datetime.now(),
            model="model",
            choices=[
                ChatChoice(
                    index=0,
                    finish_reason="stop",
                    message=ChatResponseMessage(content="Handled image", role="assistant"),
                )
            ],
            usage=CompletionsUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create_noop)

    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": False,
            "vision": True,
            "family": "vision_model",
            "structured_output": False,
        },
        model="model",
    )

    result = await client.create(
        messages=[
            UserMessage(
                content=[
                    Image.from_base64(
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAen6L8YAAAAASUVORK5CYII="
                    )
                ],
                source="user",
            )
        ]
    )
    assert result.content == "Handled image"


@pytest.mark.asyncio
async def test_r1_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensures that the content is parsed correctly when it contains an R1-style think field.
    """

    async def _mock_create_r1_content_stream(
        *args: Any, **kwargs: Any
    ) -> AsyncGenerator[StreamingChatCompletionsUpdate, None]:
        mock_chunks_content = ["<think>Thought</think> Hello", " Another Hello", " Yet Another Hello"]

        mock_chunks = [
            StreamingChatChoiceUpdate(
                index=0,
                finish_reason="stop",
                delta=StreamingChatResponseMessageUpdate(role="assistant", content=chunk_content),
            )
            for chunk_content in mock_chunks_content
        ]

        for mock_chunk in mock_chunks:
            await asyncio.sleep(0.1)
            yield StreamingChatCompletionsUpdate(
                id="id",
                choices=[mock_chunk],
                created=datetime.now(),
                model="model",
                usage=CompletionsUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    async def _mock_create_r1_content(
        *args: Any, **kwargs: Any
    ) -> ChatCompletions | AsyncGenerator[StreamingChatCompletionsUpdate, None]:
        stream = kwargs.get("stream", False)

        if not stream:
            await asyncio.sleep(0.1)
            return ChatCompletions(
                id="id",
                created=datetime.now(),
                model="model",
                choices=[
                    ChatChoice(
                        index=0,
                        finish_reason="stop",
                        message=ChatResponseMessage(content="<think>Thought</think> Hello", role="assistant"),
                    )
                ],
                usage=CompletionsUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )
        else:
            return _mock_create_r1_content_stream(*args, **kwargs)

    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create_r1_content)

    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": False,
            "vision": True,
            "family": ModelFamily.R1,
            "structured_output": False,
        },
        model="model",
    )

    result = await client.create(messages=[UserMessage(content="Hello", source="user")])
    assert result.content == "Hello"
    assert result.thought == "Thought"

    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(messages=[UserMessage(content="Hello", source="user")]):
        chunks.append(chunk)
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
    assert chunks[-1].thought == "Thought"


@pytest.fixture
def thought_with_tool_call_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    """
    Returns a client that simulates a response with both tool calls and thought content.
    """

    async def _mock_thought_with_tool_call(*args: Any, **kwargs: Any) -> ChatCompletions:
        await asyncio.sleep(0.01)
        return ChatCompletions(
            id="id",
            created=datetime.now(),
            model="model",
            choices=[
                ChatChoice(
                    index=0,
                    finish_reason=CompletionsFinishReason.TOOL_CALLS,
                    message=ChatResponseMessage(
                        role="assistant",
                        content="Let me think about what function to call.",
                        tool_calls=[
                            ChatCompletionsToolCall(
                                id="tool_call_id",
                                function=AzureFunctionCall(name="some_function", arguments='{"foo": "bar"}'),
                            )
                        ],
                    ),
                )
            ],
            usage=CompletionsUsage(prompt_tokens=8, completion_tokens=5, total_tokens=13),
        )

    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_thought_with_tool_call)
    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": True,
            "vision": False,
            "family": "function_calling_model",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_thought_field_with_tool_calls(thought_with_tool_call_client: AzureAIChatCompletionClient) -> None:
    """
    Tests that when a model returns both tool calls and text content, the text content is
    preserved in the thought field of the CreateResult.
    """
    result = await thought_with_tool_call_client.create(
        messages=[UserMessage(content="Please call a function", source="user")],
        tools=[{"name": "test_tool"}],
    )

    assert result.finish_reason == "function_calls"
    assert isinstance(result.content, list)
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "some_function"
    assert result.content[0].arguments == '{"foo": "bar"}'

    assert result.thought == "Let me think about what function to call."


@pytest.fixture
def thought_with_tool_call_stream_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    """
    Returns a client that simulates a streaming response with both tool calls and thought content.
    """
    first_choice = MagicMock()
    first_choice.delta = MagicMock()
    first_choice.delta.content = "Let me think about what function to call."
    first_choice.finish_reason = None

    mock_tool_call = MagicMock()
    mock_tool_call.id = "tool_call_id"
    mock_tool_call.function = MagicMock()
    mock_tool_call.function.name = "some_function"
    mock_tool_call.function.arguments = '{"foo": "bar"}'

    tool_call_choice = MagicMock()
    tool_call_choice.delta = MagicMock()
    tool_call_choice.delta.content = None
    tool_call_choice.delta.tool_calls = [mock_tool_call]
    tool_call_choice.finish_reason = "function_calls"

    async def _mock_thought_with_tool_call_stream(
        *args: Any, **kwargs: Any
    ) -> AsyncGenerator[StreamingChatCompletionsUpdate, None]:
        yield StreamingChatCompletionsUpdate(
            id="id",
            choices=[first_choice],
            created=datetime.now(),
            model="model",
        )

        await asyncio.sleep(0.01)

        yield StreamingChatCompletionsUpdate(
            id="id",
            choices=[tool_call_choice],
            created=datetime.now(),
            model="model",
            usage=CompletionsUsage(prompt_tokens=8, completion_tokens=5, total_tokens=13),
        )

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    async def mock_complete(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("stream", False):
            return _mock_thought_with_tool_call_stream(*args, **kwargs)
        return None

    mock_client.complete = mock_complete

    def mock_new(cls: Type[ChatCompletionsClient], *args: Any, **kwargs: Any) -> MagicMock:
        return mock_client

    monkeypatch.setattr(ChatCompletionsClient, "__new__", mock_new)

    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": True,
            "vision": False,
            "family": "function_calling_model",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_thought_field_with_tool_calls_streaming(
    thought_with_tool_call_stream_client: AzureAIChatCompletionClient,
) -> None:
    """
    Tests that when a model returns both tool calls and text content in a streaming response,
    the text content is preserved in the thought field of the final CreateResult.
    """
    chunks: List[Union[str, CreateResult]] = []
    async for chunk in thought_with_tool_call_stream_client.create_stream(
        messages=[UserMessage(content="Please call a function", source="user")],
        tools=[{"name": "test_tool"}],
    ):
        chunks.append(chunk)

    final_result = chunks[-1]
    assert isinstance(final_result, CreateResult)

    assert final_result.finish_reason == "function_calls"
    assert isinstance(final_result.content, list)
    assert isinstance(final_result.content[0], FunctionCall)
    assert final_result.content[0].name == "some_function"
    assert final_result.content[0].arguments == '{"foo": "bar"}'

    assert final_result.thought == "Let me think about what function to call."


def _pass_function(input: str) -> str:
    """Simple passthrough function."""
    return f"Processed: {input}"


def _add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@pytest.fixture
def tool_choice_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    """
    Returns a client that supports function calling for tool choice tests.
    """

    async def _mock_tool_choice_stream(
        *args: Any, **kwargs: Any
    ) -> AsyncGenerator[StreamingChatCompletionsUpdate, None]:
        mock_chunks_content = ["Hello", " Another Hello", " Yet Another Hello"]

        mock_chunks = [
            StreamingChatChoiceUpdate(
                index=0,
                finish_reason="stop",
                delta=StreamingChatResponseMessageUpdate(role="assistant", content=chunk_content),
            )
            for chunk_content in mock_chunks_content
        ]

        for mock_chunk in mock_chunks:
            await asyncio.sleep(0.01)
            yield StreamingChatCompletionsUpdate(
                id="id",
                choices=[mock_chunk],
                created=datetime.now(),
                model="model",
                usage=CompletionsUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    async def mock_complete(*args: Any, **kwargs: Any) -> Any:
        stream = kwargs.get("stream", False)

        if not stream:
            await asyncio.sleep(0.01)
            return ChatCompletions(
                id="id",
                created=datetime.now(),
                model="model",
                choices=[
                    ChatChoice(
                        index=0,
                        finish_reason=CompletionsFinishReason.TOOL_CALLS,
                        message=ChatResponseMessage(
                            role="assistant",
                            content="",
                            tool_calls=[
                                ChatCompletionsToolCall(
                                    id="call_123",
                                    function=AzureFunctionCall(name="process_text", arguments='{"input": "hello"}'),
                                )
                            ],
                        ),
                    )
                ],
                usage=CompletionsUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        else:
            return _mock_tool_choice_stream(*args, **kwargs)

    mock_client.complete = mock_complete

    def mock_new(cls: Type[ChatCompletionsClient], *args: Any, **kwargs: Any) -> MagicMock:
        return mock_client

    monkeypatch.setattr(ChatCompletionsClient, "__new__", mock_new)

    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": True,
            "vision": False,
            "family": "test",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_azure_ai_tool_choice_specific_tool(tool_choice_client: AzureAIChatCompletionClient) -> None:
    """Test tool_choice parameter with a specific tool using mocks."""
    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages = [
        UserMessage(content="Process the text 'hello'.", source="user"),
    ]

    result = await tool_choice_client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice=pass_tool,  # Force use of specific tool
    )

    # Verify the result
    assert result.finish_reason == "function_calls"
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "process_text"
    assert result.content[0].arguments == '{"input": "hello"}'


@pytest.mark.asyncio
async def test_azure_ai_tool_choice_auto(tool_choice_client: AzureAIChatCompletionClient) -> None:
    """Test tool_choice parameter with 'auto' setting using mocks."""
    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages = [
        UserMessage(content="Add 1 and 2.", source="user"),
    ]

    result = await tool_choice_client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice="auto",  # Let the model choose
    )

    # Verify the result
    assert result.finish_reason == "function_calls"
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "process_text"  # Our mock always returns process_text
    assert result.content[0].arguments == '{"input": "hello"}'


@pytest.fixture
def tool_choice_none_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    """
    Returns a client that simulates no tool calls for tool_choice='none' tests.
    """

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    async def mock_complete(*args: Any, **kwargs: Any) -> ChatCompletions:
        await asyncio.sleep(0.01)
        return ChatCompletions(
            id="id",
            created=datetime.now(),
            model="model",
            choices=[
                ChatChoice(
                    index=0,
                    finish_reason="stop",
                    message=ChatResponseMessage(role="assistant", content="I can help you with that."),
                )
            ],
            usage=CompletionsUsage(prompt_tokens=8, completion_tokens=6, total_tokens=14),
        )

    mock_client.complete = mock_complete

    def mock_new(cls: Type[ChatCompletionsClient], *args: Any, **kwargs: Any) -> MagicMock:
        return mock_client

    monkeypatch.setattr(ChatCompletionsClient, "__new__", mock_new)

    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": True,
            "vision": False,
            "family": "test",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_azure_ai_tool_choice_none(tool_choice_none_client: AzureAIChatCompletionClient) -> None:
    """Test tool_choice parameter with 'none' setting using mocks."""
    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages = [
        UserMessage(content="Just say hello.", source="user"),
    ]

    result = await tool_choice_none_client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice="none",  # Prevent tool usage
    )

    # Verify the result
    assert result.finish_reason == "stop"
    assert isinstance(result.content, str)
    assert result.content == "I can help you with that."


@pytest.mark.asyncio
async def test_azure_ai_tool_choice_required(tool_choice_client: AzureAIChatCompletionClient) -> None:
    """Test tool_choice parameter with 'required' setting using mocks."""
    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages = [
        UserMessage(content="Process some text.", source="user"),
    ]

    result = await tool_choice_client.create(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice="required",  # Force tool usage
    )

    # Verify the result
    assert result.finish_reason == "function_calls"
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "process_text"
    assert result.content[0].arguments == '{"input": "hello"}'


@pytest.fixture
def tool_choice_stream_client(monkeypatch: pytest.MonkeyPatch) -> AzureAIChatCompletionClient:
    """
    Returns a client that supports function calling for streaming tool choice tests.
    """

    # Mock tool call for streaming
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function = MagicMock()
    mock_tool_call.function.name = "process_text"
    mock_tool_call.function.arguments = '{"input": "hello"}'

    # First choice with content
    first_choice = MagicMock()
    first_choice.delta = MagicMock()
    first_choice.delta.content = "Let me process this for you."
    first_choice.finish_reason = None

    # Tool call choice
    tool_call_choice = MagicMock()
    tool_call_choice.delta = MagicMock()
    tool_call_choice.delta.content = None
    tool_call_choice.delta.tool_calls = [mock_tool_call]
    tool_call_choice.finish_reason = "function_calls"

    async def _mock_tool_choice_stream(
        *args: Any, **kwargs: Any
    ) -> AsyncGenerator[StreamingChatCompletionsUpdate, None]:
        yield StreamingChatCompletionsUpdate(
            id="id",
            choices=[first_choice],
            created=datetime.now(),
            model="model",
        )

        await asyncio.sleep(0.01)

        yield StreamingChatCompletionsUpdate(
            id="id",
            choices=[tool_call_choice],
            created=datetime.now(),
            model="model",
            usage=CompletionsUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    async def mock_complete(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("stream", False):
            return _mock_tool_choice_stream(*args, **kwargs)
        return None

    mock_client.complete = mock_complete

    def mock_new(cls: Type[ChatCompletionsClient], *args: Any, **kwargs: Any) -> MagicMock:
        return mock_client

    monkeypatch.setattr(ChatCompletionsClient, "__new__", mock_new)

    return AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_info={
            "json_output": False,
            "function_calling": True,
            "vision": False,
            "family": "test",
            "structured_output": False,
        },
        model="model",
    )


@pytest.mark.asyncio
async def test_azure_ai_tool_choice_specific_tool_streaming(
    tool_choice_stream_client: AzureAIChatCompletionClient,
) -> None:
    """Test tool_choice parameter with streaming and a specific tool using mocks."""
    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="process_text")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="add_numbers")

    messages = [
        UserMessage(content="Process the text 'hello'.", source="user"),
    ]

    chunks: List[Union[str, CreateResult]] = []
    async for chunk in tool_choice_stream_client.create_stream(
        messages=messages,
        tools=[pass_tool, add_tool],
        tool_choice=pass_tool,  # Force use of specific tool
    ):
        chunks.append(chunk)

    # Verify that we got some result
    final_result = chunks[-1]
    assert isinstance(final_result, CreateResult)
    assert final_result.finish_reason == "function_calls"
    assert isinstance(final_result.content, list)
    assert len(final_result.content) == 1
    assert isinstance(final_result.content[0], FunctionCall)
    assert final_result.content[0].name == "process_text"
    assert final_result.content[0].arguments == '{"input": "hello"}'
    assert final_result.thought == "Let me process this for you."
