from __future__ import annotations

from random import randint
from typing import Any, AsyncGenerator, Mapping, Optional, Sequence, Union

from autogen_core.base import CancellationToken
from autogen_core.components.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    RequestUsage,
)
from autogen_core.components.tools import Tool, ToolSchema


class ReplayChatCompletionClient:
    """A mock chat completion client that replays predefined responses."""

    __protocol__: ChatCompletionClient

    # TODO: Support FunctionCall in responses
    # TODO: Support logprobs in Responses
    # TODO: Support model ccapabilities
    def __init__(
        self,
        chat_completions: Sequence[Union[str, CreateResult]],
    ):
        """Initialize with a list of chat completions to replay.

        Args:
            chat_completions: List of responses to return. Each response can be:
                - A string (will be wrapped in a completion response)
                - A CreateResult object
        """
        self.chat_completions = list(chat_completions)
        self._cur_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self.provided_message_count = len(self.chat_completions)
        # self._model_capabilities = model_capabilities

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Return the next completion from the list."""
        if not self.chat_completions:
            raise ValueError("No more mock responses available")

        response = self.chat_completions.pop(0)
        if isinstance(response, str):
            # TODO: Verify the intended use case of these two
            self._cur_usage = self._generate_fake_usage()
            response = CreateResult(finish_reason="stop", content=response, usage=self._cur_usage, cached=True)
        else:
            self._cur_usage = response.usage

        self._update_total_usage()
        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Return the next completion as a stream."""
        if not self.chat_completions:
            raise ValueError("No more mock responses available")

        response = self.chat_completions.pop(0)
        if isinstance(response, str):
            # For strings, split by spaces to simulate streaming tokens
            words = response.split()
            for i, word in enumerate(words):
                self._cur_usage = self._generate_fake_usage()
                if i < len(words) - 1:
                    yield word + " "
                else:
                    yield word
        else:
            self._cur_usage = response.usage
            self._update_total_usage()
            yield response

    def actual_usage(self) -> RequestUsage:
        """Return the actual usage for the last request."""
        return self._cur_usage

    def total_usage(self) -> RequestUsage:
        """Return the total usage across all requests."""
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        """Mock token counting - returns a fixed number."""
        return 100

    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        """Mock remaining tokens - returns a fixed number."""
        return 1000

    def _generate_fake_usage(self) -> RequestUsage:
        # TODO: This probably should take the content as input to be more realistic ...
        return RequestUsage(prompt_tokens=randint(1, 10), completion_tokens=randint(1, 10))

    def _update_total_usage(self) -> None:
        self._total_usage.completion_tokens += self._cur_usage.completion_tokens
        self._total_usage.prompt_tokens += self._cur_usage.prompt_tokens

    # @property
    # def capabilities(self) -> ModelCapabilities:
    #     """Return mock capabilities."""
    #     return self._model_capabilities
