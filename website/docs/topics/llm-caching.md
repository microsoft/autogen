# LLM Caching

AutoGen supports caching API requests so that they can be reused when the same request is issued. This is useful when repeating or continuing experiments for reproducibility and cost saving.

Since version [`0.2.8`](https://github.com/microsoft/autogen/releases/tag/v0.2.8), a configurable context manager allows you to easily
configure LLM cache, using either [`DiskCache`](/docs/reference/cache/disk_cache#diskcache), [`RedisCache`](/docs/reference/cache/redis_cache#rediscache), or Cosmos DB Cache. All agents inside the context manager will use the same cache.

```python
from autogen import Cache

# Use Redis as cache
with Cache.redis(redis_url="redis://localhost:6379/0") as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)

# Use DiskCache as cache
with Cache.disk() as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)

# Use Azure Cosmos DB as cache
with Cache.cosmos_db(connection_string="your_connection_string", database_id="your_database_id", container_id="your_container_id") as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)

```

The cache can also be passed directly to the model client's create call.

```python
client = OpenAIWrapper(...)
with Cache.disk() as cache:
    client.create(..., cache=cache)
```

## Controlling the seed

You can vary the `cache_seed` parameter to get different LLM output while
still using cache.

```python
# Setting the cache_seed to 1 will use a different cache from the default one
# and you will see different output.
with Cache.disk(cache_seed=1) as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)
```

## Cache path

By default [`DiskCache`](/docs/reference/cache/disk_cache#diskcache) uses `.cache` for storage. To change the cache directory,
set `cache_path_root`:

```python
with Cache.disk(cache_path_root="/tmp/autogen_cache") as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)
```

## Disabling cache

For backward compatibility, [`DiskCache`](/docs/reference/cache/disk_cache#diskcache) is on by default with `cache_seed` set to 41.
To disable caching completely, set `cache_seed` to `None` in the `llm_config` of the agent.

```python
assistant = AssistantAgent(
    "coding_agent",
    llm_config={
        "cache_seed": None,
        "config_list": OAI_CONFIG_LIST,
        "max_tokens": 1024,
    },
)
```

## Difference between `cache_seed` and OpenAI's `seed` parameter

OpenAI v1.1 introduced a new parameter `seed`. The difference between AutoGen's `cache_seed` and OpenAI's `seed` is AutoGen uses an explicit request cache to guarantee the exactly same output is produced for the same input and when cache is hit, no OpenAI API call will be made. OpenAI's `seed` is a best-effort deterministic sampling with no guarantee of determinism. When using OpenAI's `seed` with `cache_seed` set to `None`, even for the same input, an OpenAI API call will be made and there is no guarantee for getting exactly the same output.
