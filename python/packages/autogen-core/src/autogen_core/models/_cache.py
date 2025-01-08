import hashlib
import json
import warnings
from typing import Any, AsyncGenerator, List, Mapping, Optional, Sequence, Union, cast

from .._cache_store import CacheStore
from .._cancellation_token import CancellationToken
from ..tools import Tool, ToolSchema
from ._model_client import (
    ChatCompletionClient,
    ModelCapabilities,  # type: ignore
    ModelInfo,
)
from ._types import (
    CreateResult,
    LLMMessage,
    RequestUsage,
)


class ChatCompletionCache(ChatCompletionClient):
    """
    A wrapper around a ChatCompletionClient that caches creation results from an underlying client.
    Cache hits do not contribute to token usage of the original client.
    """

    def __init__(self, client: ChatCompletionClient, store: CacheStore):
        """
        Initialize a new ChatCompletionCache.

        First initialize (for eg) a Redis store:

        ```python
        import redis

        redis_client = redis.Redis(host="localhost", port=6379, db=0)
        ```

        or diskcache store:

        ```python
        from diskcache import Cache

        diskcache_client = Cache("/tmp/diskcache")
        ```

        Then initialize the ChatCompletionCache with the store:

        ```python
        from autogen_core.models import ChatCompletionCache
        from autogen_ext.models import OpenAIChatCompletionClient

        # Original client
        client = OpenAIChatCompletionClient(...)

        # Cached version
        cached_client = ChatCompletionCache(client, redis_client)
        ```

        Args:
            client (ChatCompletionClient): The original ChatCompletionClient to wrap.
            store (CacheStore): A store object that implements get and set methods.
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
    ) -> tuple[Optional[Union[CreateResult, List[Union[str, CreateResult]]]], str]:
        """
        Helper function to check the cache for a result.
        Returns a tuple of (cached_result, cache_key).
        """

        data = {
            "messages": [message.model_dump() for message in messages],
            "tools": [(tool.schema if isinstance(tool, Tool) else tool) for tool in tools],
            "json_output": json_output,
            "extra_create_args": extra_create_args,
        }
        serialized_data = json.dumps(data, sort_keys=True)
        cache_key = hashlib.sha256(serialized_data.encode()).hexdigest()

        cached_result = cast(Optional[CreateResult], self.store.get(cache_key))
        if cached_result is not None:
            return cached_result, cache_key

        return None, cache_key

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """
        Cached version of ChatCompletionClient.create.
        If the result of a call to create has been cached, it will be returned immediately
        without invoking the underlying client.

        NOTE: cancellation_token is ignored for cached results.
        """
        cached_result, cache_key = self._check_cache(messages, tools, json_output, extra_create_args)
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
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """
        Cached version of ChatCompletionClient.create_stream.
        If the result of a call to create_stream has been cached, it will be returned
        without streaming from the underlying client.

        NOTE: cancellation_token is ignored for cached results.
        """

        async def _generator() -> AsyncGenerator[Union[str, CreateResult], None]:
            cached_result, cache_key = self._check_cache(
                messages,
                tools,
                json_output,
                extra_create_args,
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
                cancellation_token=cancellation_token,
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
