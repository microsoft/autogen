import asyncio
import time
from collections import deque
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from ..messages import BaseAgentEvent, BaseChatMessage, TextMessage
from ._message_store import MessageStore


class MemoryMessage(BaseModel):
    """A message stored in memory.

    Args:
        message (BaseAgentEvent | BaseChatMessage): The message to store.
        timestamp (int): The timestamp of the message in seconds since epoch.
    """

    message: BaseAgentEvent | BaseChatMessage | TextMessage
    ts: int = Field(default_factory=lambda: int(time.time()))


class MemoryMessageStore(MessageStore):
    """A message store that stores messages in memory with optional time-to-live.

    Args:
        ttl_sec (Optional[int]): Time-to-live in seconds for messages. If None, messages don't expire.
    """

    def __init__(self, ttl_sec: Optional[int] = None):
        super().__init__()
        self._messages: deque[MemoryMessage] = deque()
        self._lock = asyncio.Lock()
        self._ttl_sec = ttl_sec

    async def add_message(self, message: BaseAgentEvent | BaseChatMessage | TextMessage) -> None:
        async with self._lock:
            current_ts = int(time.time())
            self._messages.append(MemoryMessage(message=message, ts=current_ts))
            await self._remove_expired_messages(current_ts)

    async def add_messages(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        if not messages:
            return
        async with self._lock:
            current_ts = int(time.time())
            self._messages.extend(MemoryMessage(message=m, ts=current_ts) for m in messages)
            await self._remove_expired_messages(current_ts)

    async def get_messages(self) -> Sequence[BaseAgentEvent | BaseChatMessage]:
        async with self._lock:
            current_ts = int(time.time())
            await self._remove_expired_messages(current_ts)
            return [message.message for message in self._messages]

    async def reset_messages(self, messages: Optional[Sequence[BaseAgentEvent | BaseChatMessage]] = None) -> None:
        async with self._lock:
            self._messages.clear()
            if messages:
                current_ts = int(time.time())
                self._messages.extend(MemoryMessage(message=m, ts=current_ts) for m in messages)

    async def _remove_expired_messages(self, current_ts: int) -> None:
        if not self._ttl_sec:
            return

        time_threshold = current_ts - self._ttl_sec
        self._messages = deque(m for m in self._messages if m.ts > time_threshold)
