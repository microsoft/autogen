from typing import List, Optional, Sequence

from autogen.experimental.types import Message, MessageContext
from .chat_history import ChatHistory


class ConversationList(ChatHistory):
    def __init__(self) -> None:
        self._messages: List[Message] = []
        self._message_contexts: List[MessageContext] = []

    @property
    def messages(self) -> Sequence[Message]:
        return self._messages

    @property
    def contexts(self) -> Sequence[MessageContext]:
        return self._message_contexts

    def __len__(self) -> int:
        return len(self._messages)

    def append_message(self, message: Message, context: Optional[MessageContext]) -> None:
        self._messages.append(message)
        self._message_contexts.append(context or MessageContext())

    def __copy__(self) -> ChatHistory:
        new_conversation = ConversationList()
        new_conversation._messages = self._messages.copy()
        new_conversation._message_contexts = self._message_contexts.copy()
        return new_conversation
