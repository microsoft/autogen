import logging
from typing import Optional, Union

from .abstract_cache_base import AbstractCache
from .disk_cache import DiskCache


class CacheFactory:
    @staticmethod
    def cache_factory(
        seed: Union[str, int], redis_url: Optional[str] = None, cache_path_root: str = ".cache"
    ) -> AbstractCache:
        """
        Factory function for creating cache instances.

        Based on the provided redis_url, this function decides whether to create a RedisCache
        or DiskCache instance. If RedisCache is available and redis_url is provided,
        a RedisCache instance is created. Otherwise, a DiskCache instance is used.

        Args:
            seed (Union[str, int]): A string or int used as a seed or namespace for the cache.
                        This could be useful for creating distinct cache instances
                        or for namespacing keys in the cache.
            redis_url (str or None): The URL for the Redis server. If this is None
                                     or if RedisCache is not available, a DiskCache instance is created.

        Returns:
            An instance of either RedisCache or DiskCache, depending on the availability of RedisCache
            and the provided redis_url.

        Examples:

        Creating a Redis cache

        ```python
        redis_cache = cache_factory("myseed", "redis://localhost:6379/0")
        ```
        Creating a Disk cache

        ```python
        disk_cache = cache_factory("myseed", None)
        ```
        """
        if redis_url is not None:
            try:
                from .redis_cache import RedisCache

                return RedisCache(seed, redis_url)
            except ImportError:
                logging.warning("RedisCache is not available. Creating a DiskCache instance instead.")
                return DiskCache(f"./{cache_path_root}/{seed}")
        else:
            return DiskCache(f"./{cache_path_root}/{seed}")
