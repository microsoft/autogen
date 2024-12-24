import asyncio
from datetime import datetime
from typing import AsyncGenerator, Any

import pytest
from azure.ai.inference.aio import (
    ChatCompletionsClient,
)


from azure.ai.inference.models import (
    ChatChoice,
    ChatResponseMessage,
    CompletionsUsage,
    ChatCompletionsResponseFormatJSON,
)

from azure.ai.inference.models import (
    ChatCompletions,
    StreamingChatCompletionsUpdate,
    StreamingChatChoiceUpdate,
    StreamingChatResponseMessageUpdate,
)

from azure.core.credentials import AzureKeyCredential

from autogen_core import CancellationToken
from autogen_core.models import UserMessage
from autogen_ext.models.azure import AzureAIChatCompletionClient


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


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client() -> None:
    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_capabilities={
            "json_output": False,
            "function_calling": False,
            "vision": False,
        },
        model="model",
    )
    assert client


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create(monkeypatch: pytest.MonkeyPatch) -> None:
    # monkeypatch.setattr(AsyncCompletions, "create", _mock_create)
    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create)
    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_capabilities={
            "json_output": False,
            "function_calling": False,
            "vision": False,
        },
    )
    result = await client.create(messages=[UserMessage(content="Hello", source="user")])
    assert result.content == "Hello"


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create)
    chunks = []
    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_capabilities={
            "json_output": False,
            "function_calling": False,
            "vision": False,
        },
    )
    async for chunk in client.create_stream(messages=[UserMessage(content="Hello", source="user")]):
        chunks.append(chunk)

    assert chunks[0] == "Hello"
    assert chunks[1] == " Another Hello"
    assert chunks[2] == " Yet Another Hello"


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create)
    cancellation_token = CancellationToken()
    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_capabilities={
            "json_output": False,
            "function_calling": False,
            "vision": False,
        },
    )
    task = asyncio.create_task(
        client.create(messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token)
    )
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_azure_ai_chat_completion_client_create_stream_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ChatCompletionsClient, "complete", _mock_create)
    cancellation_token = CancellationToken()
    client = AzureAIChatCompletionClient(
        endpoint="endpoint",
        credential=AzureKeyCredential("api_key"),
        model_capabilities={
            "json_output": False,
            "function_calling": False,
            "vision": False,
        },
    )
    stream = client.create_stream(
        messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token
    )
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        async for _ in stream:
            pass
