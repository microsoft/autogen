from typing import Any, Optional, TypeVar, cast

import redis
from autogen_core import CacheStore

T = TypeVar("T")


class RedisStore(CacheStore[T]):
    """
    A typed CacheStore implementation that uses redis as the underlying storage.
    See :class:`~autogen_ext.models.cache.ChatCompletionCache` for an example of usage.

    Args:
        cache_instance: An instance of `redis.Redis`.
                        The user is responsible for managing the Redis instance's lifetime.
    """

    def __init__(self, redis_instance: redis.Redis):
        self.cache = redis_instance

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        value = cast(Optional[T], self.cache.get(key))
        if value is None:
            return default
        return value

    def set(self, key: str, value: T) -> None:
        self.cache.set(key, cast(Any, value))
