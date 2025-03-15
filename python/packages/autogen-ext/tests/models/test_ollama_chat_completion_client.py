from typing import Any, List, Mapping

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
from ollama import AsyncClient
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
