import asyncio
import time
from typing import List, Optional, Sequence

from autogen_core._component_config import Component
from pydantic import BaseModel, Field
from typing_extensions import Self

from ..messages import BaseAgentEvent, BaseChatMessage, MessageFactory
from ._message_store import MessageStore


class ListMessage(BaseModel):
    """A message stored in memory.

    Args:
        message (BaseAgentEvent | BaseChatMessage): The message to store.
        ts (int): The timestamp of the message in seconds since epoch.
    """

    message: BaseAgentEvent | BaseChatMessage
    ts: int = Field(default_factory=lambda: int(time.time()))


class ListMessageStoreConfig(BaseModel):
    ttl_sec: Optional[int] = None


class ListMessageStore(MessageStore, Component[ListMessageStoreConfig]):
    """A message store that stores messages in memory with optional time-to-live.

    Args:
        message_factory (MessageFactory): Factory to create messages.
        pin_first_message (bool): If True, the first message will never be removed when trimming expired messages.
        pin_last_message (bool): If True, the last message will never be removed when trimming expired messages.
        ttl_sec (Optional[int]): Time-to-live in seconds for messages. If None, messages don't expire.
    """

    component_config_schema = ListMessageStoreConfig
    component_provider_override = "autogen_agentchat.message_store.MemoryMessageStore"

    def __init__(
        self,
        message_factory: MessageFactory,
        pin_first_message: bool = False,
        pin_last_message: bool = True,
        ttl_sec: Optional[int] = None,
    ):
        super().__init__(message_factory)
        self._messages: List[ListMessage] = []
        self._lock = asyncio.Lock()
        self.pin_first_message = pin_first_message
        self.pin_last_message = pin_last_message
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
        if not self._ttl_sec or not self._messages:
            return

        time_threshold = current_ts - self._ttl_sec

        first_message = self._messages[0] if self.pin_first_message else None
        last_message = (
            self._messages[-1] if self.pin_last_message and len(self._messages) > (1 if first_message else 0) else None
        )

        start_idx = 1 if self.pin_first_message else 0
        end_idx = len(self._messages) - (1 if self.pin_last_message else 0)

        retained_messages: List[ListMessage] = []

        if first_message:
            retained_messages.append(first_message)
        for i in range(start_idx, end_idx):
            if self._messages[i].ts > time_threshold:
                retained_messages.extend(self._messages[i:end_idx])
                break
        if last_message:
            retained_messages.append(last_message)

        self._messages = retained_messages

    def _to_config(self) -> ListMessageStoreConfig:
        return ListMessageStoreConfig(ttl_sec=self._ttl_sec)

    @classmethod
    def _from_config(cls, config: ListMessageStoreConfig) -> Self:
        return cls(**config.model_dump())
