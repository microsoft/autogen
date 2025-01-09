from typing import Generic, Optional, Protocol, TypeVar

T = TypeVar("T")


class CacheStore(Protocol, Generic[T]):
    """
    This protocol defines the basic interface for store/cache operations.

    Allows duck-typing with any object that implements the get and set methods,
    such as redis or diskcache interfaces.
    """

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Retrieve an item from the store.

        Args:
            key: The key identifying the item in the store.
            default (optional): The default value to return if the key is not found.
                                Defaults to None.

        Returns:
            The value associated with the key if found, else the default value.
        """
        ...

    def set(self, key: str, value: T) -> None:
        """
        Set an item in the store.

        Args:
            key: The key under which the item is to be stored.
            value: The value to be stored in the store.
        """
        ...
