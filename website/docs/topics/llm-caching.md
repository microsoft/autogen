# LLM Caching

Since version [`0.2.8`](https://github.com/microsoft/autogen/releases/tag/v0.2.8), a configurable context manager allows you to easily
configure LLM cache, using either [`DiskCache`](/docs/reference/cache/disk_cache#diskcache) or [`RedisCache`](/docs/reference/cache/redis_cache#rediscache). All agents inside the
context manager will use the same cache.

```python
from autogen import Cache

# Use Redis as cache
with Cache.redis(redis_url="redis://localhost:6379/0") as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)

# Use DiskCache as cache
with Cache.disk() as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)
```

You can vary the `cache_seed` parameter to get different LLM output while
still using cache.

```python
# Setting the cache_seed to 1 will use a different cache from the default one
# and you will see different output.
with Cache.disk(cache_seed=1) as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)
```

By default [`DiskCache`](/docs/reference/cache/disk_cache#diskcache) uses `.cache` for storage. To change the cache directory,
set `cache_path_root`:

```python
with Cache.disk(cache_path_root="/tmp/autogen_cache") as cache:
    user.initiate_chat(assistant, message=coding_task, cache=cache)
```

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
