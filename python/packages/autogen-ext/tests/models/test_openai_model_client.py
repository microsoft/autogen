import asyncio
import json
import os
from typing import Annotated, Any, AsyncGenerator, Dict, Generic, List, Literal, Tuple, TypeVar
from unittest.mock import MagicMock

import httpx
import pytest
from autogen_core import CancellationToken, FunctionCall, Image
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.models._model_client import ModelFamily
from autogen_core.tools import BaseTool, FunctionTool
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.models.openai._model_info import resolve_model
from autogen_ext.models.openai._openai_client import calculate_vision_tokens, convert_tools, to_oai_type
from openai.resources.beta.chat.completions import AsyncCompletions as BetaAsyncCompletions
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion, ParsedChatCompletionMessage, ParsedChoice
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel, Field


class _MockChatCompletion:
    def __init__(self, chat_completions: List[ChatCompletion]) -> None:
        self._saved_chat_completions = chat_completions
        self.curr_index = 0
        self.calls: List[Dict[str, Any]] = []

    async def mock_create(
        self, *args: Any, **kwargs: Any
    ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        self.calls.append(kwargs)  # Save the call
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self.curr_index]
        self.curr_index += 1
        return completion


ResponseFormatT = TypeVar("ResponseFormatT", bound=BaseModel)


class _MockBetaChatCompletion(Generic[ResponseFormatT]):
    def __init__(self, chat_completions: List[ParsedChatCompletion[ResponseFormatT]]) -> None:
        self._saved_chat_completions = chat_completions
        self.curr_index = 0
        self.calls: List[Dict[str, Any]] = []

    async def mock_parse(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ParsedChatCompletion[ResponseFormatT]:
        self.calls.append(kwargs)  # Save the call
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self.curr_index]
        self.curr_index += 1
        return completion


def _pass_function(input: str) -> str:
    return "pass"


async def _fail_function(input: str) -> str:
    return "fail"


async def _echo_function(input: str) -> str:
    return input


class MyResult(BaseModel):
    result: str = Field(description="The other description.")


class MyArgs(BaseModel):
    query: str = Field(description="The description.")


class MockChunkDefinition(BaseModel):
    # defining elements for diffentiating mocking chunks
    chunk_choice: ChunkChoice
    usage: CompletionUsage | None


async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
    model = resolve_model(kwargs.get("model", "gpt-4o"))
    mock_chunks_content = ["Hello", " Another Hello", " Yet Another Hello"]

    # The openai api implementations (OpenAI and Litellm) stream chunks of tokens
    # with content as string, and then at the end a token with stop set and finally if
    # usage requested with `"stream_options": {"include_usage": True}` a chunk with the usage data
    mock_chunks = [
        # generate the list of mock chunk content
        MockChunkDefinition(
            chunk_choice=ChunkChoice(
                finish_reason=None,
                index=0,
                delta=ChoiceDelta(
                    content=mock_chunk_content,
                    role="assistant",
                ),
            ),
            usage=None,
        )
        for mock_chunk_content in mock_chunks_content
    ] + [
        # generate the stop chunk
        MockChunkDefinition(
            chunk_choice=ChunkChoice(
                finish_reason="stop",
                index=0,
                delta=ChoiceDelta(
                    content=None,
                    role="assistant",
                ),
            ),
            usage=None,
        )
    ]
    # generate the usage chunk if configured
    if kwargs.get("stream_options", {}).get("include_usage") is True:
        mock_chunks = mock_chunks + [
            # ---- API differences
            # OPENAI API does NOT create a choice
            # LITELLM (proxy) DOES create a choice
            # Not simulating all the API options, just implementing the LITELLM variant
            MockChunkDefinition(
                chunk_choice=ChunkChoice(
                    finish_reason=None,
                    index=0,
                    delta=ChoiceDelta(
                        content=None,
                        role="assistant",
                    ),
                ),
                usage=CompletionUsage(prompt_tokens=3, completion_tokens=3, total_tokens=6),
            )
        ]
    elif kwargs.get("stream_options", {}).get("include_usage") is False:
        pass
    else:
        pass

    for mock_chunk in mock_chunks:
        await asyncio.sleep(0.1)
        yield ChatCompletionChunk(
            id="id",
            choices=[mock_chunk.chunk_choice],
            created=0,
            model=model,
            object="chat.completion.chunk",
            usage=mock_chunk.usage,
        )


async def _mock_create(*args: Any, **kwargs: Any) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
    stream = kwargs.get("stream", False)
    model = resolve_model(kwargs.get("model", "gpt-4o"))
    if not stream:
        await asyncio.sleep(0.1)
        return ChatCompletion(
            id="id",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )
    else:
        return _mock_create_stream(*args, **kwargs)


@pytest.mark.asyncio
async def test_openai_chat_completion_client() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    assert client


@pytest.mark.asyncio
async def test_custom_model_with_capabilities() -> None:
    with pytest.raises(ValueError, match="model_info is required"):
        client = OpenAIChatCompletionClient(model="dummy_model", base_url="https://api.dummy.com/v0", api_key="api_key")

    client = OpenAIChatCompletionClient(
        model="dummy_model",
        base_url="https://api.dummy.com/v0",
        api_key="api_key",
        model_info={"vision": False, "function_calling": False, "json_output": False, "family": ModelFamily.UNKNOWN},
    )
    assert client


@pytest.mark.asyncio
async def test_azure_openai_chat_completion_client() -> None:
    client = AzureOpenAIChatCompletionClient(
        azure_deployment="gpt-4o-1",
        model="gpt-4o",
        api_key="api_key",
        api_version="2020-08-04",
        azure_endpoint="https://dummy.com",
        model_info={"vision": True, "function_calling": True, "json_output": True, "family": ModelFamily.GPT_4O},
    )
    assert client


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    result = await client.create(messages=[UserMessage(content="Hello", source="user")])
    assert result.content == "Hello"


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create_stream_with_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(
        messages=[UserMessage(content="Hello", source="user")],
        # include_usage not the default of the OPENAI API and must be explicitly set
        extra_create_args={"stream_options": {"include_usage": True}},
    ):
        chunks.append(chunk)
    assert chunks[0] == "Hello"
    assert chunks[1] == " Another Hello"
    assert chunks[2] == " Yet Another Hello"
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
    assert chunks[-1].usage == RequestUsage(prompt_tokens=3, completion_tokens=3)


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create_stream_no_usage_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(
        messages=[UserMessage(content="Hello", source="user")],
        # include_usage not the default of the OPENAI APIis ,
        # it can be explicitly set
        # or just not declared which is the default
        # extra_create_args={"stream_options": {"include_usage": False}},
    ):
        chunks.append(chunk)
    assert chunks[0] == "Hello"
    assert chunks[1] == " Another Hello"
    assert chunks[2] == " Yet Another Hello"
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
    assert chunks[-1].usage == RequestUsage(prompt_tokens=0, completion_tokens=0)


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create_stream_no_usage_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    chunks: List[str | CreateResult] = []
    async for chunk in client.create_stream(
        messages=[UserMessage(content="Hello", source="user")],
        # include_usage is not the default of the OPENAI API ,
        # it can be explicitly set
        # or just not declared which is the default
        extra_create_args={"stream_options": {"include_usage": False}},
    ):
        chunks.append(chunk)
    assert chunks[0] == "Hello"
    assert chunks[1] == " Another Hello"
    assert chunks[2] == " Yet Another Hello"
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
    assert chunks[-1].usage == RequestUsage(prompt_tokens=0, completion_tokens=0)


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    cancellation_token = CancellationToken()
    task = asyncio.create_task(
        client.create(messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token)
    )
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create_stream_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    cancellation_token = CancellationToken()
    stream = client.create_stream(
        messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token
    )
    assert await anext(stream)
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        async for _ in stream:
            pass


@pytest.mark.asyncio
async def test_openai_chat_completion_client_count_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    messages: List[LLMMessage] = [
        SystemMessage(content="Hello"),
        UserMessage(content="Hello", source="user"),
        AssistantMessage(content="Hello", source="assistant"),
        UserMessage(
            content=[
                "str1",
                Image.from_base64(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
                ),
            ],
            source="user",
        ),
        FunctionExecutionResultMessage(content=[FunctionExecutionResult(content="Hello", call_id="1")]),
    ]

    def tool1(test: str, test2: str) -> str:
        return test + test2

    def tool2(test1: int, test2: List[int]) -> str:
        return str(test1) + str(test2)

    tools = [FunctionTool(tool1, description="example tool 1"), FunctionTool(tool2, description="example tool 2")]

    mockcalculate_vision_tokens = MagicMock()
    monkeypatch.setattr("autogen_ext.models.openai._openai_client.calculate_vision_tokens", mockcalculate_vision_tokens)

    num_tokens = client.count_tokens(messages, tools=tools)
    assert num_tokens

    # Check that calculate_vision_tokens was called
    mockcalculate_vision_tokens.assert_called_once()

    remaining_tokens = client.remaining_tokens(messages, tools=tools)
    assert remaining_tokens


@pytest.mark.parametrize(
    "mock_size, expected_num_tokens",
    [
        ((1, 1), 255),
        ((512, 512), 255),
        ((2048, 512), 765),
        ((2048, 2048), 765),
        ((512, 1024), 425),
    ],
)
def test_openai_count_image_tokens(mock_size: Tuple[int, int], expected_num_tokens: int) -> None:
    # Step 1: Mock the Image class with only the 'image' attribute
    mock_image_attr = MagicMock()
    mock_image_attr.size = mock_size

    mock_image = MagicMock()
    mock_image.image = mock_image_attr

    # Directly call calculate_vision_tokens and check the result
    calculated_tokens = calculate_vision_tokens(mock_image, detail="auto")
    assert calculated_tokens == expected_num_tokens


def test_convert_tools_accepts_both_func_tool_and_schema() -> None:
    def my_function(arg: str, other: Annotated[int, "int arg"], nonrequired: int = 5) -> MyResult:
        return MyResult(result="test")

    tool = FunctionTool(my_function, description="Function tool.")
    schema = tool.schema

    converted_tool_schema = convert_tools([tool, schema])

    assert len(converted_tool_schema) == 2
    assert converted_tool_schema[0] == converted_tool_schema[1]


def test_convert_tools_accepts_both_tool_and_schema() -> None:
    class MyTool(BaseTool[MyArgs, MyResult]):
        def __init__(self) -> None:
            super().__init__(
                args_type=MyArgs,
                return_type=MyResult,
                name="TestTool",
                description="Description of test tool.",
            )

        async def run(self, args: MyArgs, cancellation_token: CancellationToken) -> MyResult:
            return MyResult(result="value")

    tool = MyTool()
    schema = tool.schema

    converted_tool_schema = convert_tools([tool, schema])

    assert len(converted_tool_schema) == 2
    assert converted_tool_schema[0] == converted_tool_schema[1]


@pytest.mark.asyncio
async def test_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    model = "gpt-4o-2024-11-20"
    chat_completions: List[ParsedChatCompletion[AgentResponse]] = [
        ParsedChatCompletion(
            id="id1",
            choices=[
                ParsedChoice(
                    finish_reason="stop",
                    index=0,
                    message=ParsedChatCompletionMessage(
                        content=json.dumps(
                            {
                                "thoughts": "The user explicitly states that they are happy without any indication of sadness or neutrality.",
                                "response": "happy",
                            }
                        ),
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
    ]
    mock = _MockBetaChatCompletion(chat_completions)
    monkeypatch.setattr(BetaAsyncCompletions, "parse", mock.mock_parse)

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        response_format=AgentResponse,  # type: ignore
    )

    # Test that the openai client was called with the correct response format.
    create_result = await model_client.create(messages=[UserMessage(content="I am happy.", source="user")])
    assert isinstance(create_result.content, str)
    response = AgentResponse.model_validate(json.loads(create_result.content))
    assert (
        response.thoughts
        == "The user explicitly states that they are happy without any indication of sadness or neutrality."
    )
    assert response.response == "happy"


@pytest.mark.asyncio
async def test_r1_think_field(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
        chunks = ["<think> Hello</think>", " Another Hello", " Yet Another Hello"]
        for i, chunk in enumerate(chunks):
            await asyncio.sleep(0.1)
            yield ChatCompletionChunk(
                id="id",
                choices=[
                    ChunkChoice(
                        finish_reason="stop" if i == len(chunks) - 1 else None,
                        index=0,
                        delta=ChoiceDelta(
                            content=chunk,
                            role="assistant",
                        ),
                    ),
                ],
                created=0,
                model="r1",
                object="chat.completion.chunk",
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    async def _mock_create(*args: Any, **kwargs: Any) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        stream = kwargs.get("stream", False)
        if not stream:
            await asyncio.sleep(0.1)
            return ChatCompletion(
                id="id",
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content="<think> Hello</think> Another Hello Yet Another Hello", role="assistant"
                        ),
                    )
                ],
                created=0,
                model="r1",
                object="chat.completion",
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )
        else:
            return _mock_create_stream(*args, **kwargs)

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)

    model_client = OpenAIChatCompletionClient(
        model="r1",
        api_key="",
        model_info={"family": ModelFamily.R1, "vision": False, "function_calling": False, "json_output": False},
    )

    # Successful completion with think field.
    create_result = await model_client.create(messages=[UserMessage(content="I am happy.", source="user")])
    assert create_result.content == "Another Hello Yet Another Hello"
    assert create_result.finish_reason == "stop"
    assert not create_result.cached
    assert create_result.thought == "Hello"

    # Stream completion with think field.
    chunks: List[str | CreateResult] = []
    async for chunk in model_client.create_stream(messages=[UserMessage(content="Hello", source="user")]):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].content == "Another Hello Yet Another Hello"
    assert chunks[-1].thought == "Hello"
    assert not chunks[-1].cached


@pytest.mark.asyncio
async def test_r1_think_field_not_present(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
        chunks = ["Hello", " Another Hello", " Yet Another Hello"]
        for i, chunk in enumerate(chunks):
            await asyncio.sleep(0.1)
            yield ChatCompletionChunk(
                id="id",
                choices=[
                    ChunkChoice(
                        finish_reason="stop" if i == len(chunks) - 1 else None,
                        index=0,
                        delta=ChoiceDelta(
                            content=chunk,
                            role="assistant",
                        ),
                    ),
                ],
                created=0,
                model="r1",
                object="chat.completion.chunk",
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    async def _mock_create(*args: Any, **kwargs: Any) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        stream = kwargs.get("stream", False)
        if not stream:
            await asyncio.sleep(0.1)
            return ChatCompletion(
                id="id",
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content="Hello Another Hello Yet Another Hello", role="assistant"
                        ),
                    )
                ],
                created=0,
                model="r1",
                object="chat.completion",
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )
        else:
            return _mock_create_stream(*args, **kwargs)

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)

    model_client = OpenAIChatCompletionClient(
        model="r1",
        api_key="",
        model_info={"family": ModelFamily.R1, "vision": False, "function_calling": False, "json_output": False},
    )

    # Warning completion when think field is not present.
    with pytest.warns(UserWarning, match="Could not find <think>..</think> field in model response content."):
        create_result = await model_client.create(messages=[UserMessage(content="I am happy.", source="user")])
        assert create_result.content == "Hello Another Hello Yet Another Hello"
        assert create_result.finish_reason == "stop"
        assert not create_result.cached
        assert create_result.thought is None

    # Stream completion with think field.
    with pytest.warns(UserWarning, match="Could not find <think>..</think> field in model response content."):
        chunks: List[str | CreateResult] = []
        async for chunk in model_client.create_stream(messages=[UserMessage(content="Hello", source="user")]):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert isinstance(chunks[-1], CreateResult)
        assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
        assert chunks[-1].thought is None
        assert not chunks[-1].cached


@pytest.mark.asyncio
async def test_tool_calling(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        # Successful completion, single tool call
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        # Successful completion, parallel tool calls
        ChatCompletion(
            id="id2",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            ),
                            ChatCompletionMessageToolCall(
                                id="2",
                                type="function",
                                function=Function(
                                    name="_fail_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            ),
                            ChatCompletionMessageToolCall(
                                id="3",
                                type="function",
                                function=Function(
                                    name="_echo_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            ),
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        # Warning completion when finish reason is not tool_calls.
        ChatCompletion(
            id="id3",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        # Warning completion when content is not None.
        ChatCompletion(
            id="id4",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content="I should make a tool call.",
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        # Should not be returning tool calls when the tool_calls are empty
        ChatCompletion(
            id="id5",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="I should make a tool call.",
                        tool_calls=[],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        # Should raise warning when function arguments is not a string.
        ChatCompletion(
            id="id6",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function.construct(name="_pass_function", arguments={"input": "task"}),  # type: ignore
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    pass_tool = FunctionTool(_pass_function, description="pass tool.")
    fail_tool = FunctionTool(_fail_function, description="fail tool.")
    echo_tool = FunctionTool(_echo_function, description="echo tool.")
    model_client = OpenAIChatCompletionClient(model=model, api_key="")

    # Single tool call
    create_result = await model_client.create(messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool])
    assert create_result.content == [FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function")]
    # Verify that the tool schema was passed to the model client.
    kwargs = mock.calls[0]
    assert kwargs["tools"] == [{"function": pass_tool.schema, "type": "function"}]
    # Verify finish reason
    assert create_result.finish_reason == "function_calls"

    # Parallel tool calls
    create_result = await model_client.create(
        messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool, fail_tool, echo_tool]
    )
    assert create_result.content == [
        FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function"),
        FunctionCall(id="2", arguments=r'{"input": "task"}', name="_fail_function"),
        FunctionCall(id="3", arguments=r'{"input": "task"}', name="_echo_function"),
    ]
    # Verify that the tool schema was passed to the model client.
    kwargs = mock.calls[1]
    assert kwargs["tools"] == [
        {"function": pass_tool.schema, "type": "function"},
        {"function": fail_tool.schema, "type": "function"},
        {"function": echo_tool.schema, "type": "function"},
    ]
    # Verify finish reason
    assert create_result.finish_reason == "function_calls"

    # Warning completion when finish reason is not tool_calls.
    with pytest.warns(UserWarning, match="Finish reason mismatch"):
        create_result = await model_client.create(
            messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool]
        )
        assert create_result.content == [FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function")]
        assert create_result.finish_reason == "function_calls"

    # Warning completion when content is not None.
    with pytest.warns(UserWarning, match="Both tool_calls and content are present in the message"):
        create_result = await model_client.create(
            messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool]
        )
        assert create_result.content == [FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function")]
        assert create_result.finish_reason == "function_calls"

    # Should not be returning tool calls when the tool_calls are empty
    create_result = await model_client.create(messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool])
    assert create_result.content == "I should make a tool call."
    assert create_result.finish_reason == "stop"

    # Should raise warning when function arguments is not a string.
    with pytest.warns(UserWarning, match="Tool call function arguments field is not a string"):
        create_result = await model_client.create(
            messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool]
        )
        assert create_result.content == [FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function")]
        assert create_result.finish_reason == "function_calls"


async def _test_model_client_basic_completion(model_client: OpenAIChatCompletionClient) -> None:
    # Test basic completion
    create_result = await model_client.create(
        messages=[
            SystemMessage(content="You are a helpful assistant."),
            UserMessage(content="Explain to me how AI works.", source="user"),
        ]
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0


async def _test_model_client_with_function_calling(model_client: OpenAIChatCompletionClient) -> None:
    # Test tool calling
    pass_tool = FunctionTool(_pass_function, name="pass_tool", description="pass session.")
    fail_tool = FunctionTool(_fail_function, name="fail_tool", description="fail session.")
    messages: List[LLMMessage] = [UserMessage(content="Call the pass tool with input 'task'", source="user")]
    create_result = await model_client.create(messages=messages, tools=[pass_tool, fail_tool])
    assert isinstance(create_result.content, list)
    assert len(create_result.content) == 1
    assert isinstance(create_result.content[0], FunctionCall)
    assert create_result.content[0].name == "pass_tool"
    assert json.loads(create_result.content[0].arguments) == {"input": "task"}
    assert create_result.finish_reason == "function_calls"
    assert create_result.usage is not None

    # Test reflection on tool call response.
    messages.append(AssistantMessage(content=create_result.content, source="assistant"))
    messages.append(
        FunctionExecutionResultMessage(
            content=[FunctionExecutionResult(content="passed", call_id=create_result.content[0].id)]
        )
    )
    create_result = await model_client.create(messages=messages)
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0

    # Test parallel tool calling
    messages = [
        UserMessage(
            content="Call both the pass tool with input 'task' and the fail tool also with input 'task'", source="user"
        )
    ]
    create_result = await model_client.create(messages=messages, tools=[pass_tool, fail_tool])
    assert isinstance(create_result.content, list)
    assert len(create_result.content) == 2
    assert isinstance(create_result.content[0], FunctionCall)
    assert create_result.content[0].name == "pass_tool"
    assert json.loads(create_result.content[0].arguments) == {"input": "task"}
    assert isinstance(create_result.content[1], FunctionCall)
    assert create_result.content[1].name == "fail_tool"
    assert json.loads(create_result.content[1].arguments) == {"input": "task"}
    assert create_result.finish_reason == "function_calls"
    assert create_result.usage is not None

    # Test reflection on parallel tool call response.
    messages.append(AssistantMessage(content=create_result.content, source="assistant"))
    messages.append(
        FunctionExecutionResultMessage(
            content=[
                FunctionExecutionResult(content="passed", call_id=create_result.content[0].id),
                FunctionExecutionResult(content="failed", call_id=create_result.content[1].id),
            ]
        )
    )
    create_result = await model_client.create(messages=messages)
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0


@pytest.mark.asyncio
async def test_openai() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )
    await _test_model_client_basic_completion(model_client)
    await _test_model_client_with_function_calling(model_client)


@pytest.mark.asyncio
async def test_gemini() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not found in environment variables")

    model_client = OpenAIChatCompletionClient(
        model="gemini-1.5-flash",
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "family": ModelFamily.GEMINI_1_5_FLASH,
        },
    )
    await _test_model_client_basic_completion(model_client)
    await _test_model_client_with_function_calling(model_client)


@pytest.mark.asyncio
async def test_hugging_face() -> None:
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        pytest.skip("HF_TOKEN not found in environment variables")

    model_client = OpenAIChatCompletionClient(
        model="microsoft/Phi-3.5-mini-instruct",
        api_key=api_key,
        base_url="https://api-inference.huggingface.co/v1/",
        model_info={
            "function_calling": False,
            "json_output": False,
            "vision": False,
            "family": ModelFamily.UNKNOWN,
        },
    )

    await _test_model_client_basic_completion(model_client)


@pytest.mark.asyncio
async def test_ollama() -> None:
    model = "deepseek-r1:1.5b"
    model_info: ModelInfo = {
        "function_calling": False,
        "json_output": False,
        "vision": False,
        "family": ModelFamily.R1,
    }
    # Check if the model is running locally.
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:11434/v1/models/{model}")
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        pytest.skip(f"{model} model is not running locally: {e}")
    except httpx.ConnectError as e:
        pytest.skip(f"Ollama is not running locally: {e}")

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="placeholder",
        base_url="http://localhost:11434/v1",
        model_info=model_info,
    )

    # Test basic completion with the Ollama deepseek-r1:1.5b model.
    create_result = await model_client.create(
        messages=[
            UserMessage(
                content="Taking two balls from a bag of 10 green balls and 20 red balls, "
                "what is the probability of getting a green and a red balls?",
                source="user",
            ),
        ]
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"
    assert create_result.usage is not None
    if model_info["family"] == ModelFamily.R1:
        assert create_result.thought is not None

    # Test streaming completion with the Ollama deepseek-r1:1.5b model.
    chunks: List[str | CreateResult] = []
    async for chunk in model_client.create_stream(
        messages=[
            UserMessage(
                content="Taking two balls from a bag of 10 green balls and 20 red balls, "
                "what is the probability of getting a green and a red balls?",
                source="user",
            ),
        ]
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].finish_reason == "stop"
    assert len(chunks[-1].content) > 0
    assert chunks[-1].usage is not None
    if model_info["family"] == ModelFamily.R1:
        assert chunks[-1].thought is not None


@pytest.mark.asyncio
async def test_add_name_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    sys_message = SystemMessage(content="You are a helpful AI agent, and you answer questions in a friendly way.")
    assistant_message = AssistantMessage(content="Hello, how can I help you?", source="Assistant")
    user_text_message = UserMessage(content="Hello, I am from Seattle.", source="Adam")
    user_mm_message = UserMessage(
        content=[
            "Here is a postcard from Seattle:",
            Image.from_base64(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
            ),
        ],
        source="Adam",
    )

    # Default conversion
    oai_sys = to_oai_type(sys_message)[0]
    oai_asst = to_oai_type(assistant_message)[0]
    oai_text = to_oai_type(user_text_message)[0]
    oai_mm = to_oai_type(user_mm_message)[0]

    converted_sys = to_oai_type(sys_message, prepend_name=True)[0]
    converted_asst = to_oai_type(assistant_message, prepend_name=True)[0]
    converted_text = to_oai_type(user_text_message, prepend_name=True)[0]
    converted_mm = to_oai_type(user_mm_message, prepend_name=True)[0]

    # Invariants
    assert "content" in oai_sys
    assert "content" in oai_asst
    assert "content" in oai_text
    assert "content" in oai_mm
    assert "content" in converted_sys
    assert "content" in converted_asst
    assert "content" in converted_text
    assert "content" in converted_mm
    assert oai_sys["role"] == converted_sys["role"]
    assert oai_sys["content"] == converted_sys["content"]
    assert oai_asst["role"] == converted_asst["role"]
    assert oai_asst["content"] == converted_asst["content"]
    assert oai_text["role"] == converted_text["role"]
    assert oai_mm["role"] == converted_mm["role"]
    assert isinstance(oai_mm["content"], list)
    assert isinstance(converted_mm["content"], list)
    assert len(oai_mm["content"]) == len(converted_mm["content"])
    assert "text" in converted_mm["content"][0]
    assert "text" in oai_mm["content"][0]

    # Name prepended
    assert str(converted_text["content"]) == "Adam said:\n" + str(oai_text["content"])
    assert str(converted_mm["content"][0]["text"]) == "Adam said:\n" + str(oai_mm["content"][0]["text"])


# TODO: add integration tests for Azure OpenAI using AAD token.
