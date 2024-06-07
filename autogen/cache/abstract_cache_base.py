import sys
from types import TracebackType
from typing import Any, Optional, Protocol, Type

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class AbstractCache(Protocol):
    """
    This protocol defines the basic interface for cache operations.
    Implementing classes should provide concrete implementations for
    these methods to handle caching mechanisms.
    """

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
        ...

    def set(self, key: str, value: Any) -> None:
        """
        Set an item in the cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.
        """
        ...

    def close(self) -> None:
        """
        Close the cache. Perform any necessary cleanup, such as closing network connections or
        releasing resources.
        """
        ...

    def __enter__(self) -> Self:
        """
        Enter the runtime context related to this object.

        The with statement will bind this method's return value to the target(s)
        specified in the as clause of the statement, if any.
        """
        ...

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Exit the runtime context and close the cache.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_value: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.
        """
        ...
