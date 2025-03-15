import json
import logging
from typing import Any, AsyncGenerator, List, Mapping

import httpx
import pytest
import pytest_asyncio
from autogen_core import FunctionCall
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    UserMessage,
)
from autogen_core.tools import FunctionTool
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.ollama._ollama_client import OLLAMA_VALID_CREATE_KWARGS_KEYS
from httpx import Response
from ollama import AsyncClient, ChatResponse, Message
from pydantic import BaseModel


def _mock_request(*args: Any, **kwargs: Any) -> Response:
    return Response(status_code=200, content="{'response': 'Hello world!'}")


@pytest.mark.asyncio
async def test_ollama_chat_completion_client_doesnt_error_with_host_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncClient, "_request", _mock_request)

    client = OllamaChatCompletionClient(model="llama3.1", host="http://testyhostname:11434")

    ## Call to client.create will throw a ConnectionError,
    # but that will only occur if the call to the AsyncChat's .chat() method does not receive unexpected kwargs
    # and does not throw a TypeError with unrecognized kwargs
    # (i.e. the extra unrecognized kwargs have been successfully removed)
    try:
        await client.create([UserMessage(content="hi", source="user")])
    except TypeError as e:
        assert "AsyncClient.chat() got an unexpected keyword argument" not in e.args[0]


def test_create_args_from_config_drops_unexpected_kwargs() -> None:
    test_config: Mapping[str, Any] = {
        "model": "llama3.1",
        "messages": [],
        "tools": [],
        "stream": False,
        "format": "json",
        "options": {},
        "keep_alive": 100,
        "extra_unexpected_kwarg": "value",
        "another_extra_unexpected_kwarg": "another_value",
    }

    client = OllamaChatCompletionClient(**test_config)

    final_create_args = client.get_create_args()

    for arg in final_create_args.keys():
        assert arg in OLLAMA_VALID_CREATE_KWARGS_KEYS


@pytest.mark.asyncio
async def test_create(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    model = "llama3.2"
    content_raw = "Hello world! This is a test response. Test response."

    async def _mock_chat(*args: Any, **kwargs: Any) -> ChatResponse:
        return ChatResponse(
            model=model,
            done=True,
            done_reason="stop",
            message=Message(
                role="assistant",
                content=content_raw,
            ),
            prompt_eval_count=10,
            eval_count=12,
        )

    monkeypatch.setattr(AsyncClient, "chat", _mock_chat)
    with caplog.at_level(logging.INFO):
        client = OllamaChatCompletionClient(model=model)
        create_result = await client.create(
            messages=[
                UserMessage(content="hi", source="user"),
            ],
        )
        assert "LLMCall" in caplog.text and content_raw in caplog.text
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"
    assert create_result.usage is not None
    assert create_result.usage.prompt_tokens == 10
    assert create_result.usage.completion_tokens == 12
    assert create_result.content == content_raw


@pytest.mark.asyncio
async def test_create_stream(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    model = "llama3.2"
    content_raw = "Hello world! This is a test response. Test response."

    async def _mock_chat(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatResponse, None]:
        assert "stream" in kwargs
        assert kwargs["stream"] is True

        async def _mock_stream() -> AsyncGenerator[ChatResponse, None]:
            chunks = [content_raw[i : i + 5] for i in range(0, len(content_raw), 5)]
            # Simulate streaming by yielding chunks of the response
            for chunk in chunks[:-1]:
                yield ChatResponse(
                    model=model,
                    done=False,
                    message=Message(
                        role="assistant",
                        content=chunk,
                    ),
                )
            yield ChatResponse(
                model=model,
                done=True,
                done_reason="stop",
                message=Message(
                    role="assistant",
                    content=chunks[-1],
                ),
                prompt_eval_count=10,
                eval_count=12,
            )

        return _mock_stream()

    monkeypatch.setattr(AsyncClient, "chat", _mock_chat)
    client = OllamaChatCompletionClient(model=model)
    with caplog.at_level(logging.INFO):
        stream = client.create_stream(
            messages=[
                UserMessage(content="hi", source="user"),
            ],
        )
        chunks: List[str | CreateResult] = []
        async for chunk in stream:
            chunks.append(chunk)

        assert "LLMStreamStart" in caplog.text and "hi" in caplog.text
        assert "LLMStreamEnd" in caplog.text and content_raw in caplog.text
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert isinstance(chunks[-1].content, str)
    assert chunks[-1].content == content_raw
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage is not None
    assert chunks[-1].usage.prompt_tokens == 10
    assert chunks[-1].usage.completion_tokens == 12


@pytest.mark.asyncio
async def test_create_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def add(x: int, y: int) -> str:
        return str(x + y)

    add_tool = FunctionTool(add, description="Add two numbers")

    model = "llama3.2"

    async def _mock_chat(*args: Any, **kwargs: Any) -> ChatResponse:
        return ChatResponse(
            model=model,
            done=True,
            done_reason="stop",
            message=Message(
                role="assistant",
                tool_calls=[
                    Message.ToolCall(
                        function=Message.ToolCall.Function(
                            name=add_tool.name,
                            arguments={"x": 2, "y": 2},
                        ),
                    ),
                ],
            ),
            prompt_eval_count=10,
            eval_count=12,
        )

    monkeypatch.setattr(AsyncClient, "chat", _mock_chat)

    client = OllamaChatCompletionClient(model=model)
    create_result = await client.create(
        messages=[
            UserMessage(content="hi", source="user"),
        ],
        tools=[add_tool],
    )
    assert isinstance(create_result.content, list)
    assert len(create_result.content) > 0
    assert isinstance(create_result.content[0], FunctionCall)
    assert create_result.content[0].name == add_tool.name
    assert create_result.content[0].arguments == json.dumps({"x": 2, "y": 2})
    assert create_result.finish_reason == "function_calls"
    assert create_result.usage is not None
    assert create_result.usage.prompt_tokens == 10
    assert create_result.usage.completion_tokens == 12


@pytest.mark.asyncio
async def test_create_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class ResponseType(BaseModel):
        response: str

    model = "llama3.2"

    async def _mock_chat(*args: Any, **kwargs: Any) -> ChatResponse:
        return ChatResponse(
            model=model,
            done=True,
            done_reason="stop",
            message=Message(
                role="assistant",
                content=json.dumps({"response": "Hello world!"}),
            ),
            prompt_eval_count=10,
            eval_count=12,
        )

    monkeypatch.setattr(AsyncClient, "chat", _mock_chat)

    client = OllamaChatCompletionClient(model=model)
    create_result = await client.create(
        messages=[
            UserMessage(content="hi", source="user"),
        ],
        json_output=ResponseType,
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"
    assert create_result.usage is not None
    assert create_result.usage.prompt_tokens == 10
    assert create_result.usage.completion_tokens == 12
    assert ResponseType.model_validate_json(create_result.content)

    create_result = await client.create(
        messages=[
            UserMessage(content="hi", source="user"),
        ],
        extra_create_args={"format": ResponseType.model_json_schema()},
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"
    assert create_result.usage is not None
    assert create_result.usage.prompt_tokens == 10
    assert create_result.usage.completion_tokens == 12
    assert ResponseType.model_validate_json(create_result.content)

    # Test case when response_format is in extra_create_args.
    with pytest.warns(DeprecationWarning, match="Using response_format will be deprecated. Use json_output instead."):
        create_result = await client.create(
            messages=[
                UserMessage(content="hi", source="user"),
            ],
            extra_create_args={"response_format": ResponseType},
        )

    # Test case when response_format is in extra_create_args but is not a pydantic model.
    with pytest.raises(ValueError, match="response_format must be a Pydantic model class"):
        create_result = await client.create(
            messages=[
                UserMessage(content="hi", source="user"),
            ],
            extra_create_args={"response_format": "json"},
        )

    # Test case when response_format is in extra_create_args and json_output is also set.
    with pytest.raises(
        ValueError,
        match="response_format and json_output cannot be set to a Pydantic model class at the same time. Use json_output instead.",
    ):
        create_result = await client.create(
            messages=[
                UserMessage(content="hi", source="user"),
            ],
            extra_create_args={"response_format": ResponseType},
            json_output=ResponseType,
        )

    # Test case when format is in extra_create_args and json_output is also set.
    with pytest.raises(
        ValueError, match="json_output and format cannot be set at the same time. Use json_output instead."
    ):
        create_result = await client.create(
            messages=[
                UserMessage(content="hi", source="user"),
            ],
            extra_create_args={"format": ResponseType.model_json_schema()},
            json_output=ResponseType,
        )


@pytest.mark.asyncio
async def test_create_stream_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class ResponseType(BaseModel):
        response: str

    model = "llama3.2"
    content_raw = json.dumps({"response": "Hello world! This is a test response. Test response."})

    async def _mock_chat(*args: Any, **kwargs: Any) -> AsyncGenerator[ChatResponse, None]:
        assert "stream" in kwargs
        assert kwargs["stream"] is True

        async def _mock_stream() -> AsyncGenerator[ChatResponse, None]:
            chunks = [content_raw[i : i + 5] for i in range(0, len(content_raw), 5)]
            # Simulate streaming by yielding chunks of the response
            for chunk in chunks[:-1]:
                yield ChatResponse(
                    model=model,
                    done=False,
                    message=Message(
                        role="assistant",
                        content=chunk,
                    ),
                )
            yield ChatResponse(
                model=model,
                done=True,
                done_reason="stop",
                message=Message(
                    role="assistant",
                    content=chunks[-1],
                ),
                prompt_eval_count=10,
                eval_count=12,
            )

        return _mock_stream()

    monkeypatch.setattr(AsyncClient, "chat", _mock_chat)

    client = OllamaChatCompletionClient(model=model)
    stream = client.create_stream(
        messages=[
            UserMessage(content="hi", source="user"),
        ],
        json_output=ResponseType,
    )
    chunks: List[str | CreateResult] = []
    async for chunk in stream:
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert isinstance(chunks[-1].content, str)
    assert chunks[-1].content == content_raw
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage is not None
    assert chunks[-1].usage.prompt_tokens == 10
    assert chunks[-1].usage.completion_tokens == 12
    assert ResponseType.model_validate_json(chunks[-1].content)


@pytest_asyncio.fixture  # type: ignore
async def ollama_client(request: pytest.FixtureRequest) -> OllamaChatCompletionClient:
    model = request.node.callspec.params["model"]  # type: ignore
    assert isinstance(model, str)
    # Check if the model is running locally.
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:11434/v1/models/{model}")
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        pytest.skip(f"{model} model is not running locally: {e}")
    except httpx.ConnectError as e:
        pytest.skip(f"Ollama is not running locally: {e}")
    return OllamaChatCompletionClient(model=model)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["deepseek-r1:1.5b", "llama3.2:1b"])
async def test_ollama_create(model: str, ollama_client: OllamaChatCompletionClient) -> None:
    create_result = await ollama_client.create(
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

    chunks: List[str | CreateResult] = []
    async for chunk in ollama_client.create_stream(
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


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["deepseek-r1:1.5b", "llama3.2:1b"])
async def test_ollama_create_structured_output(model: str, ollama_client: OllamaChatCompletionClient) -> None:
    class ResponseType(BaseModel):
        calculation: str
        result: str

    create_result = await ollama_client.create(
        messages=[
            UserMessage(
                content="Taking two balls from a bag of 10 green balls and 20 red balls, "
                "what is the probability of getting a green and a red balls?",
                source="user",
            ),
        ],
        json_output=ResponseType,
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"
    assert create_result.usage is not None
    assert ResponseType.model_validate_json(create_result.content)

    # Test streaming completion with the Ollama deepseek-r1:1.5b model.
    chunks: List[str | CreateResult] = []
    async for chunk in ollama_client.create_stream(
        messages=[
            UserMessage(
                content="Taking two balls from a bag of 10 green balls and 20 red balls, "
                "what is the probability of getting a green and a red balls?",
                source="user",
            ),
        ],
        json_output=ResponseType,
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    assert chunks[-1].finish_reason == "stop"
    assert isinstance(chunks[-1].content, str)
    assert len(chunks[-1].content) > 0
    assert chunks[-1].usage is not None
    assert ResponseType.model_validate_json(chunks[-1].content)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["qwen2.5:0.5b", "llama3.2:1b"])
async def test_ollama_create_tools(model: str, ollama_client: OllamaChatCompletionClient) -> None:
    def add(x: int, y: int) -> str:
        return str(x + y)

    add_tool = FunctionTool(add, description="Add two numbers")

    create_result = await ollama_client.create(
        messages=[
            UserMessage(
                content="What is 2 + 2? Use the add tool.",
                source="user",
            ),
        ],
        tools=[add_tool],
    )
    assert isinstance(create_result.content, list)
    assert len(create_result.content) > 0
    assert isinstance(create_result.content[0], FunctionCall)
    assert create_result.content[0].name == add_tool.name
    assert create_result.finish_reason == "function_calls"

    execution_result = FunctionExecutionResult(
        content="4",
        name=add_tool.name,
        call_id=create_result.content[0].id,
        is_error=False,
    )
    create_result = await ollama_client.create(
        messages=[
            UserMessage(
                content="What is 2 + 2? Use the add tool.",
                source="user",
            ),
            AssistantMessage(
                content=create_result.content,
                source="assistant",
            ),
            FunctionExecutionResultMessage(
                content=[execution_result],
            ),
        ],
    )
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"


@pytest.mark.skip("TODO: Does Ollama support structured outputs with tools?")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["llama3.2:1b"])
async def test_ollama_create_structured_output_with_tools(
    model: str, ollama_client: OllamaChatCompletionClient
) -> None:
    class ResponseType(BaseModel):
        calculation: str
        result: str

    def add(x: int, y: int) -> str:
        return str(x + y)

    add_tool = FunctionTool(add, description="Add two numbers")

    create_result = await ollama_client.create(
        messages=[
            UserMessage(
                content="What is 2 + 2? Use the add tool.",
                source="user",
            ),
        ],
        tools=[add_tool],
        json_output=ResponseType,
    )
    assert isinstance(create_result.content, list)
    assert len(create_result.content) > 0
    assert isinstance(create_result.content[0], FunctionCall)
    assert create_result.content[0].name == add_tool.name
    assert create_result.finish_reason == "function_calls"
    assert create_result.thought is not None
    assert ResponseType.model_validate_json(create_result.thought)


@pytest.mark.skip("TODO: Fix streaming with tools")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["qwen2.5:0.5b", "llama3.2:1b"])
async def test_ollama_create_stream_tools(model: str, ollama_client: OllamaChatCompletionClient) -> None:
    def add(x: int, y: int) -> str:
        return str(x + y)

    add_tool = FunctionTool(add, description="Add two numbers")

    stream = ollama_client.create_stream(
        messages=[
            UserMessage(
                content="What is 2 + 2? Use the add tool.",
                source="user",
            ),
        ],
        tools=[add_tool],
    )
    chunks: List[str | CreateResult] = []
    async for chunk in stream:
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    create_result = chunks[-1]
    assert isinstance(create_result.content, list)
    assert len(create_result.content) > 0
    assert isinstance(create_result.content[0], FunctionCall)
    assert create_result.content[0].name == add_tool.name
    assert create_result.finish_reason == "function_calls"

    execution_result = FunctionExecutionResult(
        content="4",
        name=add_tool.name,
        call_id=create_result.content[0].id,
        is_error=False,
    )
    stream = ollama_client.create_stream(
        messages=[
            UserMessage(
                content="What is 2 + 2? Use the add tool.",
                source="user",
            ),
            AssistantMessage(
                content=create_result.content,
                source="assistant",
            ),
            FunctionExecutionResultMessage(
                content=[execution_result],
            ),
        ],
    )
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    assert len(chunks) > 0
    assert isinstance(chunks[-1], CreateResult)
    create_result = chunks[-1]
    assert isinstance(create_result.content, str)
    assert len(create_result.content) > 0
    assert create_result.finish_reason == "stop"
