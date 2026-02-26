"""MessageStore abstraction for group chat message thread storage."""

import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Generic, List, Optional, Sequence, TypeVar

T = TypeVar("T")


class MessageStore(ABC, Generic[T]):
    """Abstract base class for storing and retrieving message threads in group chat teams.

    This abstraction allows different storage backends (in-memory, Redis, database, etc.)
    to be plugged into a group chat team. Implementations can also provide policies such
    as TTL-based expiration of stored messages.

    Type Args:
        T: The type of message stored in this store.

    Example:

        Creating a custom message store:

        .. code-block:: python

            from autogen_agentchat.teams import MessageStore


            class MyMessageStore(MessageStore[str]):
                def __init__(self) -> None:
                    self._messages: list[str] = []

                async def append(self, message: str) -> None:
                    self._messages.append(message)

                async def get_messages(self) -> list[str]:
                    return list(self._messages)

                async def clear(self) -> None:
                    self._messages.clear()

                async def count(self) -> int:
                    return len(self._messages)

    """

    @abstractmethod
    async def append(self, message: T) -> None:
        """Append a message to the store.

        Args:
            message: The message to append.
        """
        ...

    @abstractmethod
    async def get_messages(self) -> Sequence[T]:
        """Return all stored messages.

        Returns:
            A sequence of all messages currently in the store.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all messages from the store."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return the number of messages in the store.

        Returns:
            The number of messages currently in the store.
        """
        ...


class InMemoryMessageStore(MessageStore[T]):
    """In-memory implementation of :class:`MessageStore` with optional TTL-based expiration.

    Messages are stored in a Python list. When a ``ttl`` is provided, any call to
    :meth:`get_messages`, :meth:`count`, or :meth:`append` will first check
    whether the TTL has expired and clear the store automatically if it has.

    The TTL clock starts when the first message is appended after a clear (or on
    initial use). Calling :meth:`clear` explicitly resets the TTL clock.

    Args:
        ttl: Optional time-to-live for the entire message thread. If set, the
            stored messages are cleared automatically once this duration has
            elapsed since the first message was appended.

    Example:

        .. code-block:: python

            import asyncio
            from datetime import timedelta
            from autogen_agentchat.teams import InMemoryMessageStore


            async def main() -> None:
                store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(seconds=10))
                await store.append("hello")
                await store.append("world")
                print(await store.count())   # 2
                print(await store.get_messages())  # ['hello', 'world']
                await store.clear()
                print(await store.count())   # 0


            asyncio.run(main())

    """

    def __init__(self, ttl: Optional[timedelta] = None) -> None:
        self._messages: List[T] = []
        self._ttl = ttl
        # Monotonic timestamp (seconds) of when the first message was appended
        # after the last clear. None means the store is empty / never been used.
        self._started_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_expired(self) -> bool:
        """Return True if the TTL has elapsed since the first message was stored."""
        if self._ttl is None or self._started_at is None:
            return False
        return (time.monotonic() - self._started_at) >= self._ttl.total_seconds()

    def _evict_if_expired(self) -> None:
        """Clear the store in-place when the TTL has been exceeded."""
        if self._is_expired():
            self._messages.clear()
            self._started_at = None

    # ------------------------------------------------------------------
    # MessageStore interface
    # ------------------------------------------------------------------

    async def append(self, message: T) -> None:
        """Append a message to the store.

        If the TTL has already expired the store is cleared before the new
        message is appended, effectively restarting the TTL window.

        Args:
            message: The message to append.
        """
        self._evict_if_expired()
        if self._started_at is None:
            # Record the monotonic time of the first message in this window.
            self._started_at = time.monotonic()
        self._messages.append(message)

    async def get_messages(self) -> Sequence[T]:
        """Return all stored messages, automatically evicting expired messages.

        Returns:
            A sequence of messages. The sequence is empty if the store has
            expired or no messages have been appended yet.
        """
        self._evict_if_expired()
        return list(self._messages)

    async def clear(self) -> None:
        """Clear all messages from the store and reset the TTL clock."""
        self._messages.clear()
        self._started_at = None

    async def count(self) -> int:
        """Return the number of messages currently in the store.

        Returns:
            The number of messages. Returns 0 if the store has expired.
        """
        self._evict_if_expired()
        return len(self._messages)
