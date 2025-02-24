from typing import Any, Optional, TypeVar, cast

import diskcache
from autogen_core import CacheStore, Component
from pydantic import BaseModel
from typing_extensions import Self

T = TypeVar("T")


class DiskCacheStoreConfig(BaseModel):
    """Configuration for DiskCacheStore"""

    directory: str  # Path where cache is stored
    # Could add other diskcache.Cache parameters like size_limit, etc.


class DiskCacheStore(CacheStore[T], Component[DiskCacheStoreConfig]):
    """
    A typed CacheStore implementation that uses diskcache as the underlying storage.
    See :class:`~autogen_ext.models.cache.ChatCompletionCache` for an example of usage.

    Args:
        cache_instance: An instance of diskcache.Cache.
                        The user is responsible for managing the DiskCache instance's lifetime.
    """

    component_config_schema = DiskCacheStoreConfig
    component_provider_override = "autogen_ext.cache_store.diskcache.DiskCacheStore"

    def __init__(self, cache_instance: diskcache.Cache):  # type: ignore[no-any-unimported]
        self.cache = cache_instance

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        return cast(Optional[T], self.cache.get(key, default))  # type: ignore[reportUnknownMemberType]

    def set(self, key: str, value: T) -> None:
        self.cache.set(key, cast(Any, value))  # type: ignore[reportUnknownMemberType]

    def _to_config(self) -> DiskCacheStoreConfig:
        # Get directory from cache instance
        return DiskCacheStoreConfig(directory=self.cache.directory)

    @classmethod
    def _from_config(cls, config: DiskCacheStoreConfig) -> Self:
        return cls(cache_instance=diskcache.Cache(config.directory))  # type: ignore[no-any-return]
