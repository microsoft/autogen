import hashlib
import json
import warnings
from typing import Any, AsyncGenerator, List, Literal, Mapping, Optional, Sequence, Union

from autogen_core import CacheStore, CancellationToken, Component, ComponentModel, InMemoryStore
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel, ValidationError
from typing_extensions import Self

CHAT_CACHE_VALUE_TYPE = Union[CreateResult, List[Union[str, CreateResult]]]


class ChatCompletionCacheConfig(BaseModel):
    """ """

    client: ComponentModel
    store: Optional[ComponentModel] = None


class ChatCompletionCache(ChatCompletionClient, Component[ChatCompletionCacheConfig]):
    """
    A wrapper around a :class:`~autogen_ext.models.cache.ChatCompletionClient` that caches
    creation results from an underlying client.
    Cache hits do not contribute to token usage of the original client.

    Typical Usage:

    Lets use caching on disk with `openai` client as an example.
    First install `autogen-ext` with the required packages:

    .. code-block:: bash

        pip install -U "autogen-ext[openai, diskcache]"

    And use it as:

    .. code-block:: python

        import asyncio
        import tempfile

        from autogen_core.models import UserMessage
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.models.cache import ChatCompletionCache, CHAT_CACHE_VALUE_TYPE
        from autogen_ext.cache_store.diskcache import DiskCacheStore
        from diskcache import Cache


        async def main():
            with tempfile.TemporaryDirectory() as tmpdirname:
                # Initialize the original client
                openai_model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # Then initialize the CacheStore, in this case with diskcache.Cache.
                # You can also use redis like:
                # from autogen_ext.cache_store.redis import RedisStore
                # import redis
                # redis_instance = redis.Redis()
                # cache_store = RedisCacheStore[CHAT_CACHE_VALUE_TYPE](redis_instance)
                cache_store = DiskCacheStore[CHAT_CACHE_VALUE_TYPE](Cache(tmpdirname))
                cache_client = ChatCompletionCache(openai_model_client, cache_store)

                response = await cache_client.create([UserMessage(content="Hello, how are you?", source="user")])
                print(response)  # Should print response from OpenAI
                response = await cache_client.create([UserMessage(content="Hello, how are you?", source="user")])
                print(response)  # Should print cached response


        asyncio.run(main())

    For Redis caching:

    .. code-block:: python

        import asyncio

        from autogen_core.models import UserMessage
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.models.cache import ChatCompletionCache, CHAT_CACHE_VALUE_TYPE
        from autogen_ext.cache_store.redis import RedisStore
        import redis


        async def main():
            # Initialize the original client
            openai_model_client = OpenAIChatCompletionClient(model="gpt-4o")

            # Initialize Redis cache store
            redis_instance = redis.Redis()
            cache_store = RedisStore[CHAT_CACHE_VALUE_TYPE](redis_instance)
            cache_client = ChatCompletionCache(openai_model_client, cache_store)

            response = await cache_client.create([UserMessage(content="Hello, how are you?", source="user")])
            print(response)  # Should print response from OpenAI
            response = await cache_client.create([UserMessage(content="Hello, how are you?", source="user")])
            print(response)  # Should print cached response


        asyncio.run(main())

    For streaming with Redis caching:

    .. code-block:: python

        import asyncio

        from autogen_core.models import UserMessage, CreateResult
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.models.cache import ChatCompletionCache, CHAT_CACHE_VALUE_TYPE
        from autogen_ext.cache_store.redis import RedisStore
        import redis


        async def main():
            # Initialize the original client
            openai_model_client = OpenAIChatCompletionClient(model="gpt-4o")

            # Initialize Redis cache store
            redis_instance = redis.Redis()
            cache_store = RedisStore[CHAT_CACHE_VALUE_TYPE](redis_instance)
            cache_client = ChatCompletionCache(openai_model_client, cache_store)

            # First streaming call
            async for chunk in cache_client.create_stream(
                [UserMessage(content="List all countries in Africa", source="user")]
            ):
                if isinstance(chunk, CreateResult):
                    print("\\n")
                    print("Cached: ", chunk.cached)  # Should print False
                else:
                    print(chunk, end="")

            # Second streaming call (cached)
            async for chunk in cache_client.create_stream(
                [UserMessage(content="List all countries in Africa", source="user")]
            ):
                if isinstance(chunk, CreateResult):
                    print("\\n")
                    print("Cached: ", chunk.cached)  # Should print True
                else:
                    print(chunk, end="")


        asyncio.run(main())

    You can now use the `cached_client` as you would the original client, but with caching enabled.

    Args:
        client (ChatCompletionClient): The original ChatCompletionClient to wrap.
        store (CacheStore): A store object that implements get and set methods.
            The user is responsible for managing the store's lifecycle & clearing it (if needed).
            Defaults to using in-memory cache.
    """

    component_type = "chat_completion_cache"
    component_provider_override = "autogen_ext.models.cache.ChatCompletionCache"
    component_config_schema = ChatCompletionCacheConfig

    def __init__(
        self,
        client: ChatCompletionClient,
        store: Optional[CacheStore[CHAT_CACHE_VALUE_TYPE]] = None,
    ):
        self.client = client
        self.store = store or InMemoryStore[CHAT_CACHE_VALUE_TYPE]()

    def _check_cache(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema],
        json_output: Optional[bool | type[BaseModel]],
        extra_create_args: Mapping[str, Any],
    ) -> tuple[Optional[Union[CreateResult, List[Union[str, CreateResult]]]], str]:
        """
        Helper function to check the cache for a result.
        Returns a tuple of (cached_result, cache_key).
        """

        json_output_data: str | bool | None = None

        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            json_output_data = json.dumps(json_output.model_json_schema())
        elif isinstance(json_output, bool):
            json_output_data = json_output

        data = {
            "messages": [message.model_dump() for message in messages],
            "tools": [(tool.schema if isinstance(tool, Tool) else tool) for tool in tools],
            "json_output": json_output_data,
            "extra_create_args": extra_create_args,
        }
        serialized_data = json.dumps(data, sort_keys=True)
        cache_key = hashlib.sha256(serialized_data.encode()).hexdigest()

        cached_result = self.store.get(cache_key)
        if cached_result is not None:
            # Handle case where cache store returns dict instead of CreateResult (e.g., Redis)
            if isinstance(cached_result, dict):
                try:
                    cached_result = CreateResult.model_validate(cached_result)
                except ValidationError:
                    # If reconstruction fails, treat as cache miss
                    return None, cache_key
            elif isinstance(cached_result, list):
                # Handle streaming results - reconstruct CreateResult instances from dicts
                try:
                    reconstructed_list: List[Union[str, CreateResult]] = []
                    for item in cached_result:
                        if isinstance(item, dict):
                            reconstructed_list.append(CreateResult.model_validate(item))
                        else:
                            reconstructed_list.append(item)
                    cached_result = reconstructed_list
                except ValidationError:
                    # If reconstruction fails, treat as cache miss
                    return None, cache_key
            # If it's already the right type (CreateResult or list), return as-is
            return cached_result, cache_key

        return None, cache_key

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
        """
        Cached version of ChatCompletionClient.create.
        If the result of a call to create has been cached, it will be returned immediately
        without invoking the underlying client.

        NOTE: cancellation_token is ignored for cached results.
        """
        cached_result, cache_key = self._check_cache(messages, tools, json_output, extra_create_args)
        if cached_result is not None:
            if isinstance(cached_result, CreateResult):
                # Cache hit from previous non-streaming call
                cached_result.cached = True
                return cached_result
            elif isinstance(cached_result, list):
                # Cache hit from previous streaming call - extract the final CreateResult
                for item in reversed(cached_result):
                    if isinstance(item, CreateResult):
                        item.cached = True
                        return item
                # If no CreateResult found in list, fall through to make actual call

        result = await self.client.create(
            messages,
            tools=tools,
            json_output=json_output,
            tool_choice=tool_choice,
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
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
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
            if cached_result is not None:
                if isinstance(cached_result, list):
                    # Cache hit from previous streaming call
                    for result in cached_result:
                        if isinstance(result, CreateResult):
                            result.cached = True
                        yield result
                    return
                elif isinstance(cached_result, CreateResult):
                    # Cache hit from previous non-streaming call - convert to streaming format
                    cached_result.cached = True

                    # If content is a non-empty string, yield it as a streaming chunk first
                    if isinstance(cached_result.content, str) and cached_result.content:
                        yield cached_result.content

                    yield cached_result
                    return

            result_stream = self.client.create_stream(
                messages,
                tools=tools,
                json_output=json_output,
                tool_choice=tool_choice,
                extra_create_args=extra_create_args,
                cancellation_token=cancellation_token,
            )

            output_results: List[Union[str, CreateResult]] = []

            async for result in result_stream:
                output_results.append(result)
                yield result

            # Store the complete results only after streaming is finished
            self.store.set(cache_key, output_results)

        return _generator()

    async def close(self) -> None:
        await self.client.close()

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

    def _to_config(self) -> ChatCompletionCacheConfig:
        return ChatCompletionCacheConfig(
            client=self.client.dump_component(),
            store=self.store.dump_component() if not isinstance(self.store, InMemoryStore) else None,
        )

    @classmethod
    def _from_config(cls, config: ChatCompletionCacheConfig) -> Self:
        client = ChatCompletionClient.load_component(config.client)
        store: Optional[CacheStore[CHAT_CACHE_VALUE_TYPE]] = (
            CacheStore.load_component(config.store) if config.store else InMemoryStore()
        )
        return cls(client=client, store=store)
