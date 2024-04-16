import logging
from typing import Optional, Union

from .abstract_cache_base import AbstractCache
from .disk_cache import DiskCache


class CacheFactory:
    @staticmethod
    def cache_factory(
        seed: Union[str, int],
        redis_url: Optional[str] = None,
        cache_path_root: str = ".cache",
        connection_string: Optional[str] = None,
        database_id: str = "autogen_cache",
        container_id: Optional[str] = None,
    ) -> AbstractCache:
        """
        Factory function for creating cache instances.

        This function decides whether to create a RedisCache, DiskCache, or CosmosDBCache instance
        based on the provided parameters. If RedisCache is available and a redis_url is provided,
        a RedisCache instance is created. If connection_string, database_id, and container_id
        are provided, a CosmosDBCache is created. Otherwise, a DiskCache instance is used.

        Args:
            seed (Union[str, int]): A string or int used as a seed or namespace for the cache.
                        This could be useful for creating distinct cache instances
                        or for namespacing keys in the cache.
            redis_url (Optional[str]): The URL for the Redis server. If this is provided and Redis is available,
                                       a RedisCache instance is created.
            cache_path_root (str): The root path for the disk cache. Defaults to ".cache".
            connection_string (Optional[str]): The connection string for the Cosmos DB account. Required for creating a CosmosDBCache.
            database_id (Optional[str]): The database ID for the Cosmos DB account. Required for creating a CosmosDBCache.
            container_id (Optional[str]): The container ID for the Cosmos DB account. Required for creating a CosmosDBCache.

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

        Creating a Cosmos DB cache:
        ```python
        cosmos_cache = cache_factory("myseed", connection_string="your_connection_string", database_id="your_database_id", container_id="your_container_id")
        ```

        """
        if redis_url:
            try:
                from .redis_cache import RedisCache

                return RedisCache(seed, redis_url)
            except ImportError:
                logging.warning("RedisCache is not available. Fallback to DiskCache.")

        if connection_string and database_id and container_id:
            try:
                from .cosmos_db_cache import CosmosDBCache

                return CosmosDBCache(seed, connection_string, database_id, container_id)
            except ImportError:
                logging.warning("CosmosDBCache is not available. Fallback to DiskCache.")

        # Default to DiskCache if neither Redis nor Cosmos DB configurations are provided
        return DiskCache(f"./{cache_path_root}/{seed}")
