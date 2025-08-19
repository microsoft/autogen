import copy
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import pytest
from autogen_core import CacheStore
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.cache import CHAT_CACHE_VALUE_TYPE, ChatCompletionCache
from autogen_ext.models.replay import ReplayChatCompletionClient
from pydantic import BaseModel


def get_test_data(
    num_messages: int = 3,
) -> Tuple[list[str], list[str], SystemMessage, ChatCompletionClient, ChatCompletionCache]:
    responses = [f"This is dummy message number {i}" for i in range(num_messages)]
    prompts = [f"This is dummy prompt number {i}" for i in range(num_messages)]
    system_prompt = SystemMessage(content="This is a system prompt")
    replay_client = ReplayChatCompletionClient(responses)
    replay_client.set_cached_bool_value(False)
    cached_client = ChatCompletionCache(replay_client)

    return responses, prompts, system_prompt, replay_client, cached_client


@pytest.mark.asyncio
async def test_cache_basic_with_args() -> None:
    responses, prompts, system_prompt, _, cached_client = get_test_data()

    response0 = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert isinstance(response0, CreateResult)
    assert not response0.cached
    assert response0.content == responses[0]

    response1 = await cached_client.create([system_prompt, UserMessage(content=prompts[1], source="user")])
    assert not response1.cached
    assert response1.content == responses[1]

    # Cached output.
    response0_cached = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert isinstance(response0, CreateResult)
    assert response0_cached.cached
    assert response0_cached.content == responses[0]

    # Cache miss if args change.
    response2 = await cached_client.create(
        [system_prompt, UserMessage(content=prompts[0], source="user")], json_output=True
    )
    assert isinstance(response2, CreateResult)
    assert not response2.cached
    assert response2.content == responses[2]


@pytest.mark.asyncio
async def test_cache_structured_output_with_args() -> None:
    responses, prompts, system_prompt, _, cached_client = get_test_data(num_messages=4)

    class Answer(BaseModel):
        thought: str
        answer: str

    class Answer2(BaseModel):
        calculation: str
        answer: str

    response0 = await cached_client.create(
        [system_prompt, UserMessage(content=prompts[0], source="user")], json_output=Answer
    )
    assert isinstance(response0, CreateResult)
    assert not response0.cached
    assert response0.content == responses[0]

    response1 = await cached_client.create(
        [system_prompt, UserMessage(content=prompts[1], source="user")], json_output=Answer
    )
    assert not response1.cached
    assert response1.content == responses[1]

    # Cached output.
    response0_cached = await cached_client.create(
        [system_prompt, UserMessage(content=prompts[0], source="user")], json_output=Answer
    )
    assert isinstance(response0, CreateResult)
    assert response0_cached.cached
    assert response0_cached.content == responses[0]

    # Without the json_output argument, the cache should not be hit.
    response0 = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert isinstance(response0, CreateResult)
    assert not response0.cached
    assert response0.content == responses[2]

    # With a different output type, the cache should not be hit.
    response0 = await cached_client.create(
        [system_prompt, UserMessage(content=prompts[1], source="user")], json_output=Answer2
    )
    assert isinstance(response0, CreateResult)
    assert not response0.cached
    assert response0.content == responses[3]


@pytest.mark.asyncio
async def test_cache_model_and_count_api() -> None:
    _, prompts, system_prompt, replay_client, cached_client = get_test_data()

    assert replay_client.model_info == cached_client.model_info
    assert replay_client.capabilities == cached_client.capabilities

    messages: List[LLMMessage] = [system_prompt, UserMessage(content=prompts[0], source="user")]
    assert replay_client.count_tokens(messages) == cached_client.count_tokens(messages)
    assert replay_client.remaining_tokens(messages) == cached_client.remaining_tokens(messages)


@pytest.mark.asyncio
async def test_cache_token_usage() -> None:
    responses, prompts, system_prompt, replay_client, cached_client = get_test_data()

    response0 = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert isinstance(response0, CreateResult)
    assert not response0.cached
    assert response0.content == responses[0]
    actual_usage0 = copy.copy(cached_client.actual_usage())
    total_usage0 = copy.copy(cached_client.total_usage())

    response1 = await cached_client.create([system_prompt, UserMessage(content=prompts[1], source="user")])
    assert not response1.cached
    assert response1.content == responses[1]
    actual_usage1 = copy.copy(cached_client.actual_usage())
    total_usage1 = copy.copy(cached_client.total_usage())
    assert total_usage1.prompt_tokens > total_usage0.prompt_tokens
    assert total_usage1.completion_tokens > total_usage0.completion_tokens
    assert actual_usage1.prompt_tokens == actual_usage0.prompt_tokens
    assert actual_usage1.completion_tokens == actual_usage0.completion_tokens

    # Cached output.
    response0_cached = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert isinstance(response0, CreateResult)
    assert response0_cached.cached
    assert response0_cached.content == responses[0]
    total_usage2 = copy.copy(cached_client.total_usage())
    assert total_usage2.prompt_tokens == total_usage1.prompt_tokens
    assert total_usage2.completion_tokens == total_usage1.completion_tokens

    assert cached_client.actual_usage() == replay_client.actual_usage()
    assert cached_client.total_usage() == replay_client.total_usage()


@pytest.mark.asyncio
async def test_cache_create_stream() -> None:
    _, prompts, system_prompt, _, cached_client = get_test_data()

    original_streamed_results: List[Union[str, CreateResult]] = []
    async for completion in cached_client.create_stream(
        [system_prompt, UserMessage(content=prompts[0], source="user")]
    ):
        original_streamed_results.append(copy.copy(completion))
    total_usage0 = copy.copy(cached_client.total_usage())

    cached_completion_results: List[Union[str, CreateResult]] = []
    async for completion in cached_client.create_stream(
        [system_prompt, UserMessage(content=prompts[0], source="user")]
    ):
        cached_completion_results.append(copy.copy(completion))
    total_usage1 = copy.copy(cached_client.total_usage())

    assert total_usage1.prompt_tokens == total_usage0.prompt_tokens
    assert total_usage1.completion_tokens == total_usage0.completion_tokens

    for original, cached in zip(original_streamed_results, cached_completion_results, strict=False):
        if isinstance(original, str):
            assert original == cached
        elif isinstance(original, CreateResult) and isinstance(cached, CreateResult):
            assert original.content == cached.content
            assert cached.cached
            assert not original.cached
        else:
            raise ValueError(f"Unexpected types : {type(original)} and {type(cached)}")

    # test serialization
    # cached_client_config = cached_client.dump_component()
    # loaded_client = ChatCompletionCache.load_component(cached_client_config)
    # assert loaded_client.client == cached_client.client


class MockCacheStore(CacheStore[CHAT_CACHE_VALUE_TYPE]):
    """Mock cache store for testing deserialization scenarios."""

    def __init__(self, return_value: Optional[CHAT_CACHE_VALUE_TYPE] = None) -> None:
        self._return_value = return_value
        self._storage: Dict[str, CHAT_CACHE_VALUE_TYPE] = {}

    def get(self, key: str, default: Optional[CHAT_CACHE_VALUE_TYPE] = None) -> Optional[CHAT_CACHE_VALUE_TYPE]:
        return self._return_value  # type: ignore

    def set(self, key: str, value: CHAT_CACHE_VALUE_TYPE) -> None:
        self._storage[key] = value

    def _to_config(self) -> BaseModel:
        """Dummy implementation for testing."""
        return BaseModel()

    @classmethod
    def _from_config(cls, _config: BaseModel) -> "MockCacheStore":
        """Dummy implementation for testing."""
        return cls()


def test_check_cache_redis_dict_deserialization_success() -> None:
    """Test _check_cache when Redis cache returns a dict that can be deserialized to CreateResult.
    This tests the core Redis deserialization fix where Redis returns serialized Pydantic
    models as dictionaries instead of the original objects.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a CreateResult instance (simulating deserialized Redis data)
    create_result = CreateResult(
        content="test response from redis",
        usage=RequestUsage(prompt_tokens=15, completion_tokens=8),
        cached=False,
        finish_reason="stop",
    )

    # Mock cache store that returns a CreateResult (simulating Redis behavior)
    mock_store = MockCacheStore(return_value=create_result)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    assert cached_result is not None
    assert isinstance(cached_result, CreateResult)
    assert cached_result.content == "test response from redis"
    assert cache_key is not None


def test_check_cache_redis_dict_deserialization_failure() -> None:
    """Test _check_cache gracefully handles corrupted Redis data.
    This ensures the system degrades gracefully when Redis returns corrupted
    or invalid data that cannot be deserialized back to CreateResult.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Mock cache store that returns None (simulating deserialization failure)
    mock_store = MockCacheStore(return_value=None)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[1], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return None (cache miss) when deserialization fails
    assert cached_result is None
    assert cache_key is not None


def test_check_cache_redis_streaming_dict_deserialization() -> None:
    """Test _check_cache with Redis streaming data containing dicts that need deserialization.
    This tests the streaming scenario where Redis returns a list containing
    serialized CreateResult objects as dictionaries mixed with string chunks.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a list with CreateResult objects mixed with strings (streaming scenario)
    create_result = CreateResult(
        content="final streaming response from redis",
        usage=RequestUsage(prompt_tokens=12, completion_tokens=6),
        cached=False,
        finish_reason="stop",
    )

    cached_list: List[Union[str, CreateResult]] = [
        "streaming chunk 1",
        create_result,  # Proper CreateResult object
        "streaming chunk 2",
    ]

    # Mock cache store that returns the list with CreateResults (simulating Redis streaming)
    mock_store = MockCacheStore(return_value=cached_list)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[2], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    assert cached_result is not None
    assert isinstance(cached_result, list)
    assert len(cached_result) == 3
    assert cached_result[0] == "streaming chunk 1"
    assert isinstance(cached_result[1], CreateResult)
    assert cached_result[1].content == "final streaming response from redis"
    assert cached_result[2] == "streaming chunk 2"
    assert cache_key is not None


def test_check_cache_redis_streaming_deserialization_failure() -> None:
    """Test _check_cache gracefully handles corrupted Redis streaming data.
    This ensures the system degrades gracefully when Redis returns streaming
    data with corrupted CreateResult dictionaries that cannot be deserialized.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data(num_messages=4)

    # Mock cache store that returns None (simulating deserialization failure)
    mock_store = MockCacheStore(return_value=None)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return None (cache miss) when deserialization fails
    assert cached_result is None
    assert cache_key is not None


def test_check_cache_dict_reconstruction_success() -> None:
    """Test _check_cache successfully reconstructs CreateResult from a dict.
    This tests the line: cached_result = CreateResult.model_validate(cached_result)
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a dict that can be successfully validated as CreateResult
    valid_dict = {
        "content": "reconstructed response",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "cached": False,
        "finish_reason": "stop",
    }

    # Create a MockCacheStore that returns the dict directly (simulating Redis)
    mock_store = MockCacheStore(return_value=cast(Any, valid_dict))
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should successfully reconstruct the CreateResult from dict
    assert cached_result is not None
    assert isinstance(cached_result, CreateResult)
    assert cached_result.content == "reconstructed response"
    assert cache_key is not None


def test_check_cache_dict_reconstruction_failure() -> None:
    """Test _check_cache handles ValidationError when dict cannot be reconstructed.
    This tests the except ValidationError block for single dicts.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create an invalid dict that will fail CreateResult validation
    invalid_dict = {
        "invalid_field": "value",
        "missing_required_fields": True,
    }

    # Create a MockCacheStore that returns the invalid dict
    mock_store = MockCacheStore(return_value=cast(Any, invalid_dict))
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return None (cache miss) when reconstruction fails
    assert cached_result is None
    assert cache_key is not None


def test_check_cache_list_reconstruction_success() -> None:
    """Test _check_cache successfully reconstructs CreateResult objects from dicts in a list.
    This tests the line: reconstructed_list.append(CreateResult.model_validate(item))
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a list with valid dicts that can be reconstructed
    valid_dict1 = {
        "content": "first result",
        "usage": {"prompt_tokens": 8, "completion_tokens": 3},
        "cached": False,
        "finish_reason": "stop",
    }
    valid_dict2 = {
        "content": "second result",
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
        "cached": False,
        "finish_reason": "stop",
    }

    cached_list = [
        "streaming chunk 1",
        valid_dict1,
        "streaming chunk 2",
        valid_dict2,
    ]

    # Create a MockCacheStore that returns the list with dicts
    mock_store = MockCacheStore(return_value=cast(Any, cached_list))
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should successfully reconstruct the list with CreateResult objects
    assert cached_result is not None
    assert isinstance(cached_result, list)
    assert len(cached_result) == 4
    assert cached_result[0] == "streaming chunk 1"
    assert isinstance(cached_result[1], CreateResult)
    assert cached_result[1].content == "first result"
    assert cached_result[2] == "streaming chunk 2"
    assert isinstance(cached_result[3], CreateResult)
    assert cached_result[3].content == "second result"
    assert cache_key is not None


def test_check_cache_list_reconstruction_failure() -> None:
    """Test _check_cache handles ValidationError when list contains invalid dicts.
    This tests the except ValidationError block for lists.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a list with an invalid dict that will fail validation
    invalid_dict = {
        "invalid_field": "value",
        "missing_required": True,
    }

    cached_list = [
        "streaming chunk 1",
        invalid_dict,  # This will cause ValidationError
        "streaming chunk 2",
    ]

    # Create a MockCacheStore that returns the list with invalid dict
    mock_store = MockCacheStore(return_value=cast(Any, cached_list))
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return None (cache miss) when list reconstruction fails
    assert cached_result is None
    assert cache_key is not None


def test_check_cache_already_correct_type() -> None:
    """Test _check_cache returns data as-is when it's already the correct type.
    This tests the final return path when no reconstruction is needed.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a proper CreateResult object (already correct type)
    create_result = CreateResult(
        content="already correct type",
        usage=RequestUsage(prompt_tokens=15, completion_tokens=8),
        cached=False,
        finish_reason="stop",
    )

    # Create a MockCacheStore that returns the proper type
    mock_store = MockCacheStore(return_value=create_result)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return the same object without reconstruction
    assert cached_result is not None
    assert cached_result is create_result  # Same object reference
    assert isinstance(cached_result, CreateResult)
    assert cached_result.content == "already correct type"
    assert cache_key is not None


@pytest.mark.asyncio
async def test_redis_streaming_cache_integration() -> None:
    """Integration test for Redis streaming cache scenario.
    This test covers the original streaming cache issues:
    1. Cache is stored after streaming completes (not before)
    2. Redis cache properly handles lists containing CreateResult objects
    3. ChatCompletionCache properly reconstructs CreateResult from Redis dicts
    """
    from unittest.mock import MagicMock

    # Skip this test if redis is not available
    pytest.importorskip("redis")

    from autogen_ext.cache_store.redis import RedisStore

    # Use standardized test data
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Mock Redis instance to control what gets stored/retrieved
    redis_instance = MagicMock()
    redis_store = RedisStore[CHAT_CACHE_VALUE_TYPE](redis_instance)

    # Create the cached client with Redis store
    cached_client = ChatCompletionCache(replay_client, redis_store)

    # Simulate first streaming call (should cache after completion)
    first_stream_results: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[0], source="user")]):
        first_stream_results.append(copy.copy(chunk))

    # Verify Redis set was called with the complete streaming results
    redis_instance.set.assert_called_once()
    call_args = redis_instance.set.call_args
    serialized_data = call_args[0][1]

    # Verify the serialized data represents the complete stream
    assert isinstance(serialized_data, bytes)
    import json

    deserialized: Any = json.loads(serialized_data.decode("utf-8"))
    assert isinstance(deserialized, list)
    deserialized_list: List[Any] = cast(List[Any], deserialized)
    # Should contain both string chunks and final CreateResult (as dict)
    assert len(deserialized_list) > 0

    # Reset the mock for the second call
    redis_instance.reset_mock()

    # Configure Redis to return the serialized data (simulating cache hit)
    redis_instance.get.return_value = serialized_data

    # Second streaming call should hit the cache
    second_stream_results: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[0], source="user")]):
        second_stream_results.append(copy.copy(chunk))

    # Verify Redis get was called but set was not (cache hit)
    redis_instance.get.assert_called_once()
    redis_instance.set.assert_not_called()

    # Verify both streams have the same content
    assert len(first_stream_results) == len(second_stream_results)

    # Verify cached results are marked as cached
    for first, second in zip(first_stream_results, second_stream_results, strict=True):
        if isinstance(first, CreateResult) and isinstance(second, CreateResult):
            assert not first.cached  # First call should not be cached
            assert second.cached  # Second call should be cached
            assert first.content == second.content
        elif isinstance(first, str) and isinstance(second, str):
            assert first == second
        else:
            pytest.fail(f"Unexpected chunk types: {type(first)}, {type(second)}")


@pytest.mark.asyncio
async def test_cache_cross_compatibility_create_to_stream() -> None:
    """Test that create() cache can be used by create_stream() call.
    This tests the scenario where:
    1. User calls create() - stores CreateResult
    2. User calls create_stream() with same inputs - should get cache hit and yield the CreateResult
    """
    responses, prompts, system_prompt, _, cached_client = get_test_data()

    # First call: create() - should cache a CreateResult
    create_result = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert isinstance(create_result, CreateResult)
    assert not create_result.cached
    assert create_result.content == responses[0]

    # Second call: create_stream() with same inputs - should hit the cache
    stream_results: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[0], source="user")]):
        stream_results.append(copy.copy(chunk))

    # Should yield exactly one item (the cached CreateResult)
    assert len(stream_results) == 1
    assert isinstance(stream_results[0], CreateResult)
    assert stream_results[0].cached  # Should be marked as cached
    assert stream_results[0].content == responses[0]

    # Verify no additional API calls were made (cache hit)
    initial_usage = cached_client.total_usage()

    # Third call: create_stream() again - should still hit cache
    stream_results_2: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[0], source="user")]):
        stream_results_2.append(copy.copy(chunk))

    # Usage should be the same (no new API calls)
    assert cached_client.total_usage().prompt_tokens == initial_usage.prompt_tokens
    assert cached_client.total_usage().completion_tokens == initial_usage.completion_tokens


@pytest.mark.asyncio
async def test_cache_cross_compatibility_stream_to_create() -> None:
    """Test that create_stream() cache can be used by create() call.
    This tests the scenario where:
    1. User calls create_stream() - stores List[Union[str, CreateResult]]
    2. User calls create() with same inputs - should get cache hit and return the final CreateResult
    """
    _, prompts, system_prompt, _, cached_client = get_test_data()

    # First call: create_stream() - should cache a List[Union[str, CreateResult]]
    first_stream_results: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[0], source="user")]):
        first_stream_results.append(copy.copy(chunk))

    # Verify we got streaming results
    assert len(first_stream_results) > 0
    final_create_result = None
    for item in first_stream_results:
        if isinstance(item, CreateResult):
            final_create_result = item
            break

    assert final_create_result is not None
    assert not final_create_result.cached  # First call should not be cached

    # Second call: create() with same inputs - should hit the streaming cache
    create_result = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])

    assert isinstance(create_result, CreateResult)
    assert create_result.cached  # Should be marked as cached
    assert create_result.content == final_create_result.content

    # Verify no additional API calls were made (cache hit)
    initial_usage = cached_client.total_usage()

    # Third call: create() again - should still hit cache
    create_result_2 = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])

    # Usage should be the same (no new API calls)
    assert cached_client.total_usage().prompt_tokens == initial_usage.prompt_tokens
    assert cached_client.total_usage().completion_tokens == initial_usage.completion_tokens
    assert create_result_2.cached


@pytest.mark.asyncio
async def test_cache_cross_compatibility_mixed_sequence() -> None:
    """Test mixed sequence of create() and create_stream() calls with caching.
    This tests a realistic scenario with multiple interleaved calls:
    create() → create_stream() → create() → create_stream()
    """
    responses, prompts, system_prompt, _, cached_client = get_test_data(num_messages=4)

    # Call 1: create() with prompt[0] - should make API call
    result1 = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])
    assert not result1.cached
    assert result1.content == responses[0]
    usage_after_1 = copy.copy(cached_client.total_usage())

    # Call 2: create_stream() with prompt[0] - should hit cache from call 1
    stream1_results: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[0], source="user")]):
        stream1_results.append(chunk)

    assert len(stream1_results) == 1  # Should just yield the cached CreateResult
    assert isinstance(stream1_results[0], CreateResult)
    assert stream1_results[0].cached
    usage_after_2 = copy.copy(cached_client.total_usage())
    # No new API call should have been made
    assert usage_after_2.prompt_tokens == usage_after_1.prompt_tokens

    # Call 3: create_stream() with prompt[1] - should make new API call
    stream2_results: List[Union[str, CreateResult]] = []
    async for chunk in cached_client.create_stream([system_prompt, UserMessage(content=prompts[1], source="user")]):
        stream2_results.append(copy.copy(chunk))

    # Should have made a new API call
    usage_after_3 = copy.copy(cached_client.total_usage())
    assert usage_after_3.prompt_tokens > usage_after_2.prompt_tokens

    # Find the final CreateResult
    final_result = None
    for item in stream2_results:
        if isinstance(item, CreateResult):
            final_result = item
            break
    assert final_result is not None
    assert not final_result.cached

    # Call 4: create() with prompt[1] - should hit cache from call 3
    result4 = await cached_client.create([system_prompt, UserMessage(content=prompts[1], source="user")])
    assert result4.cached
    assert result4.content == final_result.content
    usage_after_4 = copy.copy(cached_client.total_usage())
    # No new API call should have been made
    assert usage_after_4.prompt_tokens == usage_after_3.prompt_tokens


@pytest.mark.asyncio
async def test_cache_streaming_list_without_create_result() -> None:
    """Test edge case where streaming cache contains only strings (no CreateResult).
    This could happen if streaming was interrupted or in unusual scenarios.
    The create() method should handle this gracefully by falling through to make a real API call.
    """
    responses, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a mock cache store that returns a list with only strings (no CreateResult)
    string_only_list: List[Union[str, CreateResult]] = ["Hello", " world", "!"]
    mock_store = MockCacheStore(return_value=string_only_list)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Call create() - should fall through and make API call since no CreateResult in cached list
    result = await cached_client.create([system_prompt, UserMessage(content=prompts[0], source="user")])

    assert isinstance(result, CreateResult)
    assert not result.cached  # Should be from real API call, not cache
    assert result.content == responses[0]
