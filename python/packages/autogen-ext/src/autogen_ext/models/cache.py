import hashlib
import json
import warnings
from typing import Any, AsyncGenerator, List, Mapping, Optional, Sequence, Union, cast

from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelInfo,
    RequestUsage,
)
from autogen_core.store import AbstractStore
from autogen_core.tools import Tool, ToolSchema


class ChatCompletionCache(ChatCompletionClient):
    """
    A wrapper around a ChatCompletionClient that caches creation results from an underlying client.
    Cache hits do not contribute to token usage of the original client.
    """

    def __init__(self, client: ChatCompletionClient, store: AbstractStore):
        """
        Initialize a new ChatCompletionCache.

        Args:
            client (ChatCompletionClient): The original ChatCompletionClient to wrap.
            store (AbstractStore): A store object that implements get and set methods.
                The user is responsible for managing the store's lifecycle & clearing it (if needed).
        """
        self.client = client
        self.store = store

    def _check_cache(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema],
        json_output: Optional[bool],
        extra_create_args: Mapping[str, Any],
        force_cache: bool,
        force_client: bool,
    ) -> tuple[Optional[Union[CreateResult, List[Union[str, CreateResult]]]], str]:
        """
        Helper function to check the cache for a result.
        Returns a tuple of (cached_result, cache_key).
        cached_result is None if the cache is empty or force_client is True.
        Raises an error if there is a cache miss and force_cache is True.
        """
        if force_client and force_cache:
            raise ValueError("force_cache and force_client cannot both be True")

        data = {
            "messages": [message.model_dump() for message in messages],
            "tools": [(tool.schema if isinstance(tool, Tool) else tool) for tool in tools],
            "json_output": json_output,
            "extra_create_args": extra_create_args,
        }
        serialized_data = json.dumps(data, sort_keys=True)
        cache_key = hashlib.sha256(serialized_data.encode()).hexdigest()

        if not force_client:
            cached_result = cast(Optional[CreateResult], self.store.get(cache_key))
            if cached_result is not None:
                return cached_result, cache_key
            elif force_cache:
                raise ValueError("Encountered cache miss for force_cache request")

        return None, cache_key

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        force_cache: bool = False,
        force_client: bool = False,
    ) -> CreateResult:
        """
        Cached version of ChatCompletionClient.create.
        If the result of a call to create has been cached, it will be returned immediately
        without invoking the underlying client.

        NOTE: cancellation_token is ignored for cached results.

        Additional parameters:
        - force_cache: If True, the cache will be used and an error will be raised if a result is unavailable.
        - force_client: If True, the cache will be bypassed and the underlying client will be called.
        """
        cached_result, cache_key = self._check_cache(
            messages, tools, json_output, extra_create_args, force_cache, force_client
        )
        if cached_result:
            assert isinstance(cached_result, CreateResult)
            cached_result.cached = True
            return cached_result

        result = await self.client.create(
            messages,
            tools=tools,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )
        self.store.set(cache_key, result)
        return result

    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        force_cache: bool = False,
        force_client: bool = False,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """
        Cached version of ChatCompletionClient.create_stream.
        If the result of a call to create_stream has been cached, it will be returned
        without streaming from the underlying client.

        NOTE: cancellation_token is ignored for cached results.

        Additional parameters:
        - force_cache: If True, the cache will be used and an error will be raised if a result is unavailable.
        - force_client: If True, the cache will be bypassed and the underlying client will be called.
        """

        if force_client and force_cache:
            raise ValueError("force_cache and force_client cannot both be True")

        async def _generator() -> AsyncGenerator[Union[str, CreateResult], None]:
            cached_result, cache_key = self._check_cache(
                messages, tools, json_output, extra_create_args, force_cache, force_client
            )
            if cached_result:
                assert isinstance(cached_result, list)
                for result in cached_result:
                    if isinstance(result, CreateResult):
                        result.cached = True
                    yield result
                return

            result_stream = self.client.create_stream(
                messages,
                tools=tools,
                json_output=json_output,
                extra_create_args=extra_create_args,
            )

            output_results: List[Union[str, CreateResult]] = []
            self.store.set(cache_key, output_results)

            async for result in result_stream:
                output_results.append(result)
                yield result

        return _generator()

    def actual_usage(self) -> RequestUsage:
        return self.client.actual_usage()

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return self.client.count_tokens(messages, tools=tools)

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        warnings.warn("capabilities is deprecated, use model_info instead", DeprecationWarning, stacklevel=2)
        return self.client.capabilities

    @property
    def model_info(self) -> ModelInfo:
        return self.client.model_info

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return self.client.remaining_tokens(messages, tools=tools)

    def total_usage(self) -> RequestUsage:
        return self.client.total_usage()
