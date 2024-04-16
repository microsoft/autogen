from __future__ import annotations
from typing import Optional, Protocol, Sequence

from .types import MessageContext
from .types import Message


class ChatHistoryReadOnly(Protocol):
    @property
    def messages(self) -> Sequence[Message]: ...

    @property
    def contexts(self) -> Sequence[MessageContext]: ...

    def __len__(self) -> int: ...

    def __copy__(self) -> ChatHistoryReadOnly: ...


class ChatHistory(ChatHistoryReadOnly, Protocol):
    def append_message(self, message: Message, context: Optional[MessageContext]) -> None: ...
