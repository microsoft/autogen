"""Message store abstraction for group chat message threads."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Sequence

from ...messages import BaseAgentEvent, BaseChatMessage

ChatMessage = BaseAgentEvent | BaseChatMessage


class MessageStore(ABC):
    """Abstract base class for storing group chat message threads.

    Implementations can provide different storage backends (in-memory, database, etc.)
    and message retention policies (e.g., TTL-based expiration).
    """

    @abstractmethod
    async def add(self, messages: Sequence[ChatMessage]) -> None:
        """Add messages to the store.

        Args:
            messages: A sequence of messages to append to the thread.
        """
        ...

    @abstractmethod
    async def get(self) -> List[ChatMessage]:
        """Return all messages currently in the store.

        Returns:
            A list of messages in chronological order.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Remove all messages from the store."""
        ...


class ListMessageStore(MessageStore):
    """In-memory message store backed by a Python list.

    Args:
        ttl: Optional time-to-live for messages. When set, messages older than
            ``ttl`` are automatically excluded from :meth:`get` results.
    """

    def __init__(self, *, ttl: timedelta | None = None) -> None:
        self._messages: List[ChatMessage] = []
        self._timestamps: List[datetime] = []
        self._ttl = ttl

    async def add(self, messages: Sequence[ChatMessage]) -> None:
        now = datetime.now()
        self._messages.extend(messages)
        self._timestamps.extend(now for _ in messages)

    async def get(self) -> List[ChatMessage]:
        if self._ttl is not None:
            cutoff = datetime.now() - self._ttl
            return [
                msg
                for msg, ts in zip(self._messages, self._timestamps)
                if ts >= cutoff
            ]
        return list(self._messages)

    async def clear(self) -> None:
        self._messages.clear()
        self._timestamps.clear()
