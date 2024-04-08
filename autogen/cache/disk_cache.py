import sys
from types import TracebackType
from typing import Any, Optional, Type, Union

import diskcache

from .abstract_cache_base import AbstractCache

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class DiskCache(AbstractCache):
    """
    Implementation of AbstractCache using the DiskCache library.

    This class provides a concrete implementation of the AbstractCache
    interface using the diskcache library for caching data on disk.

    Attributes:
        cache (diskcache.Cache): The DiskCache instance used for caching.

    Methods:
        __init__(self, seed): Initializes the DiskCache with the given seed.
        get(self, key, default=None): Retrieves an item from the cache.
        set(self, key, value): Sets an item in the cache.
        close(self): Closes the cache.
        __enter__(self): Context management entry.
        __exit__(self, exc_type, exc_value, traceback): Context management exit.
    """

    def __init__(self, seed: Union[str, int]):
        """
        Initialize the DiskCache instance.

        Args:
            seed (Union[str, int]): A seed or namespace for the cache. This is used to create
                        a unique storage location for the cache data.

        """
        self.cache = diskcache.Cache(seed)

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
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

    def set(self, key: str, value: Any) -> None:
        """
        Set an item in the cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.
        """
        self.cache.set(key, value)

    def close(self) -> None:
        """
        Close the cache.

        Perform any necessary cleanup, such as closing file handles or
        releasing resources.
        """
        self.cache.close()

    def __enter__(self) -> Self:
        """
        Enter the runtime context related to the object.

        Returns:
            self: The instance itself.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Exit the runtime context related to the object.

        Perform cleanup actions such as closing the cache.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_value: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.
        """
        self.close()
