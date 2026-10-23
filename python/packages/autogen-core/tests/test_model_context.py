import json
from typing import Any, AsyncGenerator, List, Literal, Mapping, Optional, Sequence, Union

import pytest
from autogen_core import CancellationToken, FunctionCall
from autogen_core.model_context import (
    BufferedChatCompletionContext,
    HeadAndTailChatCompletionContext,
    TokenLimitedChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    RequestUsage,
    UserMessage,
)
from autogen_core.models._model_client import ModelFamily, ModelInfo
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from pydantic import BaseModel


class _MessageCountingChatCompletionClient(ChatCompletionClient):
    component_type = "model"

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        raise NotImplementedError()

    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        raise NotImplementedError()

    async def close(self) -> None:
        pass

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return len(messages)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 4 - len(messages)

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        return ModelCapabilities(vision=False, function_calling=True, json_output=False)  # type: ignore

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=False,
            family=ModelFamily.UNKNOWN,
            structured_output=False,
        )


@pytest.mark.asyncio
async def test_buffered_model_context() -> None:
    model_context = BufferedChatCompletionContext(buffer_size=2)
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    await model_context.add_message(messages[0])
    await model_context.add_message(messages[1])
    await model_context.add_message(messages[2])

    retrieved = await model_context.get_messages()
    assert len(retrieved) == 2
    assert retrieved[0] == messages[1]
    assert retrieved[1] == messages[2]

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    await model_context.add_message(messages[0])
    await model_context.add_message(messages[1])
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 2
    assert retrieved[0] == messages[0]
    assert retrieved[1] == messages[1]


@pytest.mark.asyncio
async def test_head_and_tail_model_context() -> None:
    model_context = HeadAndTailChatCompletionContext(head_size=1, tail_size=1)
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
        AssistantMessage(content="Pike place, space needle, mt rainer", source="assistant"),
        UserMessage(content="More places?", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrived = await model_context.get_messages()
    assert len(retrived) == 3  # 1 head, 1 tail + 1 placeholder.
    assert retrived[0] == messages[0]
    assert retrived[2] == messages[-1]

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    for msg in messages:
        await model_context.add_message(msg)
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrived = await model_context.get_messages()
    assert len(retrived) == 3
    assert retrived[0] == messages[0]
    assert retrived[2] == messages[-1]


@pytest.mark.asyncio
async def test_unbounded_model_context() -> None:
    model_context = UnboundedChatCompletionContext()
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrieved = await model_context.get_messages()
    assert len(retrieved) == 3
    assert retrieved == messages

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    for msg in messages:
        await model_context.add_message(msg)
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 3
    assert retrieved == messages


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_client,token_limit",
    [
        (OpenAIChatCompletionClient(model="gpt-4.1-nano", temperature=0.0, api_key="test"), 30),
        (OllamaChatCompletionClient(model="llama3.3"), 20),
    ],
    ids=["openai", "ollama"],
)
async def test_token_limited_model_context_with_token_limit(
    model_client: ChatCompletionClient, token_limit: int
) -> None:
    model_context = TokenLimitedChatCompletionContext(model_client=model_client, token_limit=token_limit)
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrieved = await model_context.get_messages()
    # Token limit set low, will remove some messages
    # OpenAI: keeps 2 messages (29 tokens with limit 30)
    # Ollama: keeps 1 message (20 tokens with limit 20)
    assert len(retrieved) < len(messages)  # Some messages removed due to token limit
    assert retrieved != messages  # Will not be equal to the original messages

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    for msg in messages:
        await model_context.add_message(msg)
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrieved = await model_context.get_messages()
    assert len(retrieved) < len(messages)  # Some messages removed due to token limit
    assert retrieved != messages


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_client",
    [
        OpenAIChatCompletionClient(model="gpt-4.1-nano", temperature=0.0, api_key="test_key"),
        OllamaChatCompletionClient(model="llama3.3"),
    ],
    ids=["openai", "ollama"],
)
async def test_token_limited_model_context_without_token_limit(model_client: ChatCompletionClient) -> None:
    model_context = TokenLimitedChatCompletionContext(model_client=model_client)
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrieved = await model_context.get_messages()
    assert len(retrieved) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_client,token_limit",
    [
        (OpenAIChatCompletionClient(model="gpt-4.1-nano", temperature=0.0, api_key="test"), 60),
        (OllamaChatCompletionClient(model="llama3.3"), 50),
    ],
    ids=["openai", "ollama"],
)
async def test_token_limited_model_context_openai_with_function_result(
    model_client: ChatCompletionClient, token_limit: int
) -> None:
    model_context = TokenLimitedChatCompletionContext(model_client=model_client, token_limit=token_limit)
    messages: List[LLMMessage] = [
        FunctionExecutionResultMessage(content=[]),
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrieved = await model_context.get_messages()
    assert len(retrieved) == 3  # Token limit set very low, will remove 1 of the messages
    assert type(retrieved[0]) == UserMessage  # Function result should be removed
    assert type(retrieved[1]) == AssistantMessage
    assert type(retrieved[2]) == UserMessage


@pytest.mark.asyncio
async def test_token_limited_model_context_trims_oldest_without_splitting_tool_result() -> None:
    model_context = TokenLimitedChatCompletionContext(
        model_client=_MessageCountingChatCompletionClient(),
        token_limit=4,
    )
    messages: List[LLMMessage] = [
        UserMessage(content="oldest", source="user"),
        AssistantMessage(
            content=[FunctionCall(id="call-1", name="lookup", arguments=json.dumps({"query": "weather"}))],
            source="assistant",
        ),
        FunctionExecutionResultMessage(
            content=[
                FunctionExecutionResult(
                    call_id="call-1",
                    name="lookup",
                    content="sunny",
                    is_error=False,
                )
            ]
        ),
        UserMessage(content="newer", source="user"),
        UserMessage(content="latest", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrieved = await model_context.get_messages()

    assert retrieved == messages[1:]
