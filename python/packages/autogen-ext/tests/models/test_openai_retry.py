"""Tests for auto-retry with exponential backoff in OpenAI chat completion clients."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai._openai_client import (
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_RETRY_ON_ERROR_CODES,
    BaseOpenAIChatCompletionClient,
)
from openai import APIStatusError
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage


def _make_chat_completion(content: str = "Hello") -> ChatCompletion:
    return ChatCompletion(
        id="test-id",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(role="assistant", content=content),
            )
        ],
        created=1234567890,
        model="gpt-4o",
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
    )


def _make_api_status_error(status_code: int) -> APIStatusError:
    response = httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://api.openai.com"))
    return APIStatusError(message=f"Error {status_code}", response=response, body=None)


@pytest.mark.asyncio
async def test_retry_defaults() -> None:
    """Test that retry defaults are correctly set."""
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gpt-4o"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": True,
        },
    )
    assert client._retry_max_attempts == DEFAULT_RETRY_MAX_ATTEMPTS  # noqa: SLF001
    assert client._retry_on_error_codes == DEFAULT_RETRY_ON_ERROR_CODES  # noqa: SLF001


@pytest.mark.asyncio
async def test_retry_custom_config() -> None:
    """Test that custom retry config is applied."""
    mock_client = MagicMock()
    client = BaseOpenAIChatCompletionClient(
        client=mock_client,
        create_args={"model": "gpt-4o"},
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": True,
        },
        retry_max_attempts=5,
        retry_on_error_codes=[429, 503],
    )
    assert client._retry_max_attempts == 5  # noqa: SLF001
    assert client._retry_on_error_codes == [429, 503]  # noqa: SLF001


@pytest.mark.asyncio
async def test_create_retries_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create retries on 429 status code."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(429),
            _make_chat_completion("Success after retry"),
        ]
    )

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.create(
                messages=[UserMessage(content="Hello", source="user")],
            )

    assert result.content == "Success after retry"
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_create_retries_on_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create retries on 500 status code."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(500),
            _make_api_status_error(502),
            _make_chat_completion("Success after retries"),
        ]
    )

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.create(
                messages=[UserMessage(content="Hello", source="user")],
            )

    assert result.content == "Success after retries"
    assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_create_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create raises after exhausting all retry attempts."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(429),
            _make_api_status_error(429),
            _make_api_status_error(429),
        ]
    )

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(APIStatusError) as exc_info:
                await client.create(
                    messages=[UserMessage(content="Hello", source="user")],
                )

    assert exc_info.value.status_code == 429
    assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_create_no_retry_on_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create does not retry on non-retryable status codes (e.g., 401)."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    mock_create = AsyncMock(side_effect=_make_api_status_error(401))

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with pytest.raises(APIStatusError) as exc_info:
            await client.create(
                messages=[UserMessage(content="Hello", source="user")],
            )

    assert exc_info.value.status_code == 401
    assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_create_retries_on_424(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create retries on 424 (Failed Dependency) status code."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(424),
            _make_chat_completion("Success after 424 retry"),
        ]
    )

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.create(
                messages=[UserMessage(content="Hello", source="user")],
            )

    assert result.content == "Success after 424 retry"
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_create_retry_with_custom_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that custom retry_max_attempts is honored via OpenAIChatCompletionClient."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test", retry_max_attempts=2)

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(500),
            _make_api_status_error(500),
        ]
    )

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(APIStatusError):
                await client.create(
                    messages=[UserMessage(content="Hello", source="user")],
                )

    # Should only try 2 times (custom max_attempts=2)
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_create_retry_with_custom_error_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that custom retry_on_error_codes is honored."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test", retry_on_error_codes=[418])

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(418),
            _make_chat_completion("I'm a teapot, but recovered"),
        ]
    )

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.create(
                messages=[UserMessage(content="Hello", source="user")],
            )

    assert result.content == "I'm a teapot, but recovered"
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_create_exponential_backoff_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that exponential backoff sleep is called with increasing delays."""
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    mock_create = AsyncMock(
        side_effect=[
            _make_api_status_error(500),
            _make_api_status_error(500),
            _make_chat_completion("OK"),
        ]
    )

    sleep_calls: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", side_effect=mock_sleep):
            await client.create(
                messages=[UserMessage(content="Hello", source="user")],
            )

    assert len(sleep_calls) == 2
    # First retry: 2^0 + jitter (1.0 to 2.0)
    assert 1.0 <= sleep_calls[0] <= 2.0
    # Second retry: 2^1 + jitter (2.0 to 3.0)
    assert 2.0 <= sleep_calls[1] <= 3.0


@pytest.mark.asyncio
async def test_stream_retries_on_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that create_stream retries the initial stream creation on transient errors."""
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
    from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="test")

    # Create a mock stream that yields one chunk then stops
    chunk = ChatCompletionChunk(
        id="test",
        choices=[
            ChunkChoice(
                delta=ChoiceDelta(content="Hello", role="assistant"),
                finish_reason="stop",
                index=0,
            )
        ],
        created=1234567890,
        model="gpt-4o",
        object="chat.completion.chunk",
        usage=CompletionUsage(completion_tokens=5, prompt_tokens=3, total_tokens=8),
    )

    async def mock_stream_gen() -> None:
        yield chunk

    mock_stream = mock_stream_gen()

    # First call raises 500, second call returns the stream
    call_count = 0

    async def mock_create(**kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _make_api_status_error(500)
        return mock_stream

    with monkeypatch.context() as mp:
        mp.setattr(client._client.chat.completions, "create", mock_create)
        with patch("autogen_ext.models.openai._openai_client.asyncio.sleep", new_callable=AsyncMock):
            collected = []
            async for item in client.create_stream(
                messages=[UserMessage(content="Hello", source="user")],
            ):
                collected.append(item)

    assert call_count == 2
    # Should have the text chunk and the final CreateResult
    assert len(collected) >= 1
