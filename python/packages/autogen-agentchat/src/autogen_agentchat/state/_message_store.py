"""Message store abstraction for storing message threads in teams.

This module provides the :class:`MessageStore` abstract base class and an
:class:`InMemoryMessageStore` implementation that serves as the default,
backwards-compatible storage backend for group chat message threads.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, List, Mapping, Sequence

from ..messages import BaseAgentEvent, BaseChatMessage


class MessageStore(ABC):
    """Abstract base class for message thread storage.

    A ``MessageStore`` is responsible for persisting the message thread that
    accumulates during a group chat session.  Implementations may choose to
    keep messages in memory, write them to a database, or use any other
    persistence strategy.

    The optional *ttl* (time-to-live) parameter specifies how long messages
    should be retained (in seconds).  A value of ``None`` means messages
    never expire.  It is the responsibility of each concrete implementation
    to honour the TTL policy.
    """

    def __init__(self, *, ttl: float | None = None) -> None:
        if ttl is not None and ttl <= 0:
            raise ValueError("TTL must be a positive number or None.")
        self._ttl = ttl

    @property
    def ttl(self) -> float | None:
        """Return the TTL (time-to-live) in seconds, or ``None`` for no expiry."""
        return self._ttl

    @abstractmethod
    async def add_messages(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        """Append one or more messages to the store.

        Args:
            messages: A sequence of messages to add.
        """
        ...

    @abstractmethod
    async def get_messages(self) -> List[BaseAgentEvent | BaseChatMessage]:
        """Return all non-expired messages in insertion order.

        Returns:
            A list of messages.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Remove **all** messages from the store (including unexpired ones)."""
        ...

    @abstractmethod
    async def save_state(self) -> Mapping[str, Any]:
        """Serialise the current store contents so they can be persisted externally.

        Returns:
            A JSON-serialisable mapping.
        """
        ...

    @abstractmethod
    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore the store from a previously saved state.

        Args:
            state: A mapping previously returned by :meth:`save_state`.
        """
        ...


class InMemoryMessageStore(MessageStore):
    """A simple in-memory message store that is fully backwards compatible with
    the previous ``List``-based storage used in :class:`BaseGroupChatManager`.

    When a *ttl* is configured, messages older than *ttl* seconds are
    automatically pruned on every read (:meth:`get_messages`).  Timestamps are
    captured at the time :meth:`add_messages` is called.

    Example:

    .. code-block:: python

        store = InMemoryMessageStore(ttl=300)  # 5-minute TTL
        await store.add_messages([msg1, msg2])
        messages = await store.get_messages()
    """

    def __init__(self, *, ttl: float | None = None) -> None:
        super().__init__(ttl=ttl)
        self._messages: List[BaseAgentEvent | BaseChatMessage] = []
        # Parallel list of insertion timestamps (epoch seconds) when TTL is enabled.
        self._timestamps: List[float] = []

    async def add_messages(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        now = time.monotonic()
        for msg in messages:
            self._messages.append(msg)
            self._timestamps.append(now)

    async def get_messages(self) -> List[BaseAgentEvent | BaseChatMessage]:
        if self._ttl is not None:
            self._prune_expired()
        return list(self._messages)

    async def clear(self) -> None:
        self._messages.clear()
        self._timestamps.clear()

    async def save_state(self) -> Mapping[str, Any]:
        return {
            "messages": [msg.dump() for msg in self._messages],
            "timestamps": list(self._timestamps),
        }

    async def load_state(self, state: Mapping[str, Any]) -> None:
        from ..messages import MessageFactory

        factory = MessageFactory()
        self._messages = [factory.create(m) for m in state.get("messages", [])]
        self._timestamps = list(state.get("timestamps", []))
        # Ensure timestamps list is the same length as messages.
        while len(self._timestamps) < len(self._messages):
            self._timestamps.append(time.monotonic())

    # ------------------------------------------------------------------
    # Convenience helpers for the group chat manager integration
    # ------------------------------------------------------------------

    def extend(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        """Synchronous helper that mirrors ``list.extend`` for easy migration."""
        now = time.monotonic()
        for msg in messages:
            self._messages.append(msg)
            self._timestamps.append(now)

    @property
    def messages(self) -> List[BaseAgentEvent | BaseChatMessage]:
        """Direct access to the underlying list (backwards compatibility)."""
        if self._ttl is not None:
            self._prune_expired()
        return self._messages

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prune_expired(self) -> None:
        """Remove messages that have exceeded the TTL."""
        if self._ttl is None:
            return
        cutoff = time.monotonic() - self._ttl
        # Walk from the front; messages are in insertion order so timestamps
        # are monotonically non-decreasing.
        first_valid = 0
        for i, ts in enumerate(self._timestamps):
            if ts >= cutoff:
                first_valid = i
                break
        else:
            # All messages are expired.
            first_valid = len(self._messages)
        if first_valid > 0:
            del self._messages[:first_valid]
            del self._timestamps[:first_valid]
