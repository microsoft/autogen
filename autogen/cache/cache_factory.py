from autogen.cache.disk_cache import DiskCache

try:
    from autogen.cache.redis_cache import RedisCache
except ImportError:
    RedisCache = None


class CacheFactory:
    @staticmethod
    def cache_factory(seed, redis_url=None, cache_path_root=".cache"):
        """
        Factory function for creating cache instances.

        Based on the provided redis_url, this function decides whether to create a RedisCache
        or DiskCache instance. If RedisCache is available and redis_url is provided,
        a RedisCache instance is created. Otherwise, a DiskCache instance is used.

        Args:
            seed (str): A string used as a seed or namespace for the cache.
                        This could be useful for creating distinct cache instances
                        or for namespacing keys in the cache.
            redis_url (str or None): The URL for the Redis server. If this is None
                                     or if RedisCache is not available, a DiskCache instance is created.

        Returns:
            An instance of either RedisCache or DiskCache, depending on the availability of RedisCache
            and the provided redis_url.

        Examples:
            Creating a Redis cache
            > redis_cache = cache_factory("myseed", "redis://localhost:6379/0")

            Creating a Disk cache
            > disk_cache = cache_factory("myseed", None)
        """
        if RedisCache is not None and redis_url is not None:
            return RedisCache(seed, redis_url)
        else:
            return DiskCache(f"./{cache_path_root}/{seed}")
