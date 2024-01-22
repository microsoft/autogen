from abc import ABC, abstractmethod


class AbstractCache(ABC):
    """
    Abstract base class for cache implementations.

    This class defines the basic interface for cache operations.
    Implementing classes should provide concrete implementations for
    these methods to handle caching mechanisms.
    """

    @abstractmethod
    def get(self, key, default=None):
        """
        Retrieve an item from the cache.

        Abstract method that must be implemented by subclasses to
        retrieve an item from the cache.

        Args:
            key (str): The key identifying the item in the cache.
            default (optional): The default value to return if the key is not found.
                                Defaults to None.

        Returns:
            The value associated with the key if found, else the default value.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    def set(self, key, value):
        """
        Set an item in the cache.

        Abstract method that must be implemented by subclasses to
        store an item in the cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    def close(self):
        """
        Close the cache.

        Abstract method that should be implemented by subclasses to
        perform any necessary cleanup, such as closing network connections or
        releasing resources.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    def __enter__(self):
        """
        Enter the runtime context related to this object.

        The with statement will bind this method’s return value to the target(s)
        specified in the as clause of the statement, if any.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the runtime context and close the cache.

        Abstract method that should be implemented by subclasses to handle
        the exit from a with statement. It is responsible for resource
        release and cleanup.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_value: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
