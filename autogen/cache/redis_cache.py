import pickle
import redis
from .abstract_cache_base import AbstractCache


class RedisCache(AbstractCache):
    """
    Implementation of AbstractCache using the Redis database.

    This class provides a concrete implementation of the AbstractCache
    interface using the Redis database for caching data.

    Attributes:
        seed (str): A seed or namespace used as a prefix for cache keys.
        cache (redis.Redis): The Redis client used for caching.

    Methods:
        __init__(self, seed, redis_url): Initializes the RedisCache with the given seed and Redis URL.
        _prefixed_key(self, key): Internal method to get a namespaced cache key.
        get(self, key, default=None): Retrieves an item from the cache.
        set(self, key, value): Sets an item in the cache.
        close(self): Closes the Redis client.
        __enter__(self): Context management entry.
        __exit__(self, exc_type, exc_value, traceback): Context management exit.
    """

    def __init__(self, seed, redis_url):
        """
        Initialize the RedisCache instance.

        Args:
            seed (str): A seed or namespace for the cache. This is used as a prefix for all cache keys.
            redis_url (str): The URL for the Redis server.

        """
        self.seed = seed
        self.cache = redis.Redis.from_url(redis_url)

    def _prefixed_key(self, key):
        """
        Get a namespaced key for the cache.

        Args:
            key (str): The original key.

        Returns:
            str: The namespaced key.
        """
        return f"autogen:{self.seed}:{key}"

    def get(self, key, default=None):
        """
        Retrieve an item from the Redis cache.

        Args:
            key (str): The key identifying the item in the cache.
            default (optional): The default value to return if the key is not found.
                                Defaults to None.

        Returns:
            The deserialized value associated with the key if found, else the default value.
        """
        result = self.cache.get(self._prefixed_key(key))
        if result is None:
            return default
        return pickle.loads(result)

    def set(self, key, value):
        """
        Set an item in the Redis cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.

        Notes:
            The value is serialized using pickle before being stored in Redis.
        """
        serialized_value = pickle.dumps(value)
        self.cache.set(self._prefixed_key(key), serialized_value)

    def close(self):
        """
        Close the Redis client.

        Perform any necessary cleanup, such as closing network connections.
        """
        self.cache.close()

    def __enter__(self):
        """
        Enter the runtime context related to the object.

        Returns:
            self: The instance itself.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the runtime context related to the object.

        Perform cleanup actions such as closing the Redis client.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_value: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.
        """
        self.close()
