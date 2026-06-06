from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from ..messages import BaseAgentEvent, BaseChatMessage


class MessageStore(ABC):
    """Abstract base class for storing message threads in group chats.

    This provides an abstraction layer for persisting the message thread
    produced during a group chat. Implementations can store messages in
    memory, on disk, in a database, etc.

    All methods are async to work with the async group chat infrastructure.
    """

    @abstractmethod
    async def append(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        """Append messages to the store.

        Args:
            messages: The messages to append.
        """
        ...

    @abstractmethod
    async def get_messages(self) -> Sequence[BaseAgentEvent | BaseChatMessage]:
        """Retrieve all messages from the store.

        Returns:
            A sequence of all stored messages.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all messages from the store."""
        ...


class InMemoryMessageStore(MessageStore):
    """An in-memory implementation of :class:`MessageStore`.

    This store holds messages in a Python list. It is the default
    implementation used when no custom store is provided.

    Args:
        ttl: Optional time-to-live in seconds. If set, messages older than
            this will be filtered out when retrieved. Defaults to None (no TTL).
    """

    def __init__(self, ttl: Optional[float] = None) -> None:
        self._messages: List[BaseAgentEvent | BaseChatMessage] = []
        self._ttl = ttl

    async def append(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        self._messages.extend(messages)

    async def get_messages(self) -> Sequence[BaseAgentEvent | BaseChatMessage]:
        if self._ttl is not None:
            import datetime

            now = datetime.datetime.now()
            cutoff = now - datetime.timedelta(seconds=self._ttl)
            return [m for m in self._messages if m.created_at >= cutoff]
        return list(self._messages)

    async def clear(self) -> None:
        self._messages.clear()
