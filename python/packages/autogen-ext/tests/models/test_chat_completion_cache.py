import copy
from typing import List, Tuple, Union

import pytest
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.cache import ChatCompletionCache
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
