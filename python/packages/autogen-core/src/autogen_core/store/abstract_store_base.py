from typing import Any, Optional, Protocol


class AbstractStore(Protocol):
    """
    This protocol defines the basic interface for store/cache operations.

    Allows duck-typing with any object that implements the get and set methods,
    such as redis or diskcache interfaces.
    """

    def get(self, key: Any, default: Optional[Any] = None) -> Optional[Any]:
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

    def set(self, key: Any, value: Any) -> None:
        """
        Set an item in the store.

        Args:
            key: The key under which the item is to be stored.
            value: The value to be stored in the store.
        """
        ...
