from typing import Any, Optional, TypeVar, cast

import diskcache
from autogen_core import CacheStore

T = TypeVar("T")


class DiskCacheStore(CacheStore[T]):
    """
    A typed CacheStore implementation that uses diskcache as the underlying storage.
    See :class:`~autogen_ext.models.cache.ChatCompletionCache` for an example of usage.

    Args:
        cache_instance: An instance of diskcache.Cache.
                        The user is responsible for managing the DiskCache instance's lifetime.
    """

    def __init__(self, cache_instance: diskcache.Cache):  # type: ignore[no-any-unimported]
        self.cache = cache_instance

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        return cast(Optional[T], self.cache.get(key, default))  # type: ignore[reportUnknownMemberType]

    def set(self, key: str, value: T) -> None:
        self.cache.set(key, cast(Any, value))  # type: ignore[reportUnknownMemberType]
