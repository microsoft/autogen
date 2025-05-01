import asyncio
import time
from collections import deque
from typing import Optional, Sequence

from autogen_core._component_config import Component
from pydantic import BaseModel, Field
from typing_extensions import Self

from ..messages import BaseAgentEvent, BaseChatMessage, MessageFactory
from ._message_store import MessageStore


class ListMessage(BaseModel):
    """A message stored in memory.

    Args:
        message (BaseAgentEvent | BaseChatMessage): The message to store.
        timestamp (int): The timestamp of the message in seconds since epoch.
    """

    message: BaseAgentEvent | BaseChatMessage
    ts: int = Field(default_factory=lambda: int(time.time()))


class ListMessageStoreConfig(BaseModel):
    ttl_sec: Optional[int] = None


class ListMessageStore(MessageStore, Component[ListMessageStoreConfig]):
    """A message store that stores messages in memory with optional time-to-live.

    Args:
        ttl_sec (Optional[int]): Time-to-live in seconds for messages. If None, messages don't expire.
    """

    component_config_schema = ListMessageStoreConfig
    component_provider_override = "autogen_agentchat.message_store.MemoryMessageStore"

    def __init__(self, message_factory: MessageFactory, ttl_sec: Optional[int] = None):
        super().__init__(message_factory)
        self._messages: deque[ListMessage] = deque()
        self._lock = asyncio.Lock()
        self._ttl_sec = ttl_sec

    async def add_message(self, message: BaseAgentEvent | BaseChatMessage) -> None:
        async with self._lock:
            current_ts = int(time.time())
            self._messages.append(ListMessage(message=message, ts=current_ts))
            await self._remove_expired_messages(current_ts)

    async def add_messages(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        if not messages:
            return
        async with self._lock:
            current_ts = int(time.time())
            self._messages.extend(ListMessage(message=m, ts=current_ts) for m in messages)
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
                self._messages.extend(ListMessage(message=m, ts=current_ts) for m in messages)

    async def _remove_expired_messages(self, current_ts: int) -> None:
        if not self._ttl_sec:
            return

        time_threshold = current_ts - self._ttl_sec
        self._messages = deque(m for m in self._messages if m.ts > time_threshold)

    def _to_config(self) -> ListMessageStoreConfig:
        return ListMessageStoreConfig(ttl_sec=self._ttl_sec)

    @classmethod
    def _from_config(cls, config: ListMessageStoreConfig) -> Self:
        return cls(**config.model_dump())
