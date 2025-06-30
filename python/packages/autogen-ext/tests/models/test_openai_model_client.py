import asyncio
import json
import logging
import os
from typing import Annotated, Any, AsyncGenerator, Dict, List, Literal, Tuple, TypeVar
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage
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
from autogen_ext.models.openai._openai_client import (
    BaseOpenAIChatCompletionClient,
    calculate_vision_tokens,
    convert_tools,
    to_oai_type,
)
from autogen_ext.models.openai._transformation import TransformerMap, get_transformer
from autogen_ext.models.openai._transformation.registry import _find_model_family  # pyright: ignore[reportPrivateUsage]
from openai.resources.beta.chat.completions import (  # type: ignore
    AsyncChatCompletionStreamManager as BetaAsyncChatCompletionStreamManager,  # type: ignore
)

# type: ignore
from openai.resources.beta.chat.completions import (
    AsyncCompletions as BetaAsyncCompletions,
)
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)
from openai.types.chat.chat_completion_chunk import (
    Choice as ChunkChoice,
)
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion, ParsedChatCompletionMessage, ParsedChoice
from openai.types.chat.parsed_function_tool_call import ParsedFunction, ParsedFunctionToolCall
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel, Field

ResponseFormatT = TypeVar("ResponseFormatT", bound=BaseModel)


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


class MockChunkEvent(BaseModel):
    type: Literal["chunk"]
    chunk: ChatCompletionChunk


async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
    model = resolve_model(kwargs.get("model", "gpt-4.1-nano"))
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
    model = resolve_model(kwargs.get("model", "gpt-4.1-nano"))
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
    client = OpenAIChatCompletionClient(model="gpt-4.1-nano", api_key="api_key")
    assert client


@pytest.mark.asyncio
async def test_openai_chat_completion_client_with_gemini_model() -> None:
    client = OpenAIChatCompletionClient(model="gemini-1.5-flash", api_key="api_key")
    assert client


@pytest.mark.asyncio
async def test_openai_chat_completion_client_serialization() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4.1-nano", api_key="sk-password")
    assert client
    config = client.dump_component()
    assert config
    assert "sk-password" not in str(config)
    serialized_config = config.model_dump_json()
    assert serialized_config
    assert "sk-password" not in serialized_config
    client2 = OpenAIChatCompletionClient.load_component(config)
    assert client2


@pytest.mark.asyncio
async def test_openai_chat_completion_client_raise_on_unknown_model() -> None:
    with pytest.raises(ValueError, match="model_info is required"):
        _ = OpenAIChatCompletionClient(model="unknown", api_key="api_key")


@pytest.mark.asyncio
async def test_custom_model_with_capabilities() -> None:
    with pytest.raises(ValueError, match="model_info is required"):
        client = OpenAIChatCompletionClient(model="dummy_model", base_url="https://api.dummy.com/v0", api_key="api_key")

    client = OpenAIChatCompletionClient(
        model="dummy_model",
        base_url="https://api.dummy.com/v0",
        api_key="api_key",
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        },
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
        model_info={
            "vision": True,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    assert client


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    with caplog.at_level(logging.INFO):
        client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
        result = await client.create(messages=[UserMessage(content="Hello", source="user")])
        assert result.content == "Hello"
        assert "LLMCall" in caplog.text and "Hello" in caplog.text


@pytest.mark.asyncio
async def test_openai_chat_completion_client_create_stream_with_usage(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    chunks: List[str | CreateResult] = []
    # Check that include_usage works when set via create_args
    with caplog.at_level(logging.INFO):
        async for chunk in client.create_stream(
            messages=[UserMessage(content="Hello", source="user")],
            # include_usage not the default of the OPENAI API and must be explicitly set
            extra_create_args={"stream_options": {"include_usage": True}},
        ):
            chunks.append(chunk)

        assert "LLMStreamStart" in caplog.text
        assert "LLMStreamEnd" in caplog.text

        assert chunks[0] == "Hello"
        assert chunks[1] == " Another Hello"
        assert chunks[2] == " Yet Another Hello"
        assert isinstance(chunks[-1], CreateResult)
        assert isinstance(chunks[-1].content, str)
        assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
        assert chunks[-1].content in caplog.text
        assert chunks[-1].usage == RequestUsage(prompt_tokens=3, completion_tokens=3)

    chunks = []
    # Check that include_usage works when set via include_usage flag
    with caplog.at_level(logging.INFO):
        async for chunk in client.create_stream(
            messages=[UserMessage(content="Hello", source="user")],
            include_usage=True,
        ):
            chunks.append(chunk)

        assert "LLMStreamStart" in caplog.text
        assert "LLMStreamEnd" in caplog.text

        assert chunks[0] == "Hello"
        assert chunks[1] == " Another Hello"
        assert chunks[2] == " Yet Another Hello"
        assert isinstance(chunks[-1], CreateResult)
        assert isinstance(chunks[-1].content, str)
        assert chunks[-1].content == "Hello Another Hello Yet Another Hello"
        assert chunks[-1].content in caplog.text
        assert chunks[-1].usage == RequestUsage(prompt_tokens=3, completion_tokens=3)

    chunks = []
    # Check that setting both flags to different values raises an exception

    with pytest.raises(ValueError):
        async for chunk in client.create_stream(
            messages=[UserMessage(content="Hello", source="user")],
            extra_create_args={"stream_options": {"include_usage": False}},
            include_usage=True,
        ):
            chunks.append(chunk)


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


@pytest.mark.asyncio
async def test_openai_chat_completion_client_none_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that completion_tokens and prompt_tokens handle None usage correctly.

    This test addresses issue #6352 where result.usage could be None,
    causing TypeError in logging when trying to access completion_tokens.
    """

    async def _mock_create_with_none_usage(*args: Any, **kwargs: Any) -> ChatCompletion:
        await asyncio.sleep(0.1)
        # Create a ChatCompletion with None usage (which can happen in some API scenarios)
        return ChatCompletion(
            id="id",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant"))
            ],
            created=0,
            model="gpt-4o",
            object="chat.completion",
            usage=None,  # This is the scenario from the issue
        )

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create_with_none_usage)
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")

    # This should not raise a TypeError
    result = await client.create(messages=[UserMessage(content="Hello", source="user")])

    # Verify that the usage is correctly set to 0 when usage is None
    assert result.usage.prompt_tokens == 0
    assert result.usage.completion_tokens == 0


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
        FunctionExecutionResultMessage(
            content=[FunctionExecutionResult(content="Hello", call_id="1", is_error=False, name="tool1")]
        ),
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
async def test_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4.1-nano-2025-04-14"

    called_args = {}

    async def _mock_create(*args: Any, **kwargs: Any) -> ChatCompletion:
        # Capture the arguments passed to the function
        called_args["kwargs"] = kwargs
        return ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=json.dumps({"thoughts": "happy", "response": "happy"}),
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        )

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    model_client = OpenAIChatCompletionClient(model=model, api_key="")

    # Test that the openai client was called with the correct response format.
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=True
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    assert called_args["kwargs"]["response_format"] == {"type": "json_object"}

    # Make sure that the response format is set to json_object when json_output is True, regardless of the extra_create_args.
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        json_output=True,
        extra_create_args={"response_format": "json_object"},
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    assert called_args["kwargs"]["response_format"] == {"type": "json_object"}

    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        json_output=True,
        extra_create_args={"response_format": "text"},
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    # Check that the openai client was called with the correct response format.
    assert called_args["kwargs"]["response_format"] == {"type": "json_object"}

    # Make sure when json_output is set to False, the response format is always set to text.
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        json_output=False,
        extra_create_args={"response_format": "text"},
    )
    assert called_args["kwargs"]["response_format"] == {"type": "text"}

    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        json_output=False,
        extra_create_args={"response_format": "json_object"},
    )
    assert called_args["kwargs"]["response_format"] == {"type": "text"}

    # Make sure when response_format is set it is used when json_output is not set.
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        extra_create_args={"response_format": {"type": "json_object"}},
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    assert called_args["kwargs"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_structured_output_using_response_format(monkeypatch: pytest.MonkeyPatch) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    model = "gpt-4.1-nano-2025-04-14"

    called_args = {}

    async def _mock_create(*args: Any, **kwargs: Any) -> ChatCompletion:
        # Capture the arguments passed to the function
        called_args["kwargs"] = kwargs
        return ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=json.dumps({"thoughts": "happy", "response": "happy"}),
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        )

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)

    # Scenario 1: response_format is set to constructor.
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "test",
                "description": "test",
                "schema": AgentResponse.model_json_schema(),
            },
        },
    )

    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    assert called_args["kwargs"]["response_format"]["type"] == "json_schema"

    # Test the response format can be serailized and deserialized.
    config = model_client.dump_component()
    assert config
    loaded_client = OpenAIChatCompletionClient.load_component(config)

    create_result = await loaded_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    assert called_args["kwargs"]["response_format"]["type"] == "json_schema"

    # Scenario 2: response_format is set to a extra_create_args.
    model_client = OpenAIChatCompletionClient(model=model, api_key="")
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        extra_create_args={
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "test",
                    "description": "test",
                    "schema": AgentResponse.model_json_schema(),
                },
            }
        },
    )
    assert isinstance(create_result.content, str)
    response = json.loads(create_result.content)
    assert response["thoughts"] == "happy"
    assert response["response"] == "happy"
    assert called_args["kwargs"]["response_format"]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    model = "gpt-4.1-nano-2025-04-14"

    async def _mock_parse(*args: Any, **kwargs: Any) -> ParsedChatCompletion[AgentResponse]:
        return ParsedChatCompletion(
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
        )

    monkeypatch.setattr(BetaAsyncCompletions, "parse", _mock_parse)

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
    )

    # Test that the openai client was called with the correct response format.
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=AgentResponse
    )
    assert isinstance(create_result.content, str)
    response = AgentResponse.model_validate(json.loads(create_result.content))
    assert (
        response.thoughts
        == "The user explicitly states that they are happy without any indication of sadness or neutrality."
    )
    assert response.response == "happy"

    # Test that a warning will be raise if response_format is set to a dict.
    with pytest.warns(
        UserWarning,
        match="response_format is found in extra_create_args while json_output is set to a Pydantic model class.",
    ):
        create_result = await model_client.create(
            messages=[UserMessage(content="I am happy.", source="user")],
            json_output=AgentResponse,
            extra_create_args={"response_format": {"type": "json_object"}},
        )

    # Test that a warning will be raised if response_format is set to a pydantic model.
    with pytest.warns(
        DeprecationWarning,
        match="Using response_format to specify the BaseModel for structured output type will be deprecated.",
    ):
        create_result = await model_client.create(
            messages=[UserMessage(content="I am happy.", source="user")],
            extra_create_args={"response_format": AgentResponse},
        )

    # Test that a ValueError will be raised if response_format and json_output are set to a pydantic model.
    with pytest.raises(
        ValueError, match="response_format and json_output cannot be set to a Pydantic model class at the same time."
    ):
        create_result = await model_client.create(
            messages=[UserMessage(content="I am happy.", source="user")],
            json_output=AgentResponse,
            extra_create_args={"response_format": AgentResponse},
        )


@pytest.mark.asyncio
async def test_structured_output_with_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    model = "gpt-4.1-nano-2025-04-14"

    async def _mock_parse(*args: Any, **kwargs: Any) -> ParsedChatCompletion[AgentResponse]:
        return ParsedChatCompletion(
            id="id1",
            choices=[
                ParsedChoice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ParsedChatCompletionMessage(
                        content=json.dumps(
                            {
                                "thoughts": "The user explicitly states that they are happy without any indication of sadness or neutrality.",
                                "response": "happy",
                            }
                        ),
                        role="assistant",
                        tool_calls=[
                            ParsedFunctionToolCall(
                                id="1",
                                type="function",
                                function=ParsedFunction(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "happy"}),
                                ),
                            )
                        ],
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        )

    monkeypatch.setattr(BetaAsyncCompletions, "parse", _mock_parse)

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
    )

    # Test that the openai client was called with the correct response format.
    create_result = await model_client.create(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=AgentResponse
    )
    assert isinstance(create_result.content, list)
    assert len(create_result.content) == 1
    assert create_result.content[0] == FunctionCall(
        id="1", name="_pass_function", arguments=json.dumps({"input": "happy"})
    )
    assert isinstance(create_result.thought, str)
    response = AgentResponse.model_validate(json.loads(create_result.thought))
    assert (
        response.thoughts
        == "The user explicitly states that they are happy without any indication of sadness or neutrality."
    )
    assert response.response == "happy"


@pytest.mark.asyncio
async def test_structured_output_with_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    raw_content = json.dumps(
        {
            "thoughts": "The user explicitly states that they are happy without any indication of sadness or neutrality.",
            "response": "happy",
        }
    )
    chunked_content = [raw_content[i : i + 5] for i in range(0, len(raw_content), 5)]
    assert "".join(chunked_content) == raw_content

    model = "gpt-4.1-nano-2025-04-14"
    mock_chunk_events = [
        MockChunkEvent(
            type="chunk",
            chunk=ChatCompletionChunk(
                id="id",
                choices=[
                    ChunkChoice(
                        finish_reason=None,
                        index=0,
                        delta=ChoiceDelta(
                            content=mock_chunk_content,
                            role="assistant",
                        ),
                    )
                ],
                created=0,
                model=model,
                object="chat.completion.chunk",
                usage=None,
            ),
        )
        for mock_chunk_content in chunked_content
    ]

    async def _mock_create_stream(*args: Any) -> AsyncGenerator[MockChunkEvent, None]:
        async def _stream() -> AsyncGenerator[MockChunkEvent, None]:
            for mock_chunk_event in mock_chunk_events:
                await asyncio.sleep(0.1)
                yield mock_chunk_event

        return _stream()

    # Mock the context manager __aenter__ method which returns the stream.
    monkeypatch.setattr(BetaAsyncChatCompletionStreamManager, "__aenter__", _mock_create_stream)

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
    )

    # Test that the openai client was called with the correct response format.
    chunks: List[str | CreateResult] = []
    async for chunk in model_client.create_stream(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=AgentResponse
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert isinstance(chunks[-1].content, str)
    response = AgentResponse.model_validate(json.loads(chunks[-1].content))
    assert (
        response.thoughts
        == "The user explicitly states that they are happy without any indication of sadness or neutrality."
    )
    assert response.response == "happy"


@pytest.mark.asyncio
async def test_structured_output_with_streaming_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    raw_content = json.dumps(
        {
            "thoughts": "The user explicitly states that they are happy without any indication of sadness or neutrality.",
            "response": "happy",
        }
    )
    chunked_content = [raw_content[i : i + 5] for i in range(0, len(raw_content), 5)]
    assert "".join(chunked_content) == raw_content

    model = "gpt-4.1-nano-2025-04-14"

    # generate the list of mock chunk content
    mock_chunk_events = [
        MockChunkEvent(
            type="chunk",
            chunk=ChatCompletionChunk(
                id="id",
                choices=[
                    ChunkChoice(
                        finish_reason=None,
                        index=0,
                        delta=ChoiceDelta(
                            content=mock_chunk_content,
                            role="assistant",
                        ),
                    )
                ],
                created=0,
                model=model,
                object="chat.completion.chunk",
                usage=None,
            ),
        )
        for mock_chunk_content in chunked_content
    ]

    # add the tool call chunk.
    mock_chunk_events += [
        MockChunkEvent(
            type="chunk",
            chunk=ChatCompletionChunk(
                id="id",
                choices=[
                    ChunkChoice(
                        finish_reason="tool_calls",
                        index=0,
                        delta=ChoiceDelta(
                            content=None,
                            role="assistant",
                            tool_calls=[
                                ChoiceDeltaToolCall(
                                    id="1",
                                    index=0,
                                    type="function",
                                    function=ChoiceDeltaToolCallFunction(
                                        name="_pass_function",
                                        arguments=json.dumps({"input": "happy"}),
                                    ),
                                )
                            ],
                        ),
                    )
                ],
                created=0,
                model=model,
                object="chat.completion.chunk",
                usage=None,
            ),
        )
    ]

    async def _mock_create_stream(*args: Any) -> AsyncGenerator[MockChunkEvent, None]:
        async def _stream() -> AsyncGenerator[MockChunkEvent, None]:
            for mock_chunk_event in mock_chunk_events:
                await asyncio.sleep(0.1)
                yield mock_chunk_event

        return _stream()

    # Mock the context manager __aenter__ method which returns the stream.
    monkeypatch.setattr(BetaAsyncChatCompletionStreamManager, "__aenter__", _mock_create_stream)

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
    )

    # Test that the openai client was called with the correct response format.
    chunks: List[str | CreateResult] = []
    async for chunk in model_client.create_stream(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=AgentResponse
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert isinstance(chunks[-1].content, list)
    assert len(chunks[-1].content) == 1
    assert chunks[-1].content[0] == FunctionCall(
        id="1", name="_pass_function", arguments=json.dumps({"input": "happy"})
    )
    assert isinstance(chunks[-1].thought, str)
    response = AgentResponse.model_validate(json.loads(chunks[-1].thought))
    assert (
        response.thoughts
        == "The user explicitly states that they are happy without any indication of sadness or neutrality."
    )
    assert response.response == "happy"


@pytest.mark.asyncio
async def test_r1_reasoning_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of reasoning_content in R1 model. Testing create without streaming."""

    async def _mock_create(*args: Any, **kwargs: Any) -> ChatCompletion:
        return ChatCompletion(
            id="test_id",
            model="r1",
            object="chat.completion",
            created=1234567890,
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="This is the main content",
                        # The reasoning content is included in model_extra for hosted R1 models.
                        reasoning_content="This is the reasoning content",  # type: ignore
                    ),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=10,
                completion_tokens=10,
                total_tokens=20,
            ),
        )

    # Patch the client creation

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)

    # Create the client
    model_client = OpenAIChatCompletionClient(
        model="r1",
        api_key="",
        model_info={
            "family": ModelFamily.R1,
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
        },
    )

    # Test the create method
    result = await model_client.create([UserMessage(content="Test message", source="user")])

    # Verify that the content and thought are as expected
    assert result.content == "This is the main content"
    assert result.thought == "This is the reasoning content"


@pytest.mark.asyncio
async def test_r1_reasoning_content_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that reasoning_content in model_extra is correctly extracted and streamed."""

    async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
        contentChunks = [None, None, "This is the main content"]
        reasoningChunks = ["This is the reasoning content 1", "This is the reasoning content 2", None]
        for i in range(len(contentChunks)):
            await asyncio.sleep(0.1)
            yield ChatCompletionChunk(
                id="id",
                choices=[
                    ChunkChoice(
                        finish_reason="stop" if i == len(contentChunks) - 1 else None,
                        index=0,
                        delta=ChoiceDelta(
                            content=contentChunks[i],
                            # The reasoning content is included in model_extra for hosted R1 models.
                            reasoning_content=reasoningChunks[i],  # type: ignore
                            role="assistant",
                        ),
                    ),
                ],
                created=0,
                model="r1",
                object="chat.completion.chunk",
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    async def _mock_create(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
        return _mock_create_stream(*args, **kwargs)

    # Patch the client creation
    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    # Create the client
    model_client = OpenAIChatCompletionClient(
        model="r1",
        api_key="",
        model_info={
            "family": ModelFamily.R1,
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
        },
    )
    # Test the create_stream method
    chunks: List[str | CreateResult] = []
    async for chunk in model_client.create_stream(messages=[UserMessage(content="Hello", source="user")]):
        chunks.append(chunk)

    # Verify that the chunks first stream the reasoning content and then the main content
    # Then verify that the final result has the correct content and thought
    assert len(chunks) == 5
    assert chunks[0] == "<think>This is the reasoning content 1"
    assert chunks[1] == "This is the reasoning content 2"
    assert chunks[2] == "</think>"
    assert chunks[3] == "This is the main content"
    assert isinstance(chunks[4], CreateResult)
    assert chunks[4].content == "This is the main content"
    assert chunks[4].thought == "This is the reasoning content 1This is the reasoning content 2"


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
        model_info={
            "family": ModelFamily.R1,
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
        },
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
        model_info={
            "family": ModelFamily.R1,
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
        },
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
    model = "gpt-4.1-nano-2025-04-14"
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
        # Thought field is populated when content is not None.
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

    class _MockChatCompletion:
        def __init__(self, completions: List[ChatCompletion]):
            self.completions = list(completions)
            self.calls: List[Dict[str, Any]] = []

        async def mock_create(
            self, *args: Any, **kwargs: Any
        ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
            if kwargs.get("stream", False):
                raise NotImplementedError("Streaming not supported in this test.")
            self.calls.append(kwargs)
            return self.completions.pop(0)

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

    # Thought field is populated when content is not None.
    create_result = await model_client.create(messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool])
    assert create_result.content == [FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function")]
    assert create_result.finish_reason == "function_calls"
    assert create_result.thought == "I should make a tool call."

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


@pytest.mark.asyncio
async def test_tool_calling_with_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_create_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatCompletionChunk, None]:
        model = resolve_model(kwargs.get("model", "gpt-4o"))
        mock_chunks_content = ["Hello", " Another Hello", " Yet Another Hello"]
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
            # generate the function call chunk
            MockChunkDefinition(
                chunk_choice=ChunkChoice(
                    finish_reason="tool_calls",
                    index=0,
                    delta=ChoiceDelta(
                        content=None,
                        role="assistant",
                        tool_calls=[
                            ChoiceDeltaToolCall(
                                index=0,
                                id="1",
                                type="function",
                                function=ChoiceDeltaToolCallFunction(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            )
                        ],
                    ),
                ),
                usage=None,
            )
        ]
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
        if not stream:
            raise ValueError("Stream is not False")
        else:
            return _mock_create_stream(*args, **kwargs)

    monkeypatch.setattr(AsyncCompletions, "create", _mock_create)

    model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key="")
    pass_tool = FunctionTool(_pass_function, description="pass tool.")
    stream = model_client.create_stream(messages=[UserMessage(content="Hello", source="user")], tools=[pass_tool])
    chunks: List[str | CreateResult] = []
    async for chunk in stream:
        chunks.append(chunk)
    assert chunks[0] == "Hello"
    assert chunks[1] == " Another Hello"
    assert chunks[2] == " Yet Another Hello"
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].content == [FunctionCall(id="1", arguments=r'{"input": "task"}', name="_pass_function")]
    assert chunks[-1].finish_reason == "function_calls"
    assert chunks[-1].thought == "Hello Another Hello Yet Another Hello"


@pytest.fixture()
def openai_client(request: pytest.FixtureRequest) -> OpenAIChatCompletionClient:
    model = request.node.callspec.params["model"]  # type: ignore
    assert isinstance(model, str)
    if model.startswith("gemini"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not found in environment variables")
    elif model.startswith("claude"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not found in environment variables")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not found in environment variables")
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
    )
    return model_client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    ["gpt-4.1-nano", "gemini-1.5-flash", "claude-3-5-haiku-20241022"],
)
async def test_model_client_basic_completion(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    # Test basic completion
    create_result = await openai_client.create(
        messages=[
            SystemMessage(content="You are a helpful assistant."),
            UserMessage(content="Explain to me how AI works.", source="user"),
        ]
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    ["gpt-4.1-nano", "gemini-1.5-flash", "claude-3-5-haiku-20241022"],
)
async def test_model_client_with_function_calling(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    # Test tool calling
    pass_tool = FunctionTool(_pass_function, name="pass_tool", description="pass session.")
    fail_tool = FunctionTool(_fail_function, name="fail_tool", description="fail session.")
    messages: List[LLMMessage] = [
        UserMessage(content="Call the pass tool with input 'task' and talk result", source="user")
    ]
    create_result = await openai_client.create(messages=messages, tools=[pass_tool, fail_tool])
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
            content=[
                FunctionExecutionResult(
                    content="passed",
                    call_id=create_result.content[0].id,
                    is_error=False,
                    name=create_result.content[0].name,
                )
            ]
        )
    )
    create_result = await openai_client.create(messages=messages)
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0

    # Test parallel tool calling
    messages = [
        UserMessage(
            content="Call both the pass tool with input 'task' and the fail tool also with input 'task' and talk result",
            source="user",
        )
    ]
    create_result = await openai_client.create(messages=messages, tools=[pass_tool, fail_tool])
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
                FunctionExecutionResult(
                    content="passed", call_id=create_result.content[0].id, is_error=False, name="pass_tool"
                ),
                FunctionExecutionResult(
                    content="failed", call_id=create_result.content[1].id, is_error=True, name="fail_tool"
                ),
            ]
        )
    )
    create_result = await openai_client.create(messages=messages)
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    ["gpt-4.1-nano", "gemini-1.5-flash"],
)
async def test_openai_structured_output_using_response_format(
    model: str, openai_client: OpenAIChatCompletionClient
) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    create_result = await openai_client.create(
        messages=[UserMessage(content="I am happy.", source="user")],
        extra_create_args={
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "AgentResponse",
                    "description": "Agent response",
                    "schema": AgentResponse.model_json_schema(),
                },
            }
        },
    )

    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    response = AgentResponse.model_validate(json.loads(create_result.content))
    assert response.thoughts
    assert response.response in ["happy", "sad", "neutral"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    ["gpt-4.1-nano", "gemini-1.5-flash"],
)
async def test_openai_structured_output(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    # Test that the openai client was called with the correct response format.
    create_result = await openai_client.create(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=AgentResponse
    )
    assert isinstance(create_result.content, str)
    response = AgentResponse.model_validate(json.loads(create_result.content))
    assert response.thoughts
    assert response.response in ["happy", "sad", "neutral"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    ["gpt-4.1-nano", "gemini-1.5-flash"],
)
async def test_openai_structured_output_with_streaming(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    # Test that the openai client was called with the correct response format.
    stream = openai_client.create_stream(
        messages=[UserMessage(content="I am happy.", source="user")], json_output=AgentResponse
    )
    chunks: List[str | CreateResult] = []
    async for chunk in stream:
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert isinstance(chunks[-1].content, str)
    response = AgentResponse.model_validate(json.loads(chunks[-1].content))
    assert response.thoughts
    assert response.response in ["happy", "sad", "neutral"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4.1-nano",
        # "gemini-1.5-flash", # Gemini models do not support structured output with tool calls from model client.
    ],
)
async def test_openai_structured_output_with_tool_calls(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    def sentiment_analysis(text: str) -> str:
        """Given a text, return the sentiment."""
        return "happy" if "happy" in text else "sad" if "sad" in text else "neutral"

    tool = FunctionTool(sentiment_analysis, description="Sentiment Analysis", strict=True)

    extra_create_args = {"tool_choice": "required"}

    response1 = await openai_client.create(
        messages=[
            SystemMessage(content="Analyze input text sentiment using the tool provided."),
            UserMessage(content="I am happy.", source="user"),
        ],
        tools=[tool],
        extra_create_args=extra_create_args,
        json_output=AgentResponse,
    )
    assert isinstance(response1.content, list)
    assert len(response1.content) == 1
    assert isinstance(response1.content[0], FunctionCall)
    assert response1.content[0].name == "sentiment_analysis"
    assert json.loads(response1.content[0].arguments) == {"text": "I am happy."}
    assert response1.finish_reason == "function_calls"

    response2 = await openai_client.create(
        messages=[
            SystemMessage(content="Analyze input text sentiment using the tool provided."),
            UserMessage(content="I am happy.", source="user"),
            AssistantMessage(content=response1.content, source="assistant"),
            FunctionExecutionResultMessage(
                content=[
                    FunctionExecutionResult(
                        content="happy", call_id=response1.content[0].id, is_error=False, name=tool.name
                    )
                ]
            ),
        ],
        json_output=AgentResponse,
    )
    assert isinstance(response2.content, str)
    parsed_response = AgentResponse.model_validate(json.loads(response2.content))
    assert parsed_response.thoughts
    assert parsed_response.response in ["happy", "sad", "neutral"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4.1-nano",
        # "gemini-1.5-flash", # Gemini models do not support structured output with tool calls from model client.
    ],
)
async def test_openai_structured_output_with_streaming_tool_calls(
    model: str, openai_client: OpenAIChatCompletionClient
) -> None:
    class AgentResponse(BaseModel):
        thoughts: str
        response: Literal["happy", "sad", "neutral"]

    def sentiment_analysis(text: str) -> str:
        """Given a text, return the sentiment."""
        return "happy" if "happy" in text else "sad" if "sad" in text else "neutral"

    tool = FunctionTool(sentiment_analysis, description="Sentiment Analysis", strict=True)

    extra_create_args = {"tool_choice": "required"}

    chunks1: List[str | CreateResult] = []
    stream1 = openai_client.create_stream(
        messages=[
            SystemMessage(content="Analyze input text sentiment using the tool provided."),
            UserMessage(content="I am happy.", source="user"),
        ],
        tools=[tool],
        extra_create_args=extra_create_args,
        json_output=AgentResponse,
    )
    async for chunk in stream1:
        chunks1.append(chunk)
    assert len(chunks1) > 0
    create_result1 = chunks1[-1]
    assert isinstance(create_result1, CreateResult)
    assert isinstance(create_result1.content, list)
    assert len(create_result1.content) == 1
    assert isinstance(create_result1.content[0], FunctionCall)
    assert create_result1.content[0].name == "sentiment_analysis"
    assert json.loads(create_result1.content[0].arguments) == {"text": "I am happy."}
    assert create_result1.finish_reason == "function_calls"

    stream2 = openai_client.create_stream(
        messages=[
            SystemMessage(content="Analyze input text sentiment using the tool provided."),
            UserMessage(content="I am happy.", source="user"),
            AssistantMessage(content=create_result1.content, source="assistant"),
            FunctionExecutionResultMessage(
                content=[
                    FunctionExecutionResult(
                        content="happy", call_id=create_result1.content[0].id, is_error=False, name=tool.name
                    )
                ]
            ),
        ],
        json_output=AgentResponse,
    )
    chunks2: List[str | CreateResult] = []
    async for chunk in stream2:
        chunks2.append(chunk)
    assert len(chunks2) > 0
    create_result2 = chunks2[-1]
    assert isinstance(create_result2, CreateResult)
    assert isinstance(create_result2.content, str)
    parsed_response = AgentResponse.model_validate(json.loads(create_result2.content))
    assert parsed_response.thoughts
    assert parsed_response.response in ["happy", "sad", "neutral"]


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
            "structured_output": False,
        },
    )

    # Test basic completion
    create_result = await model_client.create(
        messages=[
            SystemMessage(content="You are a helpful assistant."),
            UserMessage(content="Explain to me how AI works.", source="user"),
        ]
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0


@pytest.mark.asyncio
async def test_ollama() -> None:
    model = "deepseek-r1:1.5b"
    model_info: ModelInfo = {
        "function_calling": False,
        "json_output": False,
        "vision": False,
        "family": ModelFamily.R1,
        "structured_output": False,
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4.1-nano",
        "gemini-1.5-flash",
        "claude-3-5-haiku-20241022",
    ],
)
async def test_muliple_system_message(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    """Test multiple system messages in a single request."""

    # Test multiple system messages
    messages: List[LLMMessage] = [
        SystemMessage(content="When you say anything Start with 'FOO'"),
        SystemMessage(content="When you say anything End with 'BAR'"),
        UserMessage(content="Just say '.'", source="user"),
    ]

    result = await openai_client.create(messages=messages)
    result_content = result.content
    assert isinstance(result_content, str)
    result_content = result_content.strip()
    assert result_content[:3] == "FOO"
    assert result_content[-3:] == "BAR"


@pytest.mark.asyncio
async def test_system_message_merge_with_continuous_system_messages_models() -> None:
    """Tests that system messages are merged correctly for Gemini models."""
    # Create a mock client
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gemini-1.5-flash"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": False,
        },
    )

    # Create two system messages
    messages: List[LLMMessage] = [
        SystemMessage(content="I am system message 1"),
        SystemMessage(content="I am system message 2"),
        UserMessage(content="Hello", source="user"),
    ]

    # Process the messages
    # pylint: disable=protected-access
    # The method is protected, but we need to test it
    create_params = client._process_create_args(  # pyright: ignore[reportPrivateUsage]
        messages=messages,
        tools=[],
        json_output=None,
        extra_create_args={},
        tool_choice="none",
    )

    # Extract the actual messages from the result
    oai_messages = create_params.messages

    # Check that there is only one system message and it contains the merged content
    system_messages = [msg for msg in oai_messages if msg["role"] == "system"]
    assert len(system_messages) == 1
    assert system_messages[0]["content"] == "I am system message 1\nI am system message 2"

    # Check that the user message is preserved
    user_messages = [msg for msg in oai_messages if msg["role"] == "user"]
    assert len(user_messages) == 1
    assert user_messages[0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_system_message_merge_with_non_continuous_messages() -> None:
    """Tests that an error is raised when non-continuous system messages are provided."""
    # Create a mock client
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gemini-1.5-flash"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": False,
        },
    )

    # Create non-continuous system messages
    messages: List[LLMMessage] = [
        SystemMessage(content="I am system message 1"),
        UserMessage(content="Hello", source="user"),
        SystemMessage(content="I am system message 2"),
    ]

    # Process should raise ValueError
    with pytest.raises(ValueError, match="Multiple and Not continuous system messages are not supported"):
        # pylint: disable=protected-access
        # The method is protected, but we need to test it
        client._process_create_args(  # pyright: ignore[reportPrivateUsage]
            messages=messages,
            tools=[],
            json_output=None,
            extra_create_args={},
            tool_choice="none",
        )


@pytest.mark.asyncio
async def test_system_message_not_merged_for_multiple_system_messages_true() -> None:
    """Tests that system messages aren't modified for non-Gemini models."""
    # Create a mock client
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gpt-4.1-nano"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": True,
        },
    )

    # Create two system messages
    messages: List[LLMMessage] = [
        SystemMessage(content="I am system message 1"),
        SystemMessage(content="I am system message 2"),
        UserMessage(content="Hello", source="user"),
    ]

    # Process the messages
    # pylint: disable=protected-access
    # The method is protected, but we need to test it
    create_params = client._process_create_args(  # pyright: ignore[reportPrivateUsage]
        messages=messages,
        tools=[],
        json_output=None,
        extra_create_args={},
        tool_choice="none",
    )

    # Extract the actual messages from the result
    oai_messages = create_params.messages

    # Check that there are two system messages preserved
    system_messages = [msg for msg in oai_messages if msg["role"] == "system"]
    assert len(system_messages) == 2
    assert system_messages[0]["content"] == "I am system message 1"
    assert system_messages[1]["content"] == "I am system message 2"


@pytest.mark.asyncio
async def test_no_system_messages_for_gemini_model() -> None:
    """Tests behavior when no system messages are provided to a Gemini model."""
    # Create a mock client
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gemini-1.5-flash"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )

    # Create messages with no system message
    messages: List[LLMMessage] = [
        UserMessage(content="Hello", source="user"),
        AssistantMessage(content="Hi there", source="assistant"),
    ]

    # Process the messages
    # pylint: disable=protected-access
    # The method is protected, but we need to test it
    create_params = client._process_create_args(  # pyright: ignore[reportPrivateUsage]
        messages=messages,
        tools=[],
        json_output=None,
        extra_create_args={},
        tool_choice="none",
    )

    # Extract the actual messages from the result
    oai_messages = create_params.messages

    # Check that there are no system messages
    system_messages = [msg for msg in oai_messages if msg["role"] == "system"]
    assert len(system_messages) == 0

    # Check that other messages are preserved
    user_messages = [msg for msg in oai_messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in oai_messages if msg["role"] == "assistant"]
    assert len(user_messages) == 1
    assert len(assistant_messages) == 1


@pytest.mark.asyncio
async def test_single_system_message_for_gemini_model() -> None:
    """Tests that a single system message is preserved for Gemini models."""
    # Create a mock client
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gemini-1.5-flash"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )

    # Create messages with a single system message
    messages: List[LLMMessage] = [
        SystemMessage(content="I am the only system message"),
        UserMessage(content="Hello", source="user"),
    ]

    # Process the messages
    # pylint: disable=protected-access
    # The method is protected, but we need to test it
    create_params = client._process_create_args(  # pyright: ignore[reportPrivateUsage]
        messages=messages,
        tools=[],
        json_output=None,
        extra_create_args={},
        tool_choice="auto",
    )

    # Extract the actual messages from the result
    oai_messages = create_params.messages

    # Check that there is exactly one system message with the correct content
    system_messages = [msg for msg in oai_messages if msg["role"] == "system"]
    assert len(system_messages) == 1
    assert system_messages[0]["content"] == "I am the only system message"


def noop(input: str) -> str:
    return "done"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gemini-1.5-flash"])
async def test_empty_assistant_content_with_gemini(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    # Test tool calling
    tool = FunctionTool(noop, name="noop", description="No-op tool")
    messages: List[LLMMessage] = [UserMessage(content="Call noop", source="user")]
    result = await openai_client.create(messages=messages, tools=[tool])
    assert isinstance(result.content, list)
    tool_call = result.content[0]
    assert isinstance(tool_call, FunctionCall)

    # reply with empty string as thought (== content)
    messages.append(AssistantMessage(content=result.content, thought="", source="assistant"))
    messages.append(
        FunctionExecutionResultMessage(
            content=[
                FunctionExecutionResult(
                    content="done",
                    call_id=tool_call.id,
                    is_error=False,
                    name=tool_call.name,
                )
            ]
        )
    )

    # This will crash if _set_empty_to_whitespace is not applied to "thought"
    result = await openai_client.create(messages=messages)
    assert isinstance(result.content, str)
    assert result.content.strip() != "" or result.content == " "


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4.1-nano",
        "gemini-1.5-flash",
        "claude-3-5-haiku-20241022",
    ],
)
async def test_empty_assistant_content_string_with_some_model(
    model: str, openai_client: OpenAIChatCompletionClient
) -> None:
    # message: assistant is response empty content
    messages: list[LLMMessage] = [
        UserMessage(content="Say something", source="user"),
        AssistantMessage(content="test", source="assistant"),
        UserMessage(content="", source="user"),
    ]

    # This will crash if _set_empty_to_whitespace is not applied to "content"
    result = await openai_client.create(messages=messages)
    assert isinstance(result.content, str)


def test_openai_model_registry_find_well() -> None:
    model = "gpt-4o"
    client1 = OpenAIChatCompletionClient(model=model, api_key="test")
    client2 = OpenAIChatCompletionClient(
        model=model,
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
            "family": ModelFamily.UNKNOWN,
        },
        api_key="test",
    )

    def get_regitered_transformer(client: OpenAIChatCompletionClient) -> TransformerMap:
        model_name = client._create_args["model"]  # pyright: ignore[reportPrivateUsage]
        model_family = client.model_info["family"]
        return get_transformer("openai", model_name, model_family)

    assert get_regitered_transformer(client1) == get_regitered_transformer(client2)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4.1-nano",
    ],
)
async def test_openai_model_unknown_message_type(model: str, openai_client: OpenAIChatCompletionClient) -> None:
    class WrongMessage:
        content = "foo"
        source = "bar"

    messages: List[WrongMessage] = [WrongMessage()]
    with pytest.raises(ValueError, match="Unknown message type"):
        await openai_client.create(messages=messages)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "claude-3-5-haiku-20241022",
    ],
)
async def test_claude_trailing_whitespace_at_last_assistant_content(
    model: str, openai_client: OpenAIChatCompletionClient
) -> None:
    messages: list[LLMMessage] = [
        UserMessage(content="foo", source="user"),
        UserMessage(content="bar", source="user"),
        AssistantMessage(content="foobar ", source="assistant"),
    ]

    result = await openai_client.create(messages=messages)
    assert isinstance(result.content, str)


def test_rstrip_railing_whitespace_at_last_assistant_content() -> None:
    messages: list[LLMMessage] = [
        UserMessage(content="foo", source="user"),
        UserMessage(content="bar", source="user"),
        AssistantMessage(content="foobar ", source="assistant"),
    ]

    # This will crash if _rstrip_railing_whitespace_at_last_assistant_content is not applied to "content"
    dummy_client = OpenAIChatCompletionClient(model="claude-3-5-haiku-20241022", api_key="dummy-key")
    result = dummy_client._rstrip_last_assistant_message(messages)  # pyright: ignore[reportPrivateUsage]

    assert isinstance(result[-1].content, str)
    assert result[-1].content == "foobar"


def test_find_model_family() -> None:
    assert _find_model_family("openai", "gpt-4") == ModelFamily.GPT_4
    assert _find_model_family("openai", "gpt-4-latest") == ModelFamily.GPT_4
    assert _find_model_family("openai", "gpt-4o") == ModelFamily.GPT_4O
    assert _find_model_family("openai", "gemini-2.0-flash") == ModelFamily.GEMINI_2_0_FLASH
    assert _find_model_family("openai", "claude-3-5-haiku-20241022") == ModelFamily.CLAUDE_3_5_HAIKU
    assert _find_model_family("openai", "error") == ModelFamily.UNKNOWN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4.1-nano",
        "gemini-1.5-flash",
        "claude-3-5-haiku-20241022",
    ],
)
async def test_multimodal_message_test(
    model: str, openai_client: OpenAIChatCompletionClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test that the multimodal message is converted to the correct format
    img = Image.from_base64(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    )
    multi_modal_message = MultiModalMessage(content=["Can you describe the content of this image?", img], source="user")

    ocr_agent = AssistantAgent(
        name="ocr_agent", model_client=openai_client, system_message="""You are a helpful agent."""
    )
    _ = await ocr_agent.run(task=multi_modal_message)


@pytest.mark.asyncio
async def test_mistral_remove_name() -> None:
    # Test that the name pramaeter is removed from the message
    # when the model is Mistral
    message = UserMessage(content="foo", source="user")
    params = to_oai_type(message, prepend_name=False, model="mistral-7b", model_family=ModelFamily.MISTRAL)
    assert ("name" in params[0]) is False

    # when the model is gpt-4o, the name parameter is not removed
    params = to_oai_type(message, prepend_name=False, model="gpt-4o", model_family=ModelFamily.GPT_4O)
    assert ("name" in params[0]) is True


@pytest.mark.asyncio
async def test_mock_tool_choice_specific_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool_choice parameter with a specific tool using mocks."""

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    model = "gpt-4o"

    # Mock successful completion with specific tool call
    chat_completion = ChatCompletion(
        id="id1",
        choices=[
            Choice(
                finish_reason="tool_calls",
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="1",
                            type="function",
                            function=Function(
                                name="_pass_function",
                                arguments=json.dumps({"input": "hello"}),
                            ),
                        )
                    ],
                ),
            )
        ],
        created=1234567890,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
    )

    client = OpenAIChatCompletionClient(model=model, api_key="test")

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")

    # Create mock for the chat completions create method
    mock_create = AsyncMock(return_value=chat_completion)

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)  # type: ignore[reportPrivateUsage]

        _ = await client.create(
            messages=[UserMessage(content="Process 'hello'", source="user")],
            tools=[pass_tool, add_tool],
            tool_choice=pass_tool,  # Force use of specific tool
        )

    # Verify the correct API call was made
    mock_create.assert_called_once()
    call_args = mock_create.call_args

    # Check that tool_choice was set correctly
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == {"type": "function", "function": {"name": "_pass_function"}}


@pytest.mark.asyncio
async def test_mock_tool_choice_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool_choice parameter with 'auto' setting using mocks."""

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    model = "gpt-4o"

    # Mock successful completion
    chat_completion = ChatCompletion(
        id="id1",
        choices=[
            Choice(
                finish_reason="tool_calls",
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="1",
                            type="function",
                            function=Function(
                                name="_add_numbers",
                                arguments=json.dumps({"a": 1, "b": 2}),
                            ),
                        )
                    ],
                ),
            )
        ],
        created=1234567890,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
    )

    client = OpenAIChatCompletionClient(model=model, api_key="test")

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")

    # Create mock for the chat completions create method
    mock_create = AsyncMock(return_value=chat_completion)

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)  # type: ignore[reportPrivateUsage]

        await client.create(
            messages=[UserMessage(content="Add 1 and 2", source="user")],
            tools=[pass_tool, add_tool],
            tool_choice="auto",  # Let model choose
        )

    # Verify the correct API call was made
    mock_create.assert_called_once()
    call_args = mock_create.call_args

    # Check that tool_choice was set correctly
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == "auto"


@pytest.mark.asyncio
async def test_mock_tool_choice_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool_choice parameter with None setting using mocks."""

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    model = "gpt-4o"

    # Mock successful completion
    chat_completion = ChatCompletion(
        id="id1",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content="I can help you with that!",
                    tool_calls=None,
                ),
            )
        ],
        created=1234567890,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
    )

    client = OpenAIChatCompletionClient(model=model, api_key="test")

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")

    # Create mock for the chat completions create method
    mock_create = AsyncMock(return_value=chat_completion)

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)  # type: ignore[reportPrivateUsage]

        await client.create(
            messages=[UserMessage(content="Hello there", source="user")],
            tools=[pass_tool],
            tool_choice="none",
        )

    # Verify the correct API call was made
    mock_create.assert_called_once()
    call_args = mock_create.call_args

    # Check that tool_choice was set to "none" (disabling tool usage)
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == "none"


@pytest.mark.asyncio
async def test_mock_tool_choice_validation_error() -> None:
    """Test tool_choice validation with invalid tool reference."""

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    def _different_function(text: str) -> str:
        """Different function."""
        return text

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")
    different_tool = FunctionTool(_different_function, description="Different tool", name="_different_function")

    messages = [UserMessage(content="Hello there", source="user")]

    # Test with a tool that's not in the tools list
    with pytest.raises(
        ValueError, match="tool_choice references '_different_function' but it's not in the provided tools"
    ):
        await client.create(
            messages=messages,
            tools=[pass_tool, add_tool],
            tool_choice=different_tool,  # This tool is not in the tools list
        )


@pytest.mark.asyncio
async def test_mock_tool_choice_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool_choice parameter with 'required' setting using mocks."""

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    model = "gpt-4o"

    # Mock successful completion with tool calls (required forces tool usage)
    chat_completion = ChatCompletion(
        id="id1",
        choices=[
            Choice(
                finish_reason="tool_calls",
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="1",
                            type="function",
                            function=Function(
                                name="_pass_function",
                                arguments=json.dumps({"input": "hello"}),
                            ),
                        )
                    ],
                ),
            )
        ],
        created=1234567890,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
    )

    client = OpenAIChatCompletionClient(model=model, api_key="test")

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")

    # Create mock for the chat completions create method
    mock_create = AsyncMock(return_value=chat_completion)

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)  # type: ignore[reportPrivateUsage]

        await client.create(
            messages=[UserMessage(content="Process some text", source="user")],
            tools=[pass_tool, add_tool],
            tool_choice="required",  # Force tool usage
        )

    # Verify the correct API call was made
    mock_create.assert_called_once()
    call_args = mock_create.call_args

    # Check that tool_choice was set correctly
    assert "tool_choice" in call_args.kwargs
    assert call_args.kwargs["tool_choice"] == "required"


# Integration tests for tool_choice using the actual OpenAI API
@pytest.mark.asyncio
async def test_openai_tool_choice_specific_tool_integration() -> None:
    """Test tool_choice parameter with a specific tool using the actual OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    model = "gpt-4o-mini"
    client = OpenAIChatCompletionClient(model=model, api_key=api_key)

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")

    # Test forcing use of specific tool
    result = await client.create(
        messages=[UserMessage(content="Process the word 'hello'", source="user")],
        tools=[pass_tool, add_tool],
        tool_choice=pass_tool,  # Force use of specific tool
    )

    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "_pass_function"
    assert result.finish_reason == "function_calls"
    assert result.usage is not None


@pytest.mark.asyncio
async def test_openai_tool_choice_auto_integration() -> None:
    """Test tool_choice parameter with 'auto' setting using the actual OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    model = "gpt-4o-mini"
    client = OpenAIChatCompletionClient(model=model, api_key=api_key)

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")

    # Test auto tool choice - model should choose to use add_numbers for math
    result = await client.create(
        messages=[UserMessage(content="What is 15 plus 27?", source="user")],
        tools=[pass_tool, add_tool],
        tool_choice="auto",  # Let model choose
    )

    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name == "_add_numbers"
    assert result.finish_reason == "function_calls"
    assert result.usage is not None

    # Parse arguments to verify correct values
    args = json.loads(result.content[0].arguments)
    assert args["a"] == 15
    assert args["b"] == 27


@pytest.mark.asyncio
async def test_openai_tool_choice_none_integration() -> None:
    """Test tool_choice parameter with 'none' setting using the actual OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    model = "gpt-4o-mini"
    client = OpenAIChatCompletionClient(model=model, api_key=api_key)

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")

    # Test none tool choice - model should not use any tools
    result = await client.create(
        messages=[UserMessage(content="Hello there, how are you?", source="user")],
        tools=[pass_tool],
        tool_choice="none",  # Disable tool usage
    )

    assert isinstance(result.content, str)
    assert len(result.content) > 0
    assert result.finish_reason == "stop"
    assert result.usage is not None


@pytest.mark.asyncio
async def test_openai_tool_choice_required_integration() -> None:
    """Test tool_choice parameter with 'required' setting using the actual OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    model = "gpt-4o-mini"
    client = OpenAIChatCompletionClient(model=model, api_key=api_key)

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")

    # Test required tool choice - model must use a tool even for general conversation
    result = await client.create(
        messages=[UserMessage(content="Say hello to me", source="user")],
        tools=[pass_tool, add_tool],
        tool_choice="required",  # Force tool usage
    )

    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], FunctionCall)
    assert result.content[0].name in ["_pass_function", "_add_numbers"]
    assert result.finish_reason == "function_calls"
    assert result.usage is not None


@pytest.mark.asyncio
async def test_openai_tool_choice_validation_error_integration() -> None:
    """Test tool_choice validation with invalid tool reference using the actual OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment variables")

    def _pass_function(input: str) -> str:
        """Simple passthrough function."""
        return f"Processed: {input}"

    def _add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    def _different_function(text: str) -> str:
        """Different function."""
        return text

    model = "gpt-4o-mini"
    client = OpenAIChatCompletionClient(model=model, api_key=api_key)

    # Define tools
    pass_tool = FunctionTool(_pass_function, description="Process input text", name="_pass_function")
    add_tool = FunctionTool(_add_numbers, description="Add two numbers together", name="_add_numbers")
    different_tool = FunctionTool(_different_function, description="Different tool", name="_different_function")

    messages = [UserMessage(content="Hello there", source="user")]

    # Test with a tool that's not in the tools list
    with pytest.raises(
        ValueError, match="tool_choice references '_different_function' but it's not in the provided tools"
    ):
        await client.create(
            messages=messages,
            tools=[pass_tool, add_tool],
            tool_choice=different_tool,  # This tool is not in the tools list
        )


# TODO: add integration tests for Azure OpenAI using AAD token.
