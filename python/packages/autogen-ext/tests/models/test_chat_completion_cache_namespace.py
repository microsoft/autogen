import hashlib
import json

import pytest
from autogen_core import InMemoryStore
from autogen_core.models import CreateResult, UserMessage
from autogen_ext.models.cache import CHAT_CACHE_VALUE_TYPE, ChatCompletionCache
from autogen_ext.models.replay import ReplayChatCompletionClient


async def complete(client: ChatCompletionCache, streaming: bool) -> CreateResult:
    messages = [UserMessage(content="same prompt", source="user")]
    if not streaming:
        return await client.create(messages)
    result: CreateResult | None = None
    async for chunk in client.create_stream(messages):
        if isinstance(chunk, CreateResult):
            result = chunk
    assert result is not None
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_stream", "second_stream"), [(False, False), (False, True), (True, False), (True, True)]
)
@pytest.mark.parametrize(
    ("first_namespace", "second_namespace"), [("model-a", "model-b"), (None, ""), (None, "model-a")]
)
async def test_namespaces_isolate_shared_store(
    first_stream: bool,
    second_stream: bool,
    first_namespace: str | None,
    second_namespace: str | None,
) -> None:
    store = InMemoryStore[CHAT_CACHE_VALUE_TYPE]()
    first_model = ReplayChatCompletionClient(["model A response"])
    second_model = ReplayChatCompletionClient(["model B response"])
    first_model.set_cached_bool_value(False)
    second_model.set_cached_bool_value(False)
    first = ChatCompletionCache(first_model, store, namespace=first_namespace)
    second = ChatCompletionCache(second_model, store, namespace=second_namespace)

    first_result = await complete(first, first_stream)
    second_result = await complete(second, second_stream)

    assert first_result.content == "model A response"
    assert second_result.content == "model B response"
    assert not first_result.cached
    assert not second_result.cached
    assert (await complete(first, second_stream)).cached
    assert (await complete(second, first_stream)).cached


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [False, True])
async def test_same_namespace_shares_entries(streaming: bool) -> None:
    store = InMemoryStore[CHAT_CACHE_VALUE_TYPE]()
    first = ChatCompletionCache(ReplayChatCompletionClient(["shared response"]), store, namespace="same-model")
    second_model = ReplayChatCompletionClient(["unused"])
    second = ChatCompletionCache(second_model, store, namespace="same-model")

    await complete(first, streaming)
    result = await complete(second, not streaming)

    assert result.content == "shared response"
    assert result.cached
    assert second_model.create_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("namespace", [None, "", "provider:model:deployment"])
async def test_namespace_survives_component_roundtrip(namespace: str | None) -> None:
    store = InMemoryStore[CHAT_CACHE_VALUE_TYPE]()
    model = ReplayChatCompletionClient(["cached response"])
    model.set_cached_bool_value(False)
    original = ChatCompletionCache(model, store, namespace=namespace)
    await complete(original, streaming=False)

    config = original.dump_component()
    restored = ChatCompletionCache.load_component(config)
    restored.store = store
    result = await complete(restored, streaming=True)

    assert restored.dump_component().config.get("namespace") == namespace
    assert result.content == "cached response"
    assert result.cached
    assert isinstance(restored.client, ReplayChatCompletionClient)
    assert restored.client.create_calls == []


@pytest.mark.asyncio
async def test_default_namespace_preserves_existing_cache_keys() -> None:
    store = InMemoryStore[CHAT_CACHE_VALUE_TYPE]()
    original = ChatCompletionCache(ReplayChatCompletionClient(["response"]), store)
    await complete(original, streaming=False)

    legacy_data: dict[str, object] = {
        "messages": [UserMessage(content="same prompt", source="user").model_dump()],
        "tools": [],
        "json_output": None,
        "extra_create_args": {},
    }
    legacy_key = hashlib.sha256(json.dumps(legacy_data, sort_keys=True).encode()).hexdigest()
    assert list(store.store) == [legacy_key]

    config = original.dump_component()
    assert "namespace" not in config.config
    restored = ChatCompletionCache.load_component(config)
    restored.store = store
    assert (await complete(restored, streaming=False)).cached
