import copy
from typing import Dict, List, Optional, Tuple, Union

import pytest
from autogen_core import CacheStore
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
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
        return self._return_value

    def set(self, key: str, value: CHAT_CACHE_VALUE_TYPE) -> None:
        self._storage[key] = value

    def _to_config(self) -> BaseModel:
        """Dummy implementation for testing."""
        return BaseModel()

    @classmethod
    def _from_config(cls, _config: BaseModel) -> "MockCacheStore":
        """Dummy implementation for testing."""
        return cls()


def test_check_cache_redis_dict_deserialization_success():
    """Test _check_cache when Redis cache returns a dict that can be deserialized to CreateResult.
    This tests the core Redis deserialization fix where Redis returns serialized Pydantic
    models as dictionaries instead of the original objects.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a dict representation of CreateResult (like what Redis would return)
    create_result_dict = {
        "content": "test response from redis",
        "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
        "cached": False,
        "finish_reason": "stop",
    }

    # Mock cache store that returns a dict (simulating Redis behavior)
    mock_store = MockCacheStore(return_value=create_result_dict)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    assert cached_result is not None
    assert isinstance(cached_result, CreateResult)
    assert cached_result.content == "test response from redis"
    assert cache_key is not None


def test_check_cache_redis_dict_deserialization_failure():
    """Test _check_cache gracefully handles corrupted Redis data.
    This ensures the system degrades gracefully when Redis returns corrupted
    or invalid data that cannot be deserialized back to CreateResult.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create an invalid dict that cannot be deserialized to CreateResult
    invalid_dict = {"invalid_field": "invalid value", "missing_required_fields": True}

    # Mock cache store that returns an invalid dict
    mock_store = MockCacheStore(return_value=invalid_dict)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[1], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return None (cache miss) when deserialization fails
    assert cached_result is None
    assert cache_key is not None


def test_check_cache_redis_streaming_dict_deserialization():
    """Test _check_cache with Redis streaming data containing dicts that need deserialization.
    This tests the streaming scenario where Redis returns a list containing
    serialized CreateResult objects as dictionaries mixed with string chunks.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data()

    # Create a list with dicts that represent CreateResults (Redis streaming scenario)
    create_result_dict = {
        "content": "final streaming response from redis",
        "usage": {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
        "cached": False,
        "finish_reason": "stop",
    }

    cached_list = [
        "streaming chunk 1",
        create_result_dict,  # This dict needs deserialization
        "streaming chunk 2",
    ]

    # Mock cache store that returns the list with dicts (simulating Redis streaming)
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


def test_check_cache_redis_streaming_deserialization_failure():
    """Test _check_cache gracefully handles corrupted Redis streaming data.
    This ensures the system degrades gracefully when Redis returns streaming
    data with corrupted CreateResult dictionaries that cannot be deserialized.
    """
    _, prompts, system_prompt, replay_client, _ = get_test_data(num_messages=4)

    # Create a list with an invalid dict that will fail deserialization
    invalid_dict = {"invalid_field": "invalid value", "missing_required_fields": True}

    cached_list = [
        "streaming chunk 1",
        invalid_dict,  # This will fail deserialization
        "streaming chunk 2",
    ]

    # Mock cache store that returns the list with invalid dict
    mock_store = MockCacheStore(return_value=cached_list)
    cached_client = ChatCompletionCache(replay_client, mock_store)

    # Test _check_cache method directly using proper test data
    messages = [system_prompt, UserMessage(content=prompts[0], source="user")]
    cached_result, cache_key = cached_client._check_cache(messages, [], None, {})  # type: ignore

    # Should return None (cache miss) when deserialization fails
    assert cached_result is None
    assert cache_key is not None
