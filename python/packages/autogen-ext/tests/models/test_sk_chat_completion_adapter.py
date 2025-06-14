import logging
import os
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import BaseTool, ParametersSchema, ToolSchema
from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)
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
                                plugin_name=None,
                                arguments='{"a": 2, "b": 2}',
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
                # Initial chunk with function call setup
                yield [
                    StreamingChatMessageContent(
                        choice_index=0,
                        inner_content=ChatCompletionChunk(
                            id="chatcmpl-123",
                            choices=[
                                Choice(
                                    delta=ChoiceDelta(
                                        role="assistant",
                                        tool_calls=[
                                            ChoiceDeltaToolCall(
                                                index=0,
                                                id="call_UwVVI0iGEmcPwmKUigJcuuuF",
                                                function=ChoiceDeltaToolCallFunction(name="calculator", arguments=""),
                                                type="function",
                                            )
                                        ],
                                    ),
                                    finish_reason=None,
                                    index=0,
                                )
                            ],
                            created=1736673679,
                            model="gpt-4o-mini",
                            object="chat.completion.chunk",
                        ),
                        ai_model_id="gpt-4o-mini",
                        role=AuthorRole.ASSISTANT,
                        items=[
                            FunctionCallContent(
                                id="call_UwVVI0iGEmcPwmKUigJcuuuF", function_name="calculator", arguments=""
                            )
                        ],
                    )
                ]

                # Arguments chunks
                for arg_chunk in ["{", '"a"', ":", " ", "2", ",", " ", '"b"', ":", " ", "2", "}"]:
                    yield [
                        StreamingChatMessageContent(
                            choice_index=0,
                            inner_content=ChatCompletionChunk(
                                id="chatcmpl-123",
                                choices=[
                                    Choice(
                                        delta=ChoiceDelta(
                                            tool_calls=[
                                                ChoiceDeltaToolCall(
                                                    index=0, function=ChoiceDeltaToolCallFunction(arguments=arg_chunk)
                                                )
                                            ]
                                        ),
                                        finish_reason=None,
                                        index=0,
                                    )
                                ],
                                created=1736673679,
                                model="gpt-4o-mini",
                                object="chat.completion.chunk",
                            ),
                            ai_model_id="gpt-4o-mini",
                            role=AuthorRole.ASSISTANT,
                            items=[FunctionCallContent(function_name="calculator", arguments=arg_chunk)],
                        )
                    ]

                # Final chunk with finish reason
                yield [
                    StreamingChatMessageContent(  # type: ignore
                        choice_index=0,
                        inner_content=ChatCompletionChunk(
                            id="chatcmpl-123",
                            choices=[Choice(delta=ChoiceDelta(), finish_reason="tool_calls", index=0)],
                            created=1736673679,
                            model="gpt-4o-mini",
                            object="chat.completion.chunk",
                            usage=CompletionUsage(prompt_tokens=53, completion_tokens=13, total_tokens=66),
                        ),
                        ai_model_id="gpt-4o-mini",
                        role=AuthorRole.ASSISTANT,
                        finish_reason=FinishReason.TOOL_CALLS,
                        metadata={"usage": {"prompt_tokens": 53, "completion_tokens": 13}},
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
async def test_sk_chat_completion_with_prompt_tools(sk_client: AzureChatCompletion) -> None:
    # Create adapter
    adapter = SKChatCompletionAdapter(sk_client)

    # Create kernel
    kernel = Kernel(memory=NullMemory())

    # Create calculator tool instance
    tool: ToolSchema = ToolSchema(
        name="calculator",
        description="Add two numbers together",
        parameters=ParametersSchema(
            type="object",
            properties={
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            required=["a", "b"],
        ),
    )

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
async def test_sk_chat_completion_without_tools(
    sk_client: AzureChatCompletion, caplog: pytest.LogCaptureFixture
) -> None:
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())

    # Test messages
    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Say hello!", source="user"),
    ]

    with caplog.at_level(logging.INFO):
        # Call create without tools
        result = await adapter.create(messages=messages, extra_create_args={"kernel": kernel})

        # Verify response
        assert isinstance(result.content, str)
        assert result.finish_reason == "stop"
        assert result.usage.prompt_tokens >= 0
        assert result.usage.completion_tokens >= 0
        assert not result.cached

        # Check log output
        assert "LLMCall" in caplog.text and result.content in caplog.text


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
async def test_sk_chat_completion_stream_without_tools(
    sk_client: AzureChatCompletion, caplog: pytest.LogCaptureFixture
) -> None:
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
    with caplog.at_level(logging.INFO):
        async for chunk in adapter.create_stream(messages=messages, extra_create_args={"kernel": kernel}):
            response_chunks.append(chunk)

        assert "LLMStreamStart" in caplog.text
        assert "LLMStreamEnd" in caplog.text

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
        assert final_chunk.content in caplog.text


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
    custom_model_info = ModelInfo(
        vision=True, function_calling=True, json_output=True, family=ModelFamily.GPT_4, structured_output=False
    )

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
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.R1, structured_output=False
        ),
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


@pytest.mark.asyncio
async def test_sk_chat_completion_stream_with_multiple_function_calls() -> None:
    """
    This test returns two distinct function calls via streaming, each one arriving in pieces.
    We intentionally set name, plugin_name, and function_name in the later partial chunks so
    that _merge_function_call_content is triggered to update them.
    """

    async def mock_get_streaming_chat_message_contents(
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs: Any,
    ) -> AsyncGenerator[list["StreamingChatMessageContent"], Any]:
        # First partial chunk for call_1
        yield [
            StreamingChatMessageContent(
                choice_index=0,
                inner_content=ChatCompletionChunk(
                    id="chunk-id-1",
                    choices=[
                        Choice(
                            delta=ChoiceDelta(
                                role="assistant",
                                tool_calls=[
                                    ChoiceDeltaToolCall(
                                        index=0,
                                        id="call_1",
                                        function=ChoiceDeltaToolCallFunction(name=None, arguments='{"arg1":'),
                                        type="function",
                                    )
                                ],
                            ),
                            finish_reason=None,
                            index=0,
                        )
                    ],
                    created=1736679999,
                    model="gpt-4o-mini",
                    object="chat.completion.chunk",
                ),
                ai_model_id="gpt-4o-mini",
                role=AuthorRole.ASSISTANT,
                items=[
                    FunctionCallContent(
                        id="call_1",
                        # no plugin_name/function_name yet
                        name=None,
                        arguments='{"arg1":',
                    )
                ],
            )
        ]
        # Second partial chunk for call_1 (updates plugin_name/function_name)
        yield [
            StreamingChatMessageContent(
                choice_index=0,
                inner_content=ChatCompletionChunk(
                    id="chunk-id-2",
                    choices=[
                        Choice(
                            delta=ChoiceDelta(
                                tool_calls=[
                                    ChoiceDeltaToolCall(
                                        index=0,
                                        function=ChoiceDeltaToolCallFunction(
                                            # Provide the rest of the arguments
                                            arguments='"value1"}',
                                            name="firstFunction",
                                        ),
                                    )
                                ]
                            ),
                            finish_reason=None,
                            index=0,
                        )
                    ],
                    created=1736679999,
                    model="gpt-4o-mini",
                    object="chat.completion.chunk",
                ),
                ai_model_id="gpt-4o-mini",
                role=AuthorRole.ASSISTANT,
                items=[
                    FunctionCallContent(
                        id="call_1", plugin_name="myPlugin", function_name="firstFunction", arguments='"value1"}'
                    )
                ],
            )
        ]
        # Now partial chunk for a second call, call_2
        yield [
            StreamingChatMessageContent(
                choice_index=0,
                inner_content=ChatCompletionChunk(
                    id="chunk-id-3",
                    choices=[
                        Choice(
                            delta=ChoiceDelta(
                                tool_calls=[
                                    ChoiceDeltaToolCall(
                                        index=0,
                                        id="call_2",
                                        function=ChoiceDeltaToolCallFunction(name=None, arguments='{"arg2":"another"}'),
                                        type="function",
                                    )
                                ],
                            ),
                            finish_reason=None,
                            index=0,
                        )
                    ],
                    created=1736679999,
                    model="gpt-4o-mini",
                    object="chat.completion.chunk",
                ),
                ai_model_id="gpt-4o-mini",
                role=AuthorRole.ASSISTANT,
                items=[FunctionCallContent(id="call_2", arguments='{"arg2":"another"}')],
            )
        ]
        # Next partial chunk updates name, plugin_name, function_name for call_2
        yield [
            StreamingChatMessageContent(
                choice_index=0,
                inner_content=ChatCompletionChunk(
                    id="chunk-id-4",
                    choices=[
                        Choice(
                            delta=ChoiceDelta(
                                tool_calls=[
                                    ChoiceDeltaToolCall(
                                        index=0, function=ChoiceDeltaToolCallFunction(name="secondFunction")
                                    )
                                ]
                            ),
                            finish_reason=None,
                            index=0,
                        )
                    ],
                    created=1736679999,
                    model="gpt-4o-mini",
                    object="chat.completion.chunk",
                ),
                ai_model_id="gpt-4o-mini",
                role=AuthorRole.ASSISTANT,
                items=[
                    FunctionCallContent(
                        id="call_2",
                        name="someFancyName",
                        plugin_name="anotherPlugin",
                        function_name="secondFunction",
                    )
                ],
            )
        ]
        # Final chunk signals finish with tool_calls
        yield [
            StreamingChatMessageContent(  # type: ignore
                choice_index=0,
                inner_content=ChatCompletionChunk(
                    id="chunk-id-5",
                    choices=[Choice(delta=ChoiceDelta(), finish_reason="tool_calls", index=0)],
                    created=1736679999,
                    model="gpt-4o-mini",
                    object="chat.completion.chunk",
                    usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                ),
                ai_model_id="gpt-4o-mini",
                role=AuthorRole.ASSISTANT,
                finish_reason=FinishReason.TOOL_CALLS,
                metadata={"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            )
        ]

    # Mock SK client
    mock_client = AsyncMock(spec=AzureChatCompletion)
    mock_client.get_streaming_chat_message_contents = mock_get_streaming_chat_message_contents

    # Create adapter and kernel
    kernel = Kernel(memory=NullMemory())
    adapter = SKChatCompletionAdapter(mock_client, kernel=kernel)

    # Call create_stream with no actual tools (we just test the multiple calls)
    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Call two different plugin functions", source="user"),
    ]

    # Collect streaming outputs
    response_chunks: list[CreateResult | str] = []
    async for chunk in adapter.create_stream(messages=messages):
        response_chunks.append(chunk)

    # The final chunk should be a CreateResult with function_calls
    assert len(response_chunks) > 0
    final_chunk = response_chunks[-1]
    assert isinstance(final_chunk, CreateResult)
    assert final_chunk.finish_reason == "function_calls"
    assert isinstance(final_chunk.content, list)
    assert len(final_chunk.content) == 2  # We expect 2 calls

    # Verify first call merged name + arguments
    first_call = final_chunk.content[0]
    assert first_call.id == "call_1"
    assert first_call.name == "myPlugin-firstFunction"  # pluginName-functionName
    assert '{"arg1":"value1"}' in first_call.arguments

    # Verify second call also merged everything
    second_call = final_chunk.content[1]
    assert second_call.id == "call_2"
    assert second_call.name == "anotherPlugin-secondFunction"
    assert '{"arg2":"another"}' in second_call.arguments


@pytest.mark.asyncio
async def test_sk_chat_completion_with_function_call_and_execution_result_messages() -> None:
    """
    Test that _convert_to_chat_history can properly handle a conversation
    that includes both an assistant function-call message and a function
    execution result message in the same sequence.
    """
    # Mock the SK client to return some placeholder response
    mock_client = AsyncMock(spec=AzureChatCompletion)
    mock_client.get_chat_message_contents = AsyncMock(
        return_value=[
            ChatMessageContent(
                ai_model_id="test-model",
                role=AuthorRole.ASSISTANT,
                items=[TextContent(text="All done!")],
                finish_reason=FinishReason.STOP,
                metadata={"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            )
        ]
    )

    adapter = SKChatCompletionAdapter(sk_client=mock_client, kernel=Kernel(memory=NullMemory()))

    # Messages include:
    #  1) SystemMessage
    #  2) UserMessage
    #  3) AssistantMessage with a function call
    #  4) FunctionExecutionResultMessage
    #  5) AssistantMessage with plain text

    messages: list[LLMMessage] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="What is 3 + 5?", source="user"),
        AssistantMessage(
            content=[
                FunctionCall(
                    id="call_1",
                    name="calculator",
                    arguments='{"a":3,"b":5}',
                )
            ],
            thought="Let me call the calculator function",
            source="assistant",
        ),
        FunctionExecutionResultMessage(
            content=[
                FunctionExecutionResult(
                    call_id="call_1",
                    name="calculator",
                    content="8",
                )
            ]
        ),
        AssistantMessage(content="The answer is 8.", source="assistant"),
    ]

    # Run create (which triggers _convert_to_chat_history internally)
    result = await adapter.create(messages=messages)

    # Verify final CreateResult
    assert isinstance(result.content, str)
    assert "All done!" in result.content
    assert result.finish_reason == "stop"

    # Ensure the underlying client was called with a properly built ChatHistory
    mock_client.get_chat_message_contents.assert_awaited_once()
    chat_history_arg = mock_client.get_chat_message_contents.call_args[0][0]  # The ChatHistory passed in

    # Expecting 5 messages in the ChatHistory
    assert len(chat_history_arg) == 6

    # 1) System message
    assert chat_history_arg[0].role == AuthorRole.SYSTEM
    assert chat_history_arg[0].items[0].text == "You are a helpful assistant."

    # 2) User message
    assert chat_history_arg[1].role == AuthorRole.USER
    assert chat_history_arg[1].items[0].text == "What is 3 + 5?"

    # 3) Assistant message with thought
    assert chat_history_arg[2].role == AuthorRole.ASSISTANT
    assert chat_history_arg[2].items[0].text == "Let me call the calculator function"

    # 4) Assistant message with function call
    assert chat_history_arg[3].role == AuthorRole.ASSISTANT
    assert chat_history_arg[3].finish_reason == FinishReason.TOOL_CALLS
    # Should have one FunctionCallContent
    func_call_contents = chat_history_arg[3].items
    assert len(func_call_contents) == 1
    assert func_call_contents[0].id == "call_1"
    assert func_call_contents[0].function_name == "calculator"
    assert func_call_contents[0].arguments == '{"a":3,"b":5}'
    assert func_call_contents[0].plugin_name == "autogen_tools"

    # 5) Function execution result message
    assert chat_history_arg[4].role == AuthorRole.TOOL
    tool_contents = chat_history_arg[4].items
    assert len(tool_contents) == 1
    assert tool_contents[0].id == "call_1"
    assert tool_contents[0].result == "8"
    assert tool_contents[0].function_name == "calculator"
    assert tool_contents[0].plugin_name == "autogen_tools"

    # 6) Assistant message with plain text
    assert chat_history_arg[5].role == AuthorRole.ASSISTANT
    assert chat_history_arg[5].items[0].text == "The answer is 8."
