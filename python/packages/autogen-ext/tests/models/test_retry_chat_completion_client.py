"""Tests for RetryableChatCompletionClient auto-recovery logic."""

import asyncio
from typing import Any, AsyncGenerator, Literal, Mapping, Optional, Sequence, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,
    ModelInfo,
    RequestUsage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel

from autogen_ext.models.retry import RetryableChatCompletionClient, RetryConfig
from autogen_ext.models.retry._retry_chat_completion_client import (
    _calculate_delay,
    _get_retry_after,
    _get_status_code,
    _is_retryable,
)


# ---- Helpers ----


class MockChatCompletionClient(ChatCompletionClient):
    """A mock chat completion client for testing."""

    component_type = "model"
    component_config_schema = BaseModel

    def __init__(self) -> None:
        self.create_mock = AsyncMock()
        self._stream_results: list[Any] = []
        self._stream_error: Optional[Exception] = None
        self._close_called = False

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
        return await self.create_mock(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )

    async def _stream_gen(self) -> AsyncGenerator[Union[str, CreateResult], None]:
        if self._stream_error is not None:
            raise self._stream_error
        for item in self._stream_results:
            yield item

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
        return self._stream_gen()

    async def close(self) -> None:
        self._close_called = True

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=10, completion_tokens=20)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=100, completion_tokens=200)

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 42

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 1000

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        return {"vision": False, "function_calling": True, "json_output": True}  # type: ignore

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="unknown",
            structured_output=False,
        )


def _make_create_result(content: str = "Hello") -> CreateResult:
    return CreateResult(
        finish_reason="stop",
        content=content,
        usage=RequestUsage(prompt_tokens=5, completion_tokens=10),
        cached=False,
    )


def _make_error_with_status(name: str, status_code: int, message: str = "error") -> Exception:
    """Create a mock error with a status_code attribute."""
    error = Exception(message)
    error.__class__ = type(name, (Exception,), {})
    error.status_code = status_code  # type: ignore[attr-defined]
    return error


def _make_rate_limit_error(retry_after: Optional[str] = None) -> Exception:
    """Create a mock RateLimitError."""
    error = Exception("Rate limit is exceeded. Try again in 1 seconds.")
    error.__class__ = type("RateLimitError", (Exception,), {})
    error.status_code = 429  # type: ignore[attr-defined]
    if retry_after is not None:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": retry_after}
        error.response = mock_response  # type: ignore[attr-defined]
    return error


# ---- Tests for RetryConfig ----


class TestRetryConfig:
    def test_default_config(self) -> None:
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert 429 in config.retry_on_status_codes
        assert 500 in config.retry_on_status_codes
        assert 502 in config.retry_on_status_codes
        assert 503 in config.retry_on_status_codes
        assert "RateLimitError" in config.retry_on_error_types

    def test_custom_config(self) -> None:
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.jitter is False


# ---- Tests for helper functions ----


class TestGetStatusCode:
    def test_status_code_attribute(self) -> None:
        error = Exception("test")
        error.status_code = 429  # type: ignore[attr-defined]
        assert _get_status_code(error) == 429

    def test_response_status_code(self) -> None:
        error = Exception("test")
        mock_response = MagicMock()
        mock_response.status_code = 500
        error.response = mock_response  # type: ignore[attr-defined]
        assert _get_status_code(error) == 500

    def test_no_status_code(self) -> None:
        error = Exception("test")
        assert _get_status_code(error) is None


class TestGetRetryAfter:
    def test_retry_after_header(self) -> None:
        error = Exception("test")
        mock_response = MagicMock()
        mock_response.headers = {"retry-after": "5"}
        error.response = mock_response  # type: ignore[attr-defined]
        assert _get_retry_after(error) == 5.0

    def test_retry_after_in_message(self) -> None:
        error = Exception("Rate limit is exceeded. Try again in 2 seconds.")
        assert _get_retry_after(error) == 2.0

    def test_no_retry_after(self) -> None:
        error = Exception("some other error")
        assert _get_retry_after(error) is None


class TestIsRetryable:
    def test_rate_limit_error(self) -> None:
        config = RetryConfig()
        error = _make_rate_limit_error()
        assert _is_retryable(error, config) is True

    def test_server_error_500(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("APIStatusError", 500)
        assert _is_retryable(error, config) is True

    def test_server_error_502(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("APIStatusError", 502)
        assert _is_retryable(error, config) is True

    def test_server_error_503(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("APIStatusError", 503)
        assert _is_retryable(error, config) is True

    def test_timeout_error(self) -> None:
        config = RetryConfig()
        error = TimeoutError("Connection timed out")
        assert _is_retryable(error, config) is True

    def test_connection_error(self) -> None:
        config = RetryConfig()
        error = ConnectionError("Connection refused")
        assert _is_retryable(error, config) is True

    def test_auth_error_not_retryable(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("AuthenticationError", 401)
        assert _is_retryable(error, config) is False

    def test_permission_denied_not_retryable(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("PermissionDeniedError", 403)
        assert _is_retryable(error, config) is False

    def test_bad_request_not_retryable(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("SomeError", 400)
        assert _is_retryable(error, config) is False

    def test_not_found_not_retryable(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("SomeError", 404)
        assert _is_retryable(error, config) is False

    def test_unknown_error_not_retryable(self) -> None:
        config = RetryConfig()
        error = ValueError("some value error")
        assert _is_retryable(error, config) is False

    def test_failed_dependency_424(self) -> None:
        config = RetryConfig()
        error = _make_error_with_status("APIStatusError", 424)
        assert _is_retryable(error, config) is True


class TestCalculateDelay:
    def test_exponential_backoff_no_jitter(self) -> None:
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False, max_delay=60.0)
        assert _calculate_delay(0, config) == 1.0
        assert _calculate_delay(1, config) == 2.0
        assert _calculate_delay(2, config) == 4.0
        assert _calculate_delay(3, config) == 8.0

    def test_max_delay_cap(self) -> None:
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False, max_delay=5.0)
        assert _calculate_delay(10, config) == 5.0

    def test_retry_after_respected(self) -> None:
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False, max_delay=60.0)
        # Attempt 0 would give delay=1.0, but retry_after=10 should override
        assert _calculate_delay(0, config, retry_after=10.0) == 10.0

    def test_jitter_adds_randomness(self) -> None:
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True, max_delay=60.0)
        delays = {_calculate_delay(0, config) for _ in range(20)}
        # With jitter, we should get different values
        assert len(delays) > 1


# ---- Tests for RetryableChatCompletionClient ----


class TestRetryableChatCompletionClientCreate:
    @pytest.mark.asyncio
    async def test_success_no_retry(self) -> None:
        """Test that a successful call does not trigger any retries."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("Success")
        mock_client.create_mock.return_value = expected_result

        client = RetryableChatCompletionClient(client=mock_client)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result
        assert mock_client.create_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self) -> None:
        """Test that rate limit errors trigger retries."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("After retry")
        mock_client.create_mock.side_effect = [
            _make_rate_limit_error(),
            expected_result,
        ]

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result
        assert mock_client.create_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self) -> None:
        """Test that server errors (500) trigger retries."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("Recovered")
        mock_client.create_mock.side_effect = [
            _make_error_with_status("InternalServerError", 500),
            _make_error_with_status("InternalServerError", 502),
            expected_result,
        ]

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result
        assert mock_client.create_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(self) -> None:
        """Test that permanent errors (400) are not retried."""
        mock_client = MockChatCompletionClient()
        mock_client.create_mock.side_effect = _make_error_with_status("BadRequestError", 400)

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]

        with pytest.raises(Exception):
            await client.create(messages)

        assert mock_client.create_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self) -> None:
        """Test that authentication errors are not retried."""
        mock_client = MockChatCompletionClient()
        mock_client.create_mock.side_effect = _make_error_with_status("AuthenticationError", 401)

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]

        with pytest.raises(Exception):
            await client.create(messages)

        assert mock_client.create_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        """Test that the error is raised after all retries are exhausted."""
        mock_client = MockChatCompletionClient()
        error = _make_rate_limit_error()
        mock_client.create_mock.side_effect = error

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]

        with pytest.raises(Exception):
            await client.create(messages)

        # 1 initial + 2 retries = 3 total attempts
        assert mock_client.create_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self) -> None:
        """Test that timeout errors trigger retries."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("OK")
        mock_client.create_mock.side_effect = [
            TimeoutError("Connection timed out"),
            expected_result,
        ]

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result
        assert mock_client.create_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self) -> None:
        """Test that connection errors trigger retries."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("Connected")
        mock_client.create_mock.side_effect = [
            ConnectionError("Connection refused"),
            expected_result,
        ]

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result
        assert mock_client.create_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_retry_after_header(self) -> None:
        """Test that Retry-After header is respected."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("OK")
        mock_client.create_mock.side_effect = [
            _make_rate_limit_error(retry_after="0.01"),
            expected_result,
        ]

        config = RetryConfig(max_retries=3, base_delay=0.001, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_retry_on_424_failed_dependency(self) -> None:
        """Test that 424 (failed dependency) errors are retried, as mentioned in the issue."""
        mock_client = MockChatCompletionClient()
        expected_result = _make_create_result("OK")
        mock_client.create_mock.side_effect = [
            _make_error_with_status("APIStatusError", 424, "Error occurred while processing image(s)."),
            expected_result,
        ]

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]
        result = await client.create(messages)

        assert result == expected_result
        assert mock_client.create_mock.call_count == 2


class TestRetryableChatCompletionClientStream:
    @pytest.mark.asyncio
    async def test_stream_success_no_retry(self) -> None:
        """Test that a successful stream does not trigger retries."""
        mock_client = MockChatCompletionClient()
        result = _make_create_result("Complete")
        mock_client._stream_results = ["chunk1", "chunk2", result]

        client = RetryableChatCompletionClient(client=mock_client)
        messages = [UserMessage(content="Hello", source="test")]

        chunks = []
        async for chunk in client.create_stream(messages):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2", result]

    @pytest.mark.asyncio
    async def test_stream_retry_on_error(self) -> None:
        """Test that stream errors trigger retries."""
        mock_client = MockChatCompletionClient()
        error = _make_rate_limit_error()
        result = _make_create_result("OK")
        call_count = 0

        async def mock_stream_gen() -> AsyncGenerator[Union[str, CreateResult], None]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            yield "chunk"
            yield result

        mock_client._stream_gen = mock_stream_gen  # type: ignore[assignment]

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]

        chunks = []
        async for chunk in client.create_stream(messages):
            chunks.append(chunk)

        assert chunks == ["chunk", result]
        assert call_count == 2


class TestRetryableChatCompletionClientDelegation:
    """Test that delegated methods work correctly."""

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        await client.close()
        assert mock_client._close_called is True

    def test_actual_usage(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        usage = client.actual_usage()
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20

    def test_total_usage(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        usage = client.total_usage()
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 200

    def test_count_tokens(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        messages = [UserMessage(content="Hello", source="test")]
        assert client.count_tokens(messages) == 42

    def test_remaining_tokens(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        messages = [UserMessage(content="Hello", source="test")]
        assert client.remaining_tokens(messages) == 1000

    def test_model_info(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        info = client.model_info
        assert info["vision"] is False
        assert info["function_calling"] is True

    def test_capabilities(self) -> None:
        mock_client = MockChatCompletionClient()
        client = RetryableChatCompletionClient(client=mock_client)
        caps = client.capabilities  # type: ignore
        assert caps["vision"] is False


class TestRetryableZeroRetries:
    @pytest.mark.asyncio
    async def test_zero_retries_raises_immediately(self) -> None:
        """Test that with max_retries=0, errors are raised immediately."""
        mock_client = MockChatCompletionClient()
        mock_client.create_mock.side_effect = _make_rate_limit_error()

        config = RetryConfig(max_retries=0)
        client = RetryableChatCompletionClient(client=mock_client, retry_config=config)
        messages = [UserMessage(content="Hello", source="test")]

        with pytest.raises(Exception):
            await client.create(messages)

        assert mock_client.create_mock.call_count == 1
