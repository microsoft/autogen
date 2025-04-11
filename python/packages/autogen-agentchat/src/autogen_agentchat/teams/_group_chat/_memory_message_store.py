import asyncio
import time
from typing import List, Optional

from ...messages import BaseChatMessage
from ._message_store import MessageStore


class MemoryMessageStore(MessageStore):
    def __init__(self, ttl: Optional[float] = None):
        super().__init__()
        self._ttl = ttl
        self._lock = asyncio.Lock()
        self._messages: List[tuple[BaseChatMessage, float]] = []

    async def add_message(self, message: BaseChatMessage) -> None:
        await self._remove_expired_messages()
        async with self._lock:
            self._messages.append((message, time.time()))

    async def get_message_thread(self) -> List[BaseChatMessage]:
        await self._remove_expired_messages()

        async with self._lock:
            return [message for message, _ in self._messages]

    async def clear(self) -> None:
        async with self._lock:
            self._messages.clear()

    async def _remove_expired_messages(self) -> None:
        if self._ttl:
            async with self._lock:
                time_threshold = time.time() - self._ttl
                self._messages = [
                    (message, timestamp) for message, timestamp in self._messages if timestamp > time_threshold
                ]

    @property
    def ttl(self) -> Optional[float]:
        return self._ttl
