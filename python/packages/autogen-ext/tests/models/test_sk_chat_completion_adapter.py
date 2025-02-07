import os
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from autogen_core import CancellationToken
from autogen_core.models import CreateResult, LLMMessage, ModelFamily, ModelInfo, SystemMessage, UserMessage
from autogen_core.tools import BaseTool
from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice, ChoiceDelta
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent
from semantic_kernel.contents.streaming_text_content import StreamingTextContent
from semantic_kernel.contents.text_content import TextContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.utils.finish_reason import FinishReason
from semantic_kernel.kernel import Kernel
from semantic_kernel.memory.null_memory import NullMemory


class CalculatorArgs(BaseModel):
    a: float
    b: float


class CalculatorResult(BaseModel):
    result: float


class CalculatorTool(BaseTool[CalculatorArgs, CalculatorResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=CalculatorArgs,
            return_type=CalculatorResult,
            name="calculator",
            description="Add two numbers together",
        )

    async def run(self, args: CalculatorArgs, cancellation_token: CancellationToken) -> CalculatorResult:
        return CalculatorResult(result=args.a + args.b)


@pytest.fixture
def sk_client() -> AzureChatCompletion:
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not all([deployment_name, endpoint, api_key]):
        mock_client = AsyncMock(spec=AzureChatCompletion)

        async def mock_get_chat_message_contents(
            chat_history: ChatHistory,
            settings: PromptExecutionSettings,
            **kwargs: Any,
        ) -> list[ChatMessageContent]:
            if "What is 2 + 2?" in str(chat_history):
                # Mock response for calculator tool test
                return [
                    ChatMessageContent(
                        ai_model_id="gpt-4o-mini",
                        role=AuthorRole.ASSISTANT,
                        metadata={"usage": {"prompt_tokens": 53, "completion_tokens": 13}},
                        items=[
                            FunctionCallContent(
                                id="call_UwVVI0iGEmcPwmKUigJcuuuF",
                                function_name="calculator",
                                plugin_name="autogen_tools",
                                arguments="{}",
                            )
                        ],
                        finish_reason=FinishReason.TOOL_CALLS,
                    )
                ]
            else:
                # Mock response for hello test
                return [
                    ChatMessageContent(
                        ai_model_id="gpt-4o-mini",
                        role=AuthorRole.ASSISTANT,
                        metadata={"usage": {"prompt_tokens": 20, "completion_tokens": 9}},
                        items=[TextContent(text="Hello! How can I assist you today?")],
                        finish_reason=FinishReason.STOP,
                    )
                ]

        async def mock_get_streaming_chat_message_contents(
            chat_history: ChatHistory,
            settings: PromptExecutionSettings,
            **kwargs: Any,
        ) -> AsyncGenerator[list["StreamingChatMessageContent"], Any]:
            if "What is 2 + 2?" in str(chat_history):
                # Mock response for calculator tool test - single message with function call
                yield [
                    StreamingChatMessageContent(
                        choice_index=0,
                        inner_content=None,
                        ai_model_id="gpt-4o-mini",
                        metadata={
                            "logprobs": None,
                            "id": "chatcmpl-AooRjGxKtdTke46keWkBQBKg033XW",
                            "created": 1736673679,
                            "usage": {"prompt_tokens": 53, "completion_tokens": 13},
                        },
                        role=AuthorRole.ASSISTANT,
                        items=[  # type: ignore
                            FunctionCallContent(
                                id="call_n8135GXc2kbiaaDdpImsB1VW",
                                function_name="calculator",
                                plugin_name="autogen_tools",
                                arguments="",
                                content_type="function_call",  # type: ignore
                            )
                        ],
                        finish_reason=None,
                        function_invoke_attempt=0,
                    )
                ]
            else:
                # First chunk with empty content and role
                yield [
                    StreamingChatMessageContent(
                        choice_index=0,
                        inner_content=ChatCompletionChunk(
                            id="chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9",
                            choices=[
                                Choice(delta=ChoiceDelta(content="", role="assistant"), finish_reason=None, index=0)
                            ],
                            created=1736674044,
                            model="gpt-4o-mini-2024-07-18",
                            object="chat.completion.chunk",
                            service_tier="scale",
                            system_fingerprint="fingerprint",
                            usage=CompletionUsage(prompt_tokens=20, completion_tokens=9, total_tokens=29),
                        ),
                        ai_model_id="gpt-4o-mini",
                        metadata={"id": "chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9", "created": 1736674044},
                        role=AuthorRole.ASSISTANT,
                        items=[StreamingTextContent(choice_index=0, text="")],  # type: ignore
                    )
                ]

                # Second chunk with "Hello"
                yield [
                    StreamingChatMessageContent(
                        choice_index=0,
                        inner_content=ChatCompletionChunk(
                            id="chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9",
                            choices=[Choice(delta=ChoiceDelta(content="Hello"), finish_reason=None, index=0)],
                            created=1736674044,
                            model="gpt-4o-mini-2024-07-18",
                            object="chat.completion.chunk",
                            service_tier="scale",
                            system_fingerprint="fingerprint",
                            usage=CompletionUsage(prompt_tokens=20, completion_tokens=9, total_tokens=29),
                        ),
                        ai_model_id="gpt-4o-mini",
                        metadata={"id": "chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9", "created": 1736674044},
                        role=AuthorRole.ASSISTANT,
                        items=[StreamingTextContent(choice_index=0, text="Hello")],  # type: ignore
                    )
                ]

                # Third chunk with "!"
                yield [
                    StreamingChatMessageContent(
                        choice_index=0,
                        inner_content=ChatCompletionChunk(
                            id="chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9",
                            choices=[Choice(delta=ChoiceDelta(content="!"), finish_reason=None, index=0)],
                            created=1736674044,
                            model="gpt-4o-mini-2024-07-18",
                            object="chat.completion.chunk",
                            service_tier="scale",
                            system_fingerprint="fingerprint",
                            usage=CompletionUsage(prompt_tokens=20, completion_tokens=9, total_tokens=29),
                        ),
                        ai_model_id="gpt-4o-mini",
                        metadata={"id": "chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9", "created": 1736674044},
                        role=AuthorRole.ASSISTANT,
                        items=[StreamingTextContent(choice_index=0, text="!")],  # type: ignore
                    )
                ]

                # Fourth chunk with " How can I assist you today?"
                yield [
                    StreamingChatMessageContent(
                        choice_index=0,
                        inner_content=ChatCompletionChunk(
                            id="chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9",
                            choices=[
                                Choice(
                                    delta=ChoiceDelta(content=" How can I assist you today?"),
                                    finish_reason=None,
                                    index=0,
                                )
                            ],
                            created=1736674044,
                            model="gpt-4o-mini-2024-07-18",
                            object="chat.completion.chunk",
                            service_tier="scale",
                            system_fingerprint="fingerprint",
                            usage=CompletionUsage(prompt_tokens=20, completion_tokens=9, total_tokens=29),
                        ),
                        ai_model_id="gpt-4o-mini",
                        metadata={
                            "id": "chatcmpl-AooXcRvW2Dhvr6VL6tqatzvRMXTx9",
                            "created": 1736674044,
                            "usage": {"prompt_tokens": 20, "completion_tokens": 9, "total_tokens": 29},
                        },
                        role=AuthorRole.ASSISTANT,
                        items=[StreamingTextContent(choice_index=0, text=" How can I assist you today?")],
                        finish_reason=FinishReason.STOP,
                    )
                ]

        mock_client.get_chat_message_contents = mock_get_chat_message_contents
        mock_client.get_streaming_chat_message_contents = mock_get_streaming_chat_message_contents
        return mock_client

    return AzureChatCompletion(
        deployment_name=deployment_name,
        endpoint=endpoint,
        api_key=api_key,
    )


@pytest.mark.asyncio
async def test_sk_chat_completion_with_tools(sk_client: AzureChatCompletion) -> None:
    # Create adapter
    adapter = SKChatCompletionAdapter(sk_client)

    # Create kernel
    kernel = Kernel(memory=NullMemory())

    # Create calculator tool instance
    tool = CalculatorTool()

    # Test messages
    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="What is 2 + 2?", source="user"),
    ]

    # Call create with tool
    result = await adapter.create(messages=messages, tools=[tool], extra_create_args={"kernel": kernel})

    # Verify response
    assert isinstance(result.content, list)
    assert result.finish_reason == "function_calls"
    assert result.usage.prompt_tokens >= 0
    assert result.usage.completion_tokens >= 0
    assert not result.cached


@pytest.mark.asyncio
async def test_sk_chat_completion_without_tools(sk_client: AzureChatCompletion) -> None:
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())

    # Test messages
    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Say hello!", source="user"),
    ]

    # Call create without tools
    result = await adapter.create(messages=messages, extra_create_args={"kernel": kernel})

    # Verify response
    assert isinstance(result.content, str)
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens >= 0
    assert result.usage.completion_tokens >= 0
    assert not result.cached


@pytest.mark.asyncio
async def test_sk_chat_completion_stream_with_tools(sk_client: AzureChatCompletion) -> None:
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())

    # Create calculator tool
    tool = CalculatorTool()

    # Test messages
    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="What is 2 + 2?", source="user"),
    ]

    # Call create_stream with tool
    response_chunks: list[CreateResult | str] = []
    async for chunk in adapter.create_stream(messages=messages, tools=[tool], extra_create_args={"kernel": kernel}):
        response_chunks.append(chunk)

    # Verify response
    assert len(response_chunks) > 0
    final_chunk = response_chunks[-1]
    assert isinstance(final_chunk, CreateResult)
    assert isinstance(final_chunk.content, list)  # Function calls
    assert final_chunk.finish_reason == "function_calls"
    assert final_chunk.usage.prompt_tokens >= 0
    assert final_chunk.usage.completion_tokens >= 0
    assert not final_chunk.cached


@pytest.mark.asyncio
async def test_sk_chat_completion_stream_without_tools(sk_client: AzureChatCompletion) -> None:
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())

    # Test messages
    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Say hello!", source="user"),
    ]

    # Call create_stream without tools
    response_chunks: list[CreateResult | str] = []
    async for chunk in adapter.create_stream(messages=messages, extra_create_args={"kernel": kernel}):
        response_chunks.append(chunk)

    # Verify response
    assert len(response_chunks) > 0
    # All chunks except last should be strings
    for chunk in response_chunks[:-1]:
        assert isinstance(chunk, str)

    # Final chunk should be CreateResult
    final_chunk = response_chunks[-1]
    assert isinstance(final_chunk, CreateResult)
    assert isinstance(final_chunk.content, str)
    assert final_chunk.finish_reason == "stop"
    assert final_chunk.usage.prompt_tokens >= 0
    assert final_chunk.usage.completion_tokens >= 0
    assert not final_chunk.cached


@pytest.mark.asyncio
async def test_sk_chat_completion_default_model_info(sk_client: AzureChatCompletion) -> None:
    # Create adapter with default model_info
    adapter = SKChatCompletionAdapter(sk_client)

    # Verify default model_info values
    assert adapter.model_info["vision"] is False
    assert adapter.model_info["function_calling"] is False
    assert adapter.model_info["json_output"] is False
    assert adapter.model_info["family"] == ModelFamily.UNKNOWN

    # Verify capabilities returns the same ModelInfo
    assert adapter.capabilities == adapter.model_info


@pytest.mark.asyncio
async def test_sk_chat_completion_custom_model_info(sk_client: AzureChatCompletion) -> None:
    # Create custom model info
    custom_model_info = ModelInfo(vision=True, function_calling=True, json_output=True, family=ModelFamily.GPT_4)

    # Create adapter with custom model_info
    adapter = SKChatCompletionAdapter(sk_client, model_info=custom_model_info)

    # Verify custom model_info values
    assert adapter.model_info["vision"] is True
    assert adapter.model_info["function_calling"] is True
    assert adapter.model_info["json_output"] is True
    assert adapter.model_info["family"] == ModelFamily.GPT_4

    # Verify capabilities returns the same ModelInfo
    assert adapter.capabilities == adapter.model_info


@pytest.mark.asyncio
async def test_sk_chat_completion_r1_content() -> None:
    async def mock_get_chat_message_contents(
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs: Any,
    ) -> list[ChatMessageContent]:
        return [
            ChatMessageContent(
                ai_model_id="r1",
                role=AuthorRole.ASSISTANT,
                metadata={"usage": {"prompt_tokens": 20, "completion_tokens": 9}},
                items=[TextContent(text="<think>Reasoning...</think> Hello!")],
                finish_reason=FinishReason.STOP,
            )
        ]

    async def mock_get_streaming_chat_message_contents(
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs: Any,
    ) -> AsyncGenerator[list["StreamingChatMessageContent"], Any]:
        chunks = ["<think>Reasoning...</think>", " Hello!"]
        for i, chunk in enumerate(chunks):
            yield [
                StreamingChatMessageContent(
                    choice_index=0,
                    inner_content=ChatCompletionChunk(
                        id=f"chatcmpl-{i}",
                        choices=[Choice(delta=ChoiceDelta(content=chunk), finish_reason=None, index=0)],
                        created=1736674044,
                        model="r1",
                        object="chat.completion.chunk",
                        service_tier="scale",
                        system_fingerprint="fingerprint",
                        usage=CompletionUsage(prompt_tokens=20, completion_tokens=9, total_tokens=29),
                    ),
                    ai_model_id="gpt-4o-mini",
                    metadata={"id": f"chatcmpl-{i}", "created": 1736674044},
                    role=AuthorRole.ASSISTANT,
                    items=[StreamingTextContent(choice_index=0, text=chunk)],
                    finish_reason=FinishReason.STOP if i == len(chunks) - 1 else None,
                )
            ]

    mock_client = AsyncMock(spec=AzureChatCompletion)
    mock_client.get_chat_message_contents = mock_get_chat_message_contents
    mock_client.get_streaming_chat_message_contents = mock_get_streaming_chat_message_contents

    kernel = Kernel(memory=NullMemory())

    adapter = SKChatCompletionAdapter(
        mock_client,
        kernel=kernel,
        model_info=ModelInfo(vision=False, function_calling=False, json_output=False, family=ModelFamily.R1),
    )

    result = await adapter.create(messages=[UserMessage(content="Say hello!", source="user")])
    assert result.finish_reason == "stop"
    assert result.content == "Hello!"
    assert result.thought == "Reasoning..."

    response_chunks: list[CreateResult | str] = []
    async for chunk in adapter.create_stream(messages=[UserMessage(content="Say hello!", source="user")]):
        response_chunks.append(chunk)
    assert len(response_chunks) > 0
    assert isinstance(response_chunks[-1], CreateResult)
    assert response_chunks[-1].finish_reason == "stop"
    assert response_chunks[-1].content == "Hello!"
    assert response_chunks[-1].thought == "Reasoning..."
