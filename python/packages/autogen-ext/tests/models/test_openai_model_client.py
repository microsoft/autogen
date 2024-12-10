import asyncio
from typing import Annotated, Any, AsyncGenerator, List, Tuple
from unittest.mock import MagicMock

import pytest
from autogen_core import CancellationToken, Image
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import BaseTool, FunctionTool
from autogen_ext.models import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.models._openai._model_info import resolve_model
from autogen_ext.models._openai._openai_client import calculate_vision_tokens, convert_tools
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel, Field


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
async def test_azure_openai_chat_completion_client() -> None:
    client = AzureOpenAIChatCompletionClient(
        azure_deployment="gpt-4o-1",
        model="gpt-4o",
        api_key="api_key",
        api_version="2020-08-04",
        azure_endpoint="https://dummy.com",
        model_capabilities={"vision": True, "function_calling": True, "json_output": True},
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
    monkeypatch.setattr(
        "autogen_ext.models._openai._openai_client.calculate_vision_tokens", mockcalculate_vision_tokens
    )

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
