import asyncio

import pytest

import google.generativeai as genai
from google.generativeai import protos as proto
from google.generativeai.types import generation_types, answer_types
from autogen_core.base import CancellationToken
from autogen_core.components.models import UserMessage, SystemMessage
from autogen_ext.models import GeminiChatCompletionClient


async def _mock_create(*args, **kwargs):
    stream = kwargs.get("stream", False)
    if not stream:
        return generation_types.AsyncGenerateContentResponse.from_response(
            response=proto.GenerateContentResponse(
                candidates=[  # type: ignore
                    {
                        "content": {},
                        "finish_reason": answer_types.FinishReason.BLOCKLIST,
                    }
                ]
            )
        )


@pytest.mark.asyncio
async def test_gemini_chat_completion_client() -> None:
    client = GeminiChatCompletionClient(api_key="api_key", model="gemini-pro")
    assert client


@pytest.mark.asyncio
async def test_gemini_chat_completion_client_create(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(genai.ChatSession, "send_message_async", _mock_create)
    client = GeminiChatCompletionClient(api_key="api_key")
    result = await client.create(messages=[UserMessage(content="Hello", source="user")])
    assert result.content == "Hello"
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_gemini_chat_completion_client_create_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(genai.ChatSession, "send_message_async", _mock_create)
    client = GeminiChatCompletionClient(api_key="api_key")
    cancellation_token = CancellationToken()
    task = asyncio.create_task(
        client.create(messages=[UserMessage(content="Hello", source="user")], cancellation_token=cancellation_token)
    )
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
