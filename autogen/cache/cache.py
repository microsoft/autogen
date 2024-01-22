from typing import Dict, Any

from autogen.cache.cache_factory import CacheFactory


class Cache:
    """
    A wrapper class for managing cache configuration and instances.

    This class provides a unified interface for creating and interacting with
    different types of cache (e.g., Redis, Disk). It abstracts the underlying
    cache implementation details, providing methods for cache operations.

    Attributes:
        config (Dict[str, Any]): A dictionary containing cache configuration.
        cache: The cache instance created based on the provided configuration.

    Methods:
        redis(cache_seed=42, redis_url="redis://localhost:6379/0"): Static method to create a Redis cache instance.
        disk(cache_seed=42, cache_path_root=".cache"): Static method to create a Disk cache instance.
        __init__(self, config): Initializes the Cache with the given configuration.
        __enter__(self): Context management entry, returning the cache instance.
        __exit__(self, exc_type, exc_value, traceback): Context management exit.
        get(self, key, default=None): Retrieves an item from the cache.
        set(self, key, value): Sets an item in the cache.
        close(self): Closes the cache.
    """

    ALLOWED_CONFIG_KEYS = ["cache_seed", "redis_url", "cache_path_root"]

    @staticmethod
    def redis(cache_seed=42, redis_url="redis://localhost:6379/0"):
        """
        Create a Redis cache instance.

        Args:
            cache_seed (int, optional): A seed for the cache. Defaults to 42.
            redis_url (str, optional): The URL for the Redis server. Defaults to "redis://localhost:6379/0".

        Returns:
            Cache: A Cache instance configured for Redis.
        """
        return Cache({"cache_seed": cache_seed, "redis_url": redis_url})

    @staticmethod
    def disk(cache_seed=42, cache_path_root=".cache"):
        """
        Create a Disk cache instance.

        Args:
            cache_seed (int, optional): A seed for the cache. Defaults to 42.
            cache_path_root (str, optional): The root path for the disk cache. Defaults to ".cache".

        Returns:
            Cache: A Cache instance configured for Disk caching.
        """
        return Cache({"cache_seed": cache_seed, "cache_path_root": cache_path_root})

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Cache with the given configuration.

        Validates the configuration keys and creates the cache instance.

        Args:
            config (Dict[str, Any]): A dictionary containing the cache configuration.

        Raises:
            ValueError: If an invalid configuration key is provided.
        """
        self.config = config
        # validate config
        for key in self.config.keys():
            if key not in self.ALLOWED_CONFIG_KEYS:
                raise ValueError(f"Invalid config key: {key}")
        # create cache instance
        self.cache = CacheFactory.cache_factory(
            self.config.get("cache_seed", "42"),
            self.config.get("redis_url", None),
            self.config.get("cache_path_root", None),
        )

    def __enter__(self):
        """
        Enter the runtime context related to the cache object.

        Returns:
            The cache instance for use within a context block.
        """
        return self.cache.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the runtime context related to the cache object.

        Cleans up the cache instance and handles any exceptions that occurred
        within the context.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_value: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.
        """
        return self.cache.__exit__(exc_type, exc_value, traceback)

    def get(self, key, default=None):
        """
        Retrieve an item from the cache.

        Args:
            key (str): The key identifying the item in the cache.
            default (optional): The default value to return if the key is not found.
                                Defaults to None.

        Returns:
            The value associated with the key if found, else the default value.
        """
        return self.cache.get(key, default)

    def set(self, key, value):
        """
        Set an item in the cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.
        """
        self.cache.set(key, value)

    def close(self):
        """
        Close the cache.

        Perform any necessary cleanup, such as closing connections or releasing resources.
        """
        self.cache.close()
