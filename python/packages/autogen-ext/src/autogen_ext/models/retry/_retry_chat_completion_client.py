"""A wrapper client that adds auto-recovery with configurable retry logic to any ChatCompletionClient.

This module provides a :class:`RetryableChatCompletionClient` that wraps an existing
:class:`~autogen_core.models.ChatCompletionClient` and automatically retries on transient
errors such as rate limits (HTTP 429), server errors (HTTP 500, 502, 503, 504),
and timeout errors.

The retry strategy uses exponential backoff with jitter to prevent thundering herd
problems when many clients are retrying simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional, Sequence, Set, Union

from autogen_core import TRACE_LOGGER_NAME, CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel
from typing_extensions import AsyncGenerator

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts. Defaults to 3.
        base_delay: Base delay in seconds for exponential backoff. Defaults to 1.0.
        max_delay: Maximum delay in seconds between retries. Defaults to 60.0.
        exponential_base: Base for exponential backoff calculation. Defaults to 2.0.
        jitter: Whether to add random jitter to the delay. Defaults to True.
        retry_on_status_codes: HTTP status codes that should trigger a retry.
            Defaults to {408, 424, 429, 500, 502, 503, 504}.
        retry_on_error_types: Exception type names (strings) that should trigger a retry.
            Defaults to common transient error types.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status_codes: Set[int] = field(
        default_factory=lambda: {408, 424, 429, 500, 502, 503, 504}
    )
    retry_on_error_types: Set[str] = field(
        default_factory=lambda: {
            "APITimeoutError",
            "RateLimitError",
            "APIStatusError",
            "APIConnectionError",
            "InternalServerError",
        }
    )


def _get_status_code(error: Exception) -> Optional[int]:
    """Extract HTTP status code from an exception, if available."""
    # OpenAI SDK errors have a status_code attribute
    status_code = getattr(error, "status_code", None)
    if status_code is not None:
        return int(status_code)
    # Some errors store it in the response
    response = getattr(error, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if code is not None:
            return int(code)
    return None


def _get_retry_after(error: Exception) -> Optional[float]:
    """Extract Retry-After header value from an exception, if available."""
    response = getattr(error, "response", None)
    if response is not None:
        headers = getattr(response, "headers", {})
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except (ValueError, TypeError):
                pass
    # Some OpenAI errors include retry info in the message
    message = str(error)
    if "Try again in" in message:
        try:
            # Parse "Try again in X seconds" pattern
            parts = message.split("Try again in")
            if len(parts) > 1:
                num_str = parts[1].strip().split()[0]
                return float(num_str)
        except (ValueError, IndexError):
            pass
    return None


def _is_retryable(error: Exception, config: RetryConfig) -> bool:
    """Determine if an error is retryable based on the retry configuration.

    An error is considered retryable if:
    1. Its type name matches one of the configured error types, OR
    2. It has an HTTP status code that matches one of the configured status codes.

    Errors that are clearly permanent (e.g., authentication errors, invalid requests)
    are never retried.
    """
    error_type_name = type(error).__name__

    # Never retry authentication or permission errors
    if error_type_name in ("AuthenticationError", "PermissionDeniedError"):
        return False

    # Never retry on 400 (bad request) or 401/403 (auth errors)
    status_code = _get_status_code(error)
    if status_code is not None and status_code in (400, 401, 403, 404):
        return False

    # Check if the error type is in the retryable set
    if error_type_name in config.retry_on_error_types:
        return True

    # Check if the status code is in the retryable set
    if status_code is not None and status_code in config.retry_on_status_codes:
        return True

    # Check for common transient error patterns
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return True

    return False


def _calculate_delay(attempt: int, config: RetryConfig, retry_after: Optional[float] = None) -> float:
    """Calculate the delay before the next retry attempt.

    Uses exponential backoff with optional jitter. If a Retry-After header
    value is provided, it is used as a minimum delay.

    Args:
        attempt: The current attempt number (0-indexed).
        config: The retry configuration.
        retry_after: Optional Retry-After value from the server.

    Returns:
        The delay in seconds before the next retry.
    """
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)

    # Add jitter to prevent thundering herd
    if config.jitter:
        delay = delay * (0.5 + random.random())  # noqa: S311

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Respect Retry-After header if present
    if retry_after is not None:
        delay = max(delay, retry_after)

    return delay


class RetryableChatCompletionClient(ChatCompletionClient):
    """A wrapper that adds auto-recovery with configurable retry logic to any
    :class:`~autogen_core.models.ChatCompletionClient`.

    This client wraps an existing chat completion client and automatically retries
    failed requests based on the error type and configured retry policy. It supports:

    - Exponential backoff with configurable base and maximum delay
    - Jitter to prevent thundering herd problems
    - Configurable retryable HTTP status codes and error types
    - Respect for ``Retry-After`` response headers
    - Logging of all retry attempts
    - Classification of transient vs permanent errors

    Args:
        client: The underlying chat completion client to wrap.
        retry_config: Configuration for the retry behavior. Uses sensible defaults
            if not provided.

    Examples:

        .. code-block:: python

            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.models.retry import RetryableChatCompletionClient, RetryConfig

            # Create the underlying client
            openai_client = OpenAIChatCompletionClient(model="gpt-4o")

            # Wrap it with retry logic
            retryable_client = RetryableChatCompletionClient(
                client=openai_client,
                retry_config=RetryConfig(
                    max_retries=5,
                    base_delay=1.0,
                    max_delay=30.0,
                ),
            )

            # Use it just like any other ChatCompletionClient
            result = await retryable_client.create(
                [UserMessage(content="Hello!", source="user")]
            )
    """

    component_type = "model"
    component_config_schema = BaseModel  # placeholder for component config

    def __init__(
        self,
        client: ChatCompletionClient,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        self._client = client
        self._config = retry_config or RetryConfig()

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
        last_error: Optional[Exception] = None
        for attempt in range(self._config.max_retries + 1):
            try:
                return await self._client.create(
                    messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    json_output=json_output,
                    extra_create_args=extra_create_args,
                    cancellation_token=cancellation_token,
                )
            except Exception as e:
                last_error = e
                if attempt >= self._config.max_retries or not _is_retryable(e, self._config):
                    raise
                retry_after = _get_retry_after(e)
                delay = _calculate_delay(attempt, self._config, retry_after)
                status_code = _get_status_code(e)
                trace_logger.warning(
                    "Chat completion attempt %d/%d failed with %s (status=%s). "
                    "Retrying in %.2f seconds.",
                    attempt + 1,
                    self._config.max_retries + 1,
                    type(e).__name__,
                    status_code,
                    delay,
                )
                await asyncio.sleep(delay)
        # Should not reach here, but satisfy type checker
        assert last_error is not None
        raise last_error

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
        return self._create_stream_with_retry(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )

    async def _create_stream_with_retry(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        last_error: Optional[Exception] = None
        for attempt in range(self._config.max_retries + 1):
            try:
                async for chunk in self._client.create_stream(
                    messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    json_output=json_output,
                    extra_create_args=extra_create_args,
                    cancellation_token=cancellation_token,
                ):
                    yield chunk
                return  # Stream completed successfully
            except Exception as e:
                last_error = e
                if attempt >= self._config.max_retries or not _is_retryable(e, self._config):
                    raise
                retry_after = _get_retry_after(e)
                delay = _calculate_delay(attempt, self._config, retry_after)
                status_code = _get_status_code(e)
                trace_logger.warning(
                    "Chat completion stream attempt %d/%d failed with %s (status=%s). "
                    "Retrying in %.2f seconds.",
                    attempt + 1,
                    self._config.max_retries + 1,
                    type(e).__name__,
                    status_code,
                    delay,
                )
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def close(self) -> None:
        await self._client.close()

    def actual_usage(self) -> RequestUsage:
        return self._client.actual_usage()

    def total_usage(self) -> RequestUsage:
        return self._client.total_usage()

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return self._client.count_tokens(messages, tools=tools)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return self._client.remaining_tokens(messages, tools=tools)

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        return self._client.capabilities  # type: ignore

    @property
    def model_info(self) -> ModelInfo:
        return self._client.model_info
