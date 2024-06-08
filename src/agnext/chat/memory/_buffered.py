from typing import Any, List, Mapping

from ..types import Message
from ._base import ChatMemory


class BufferedChatMemory(ChatMemory):
    def __init__(self, buffer_size: int) -> None:
        self._messages: List[Message] = []
        self._buffer_size = buffer_size

    def add_message(self, message: Message) -> None:
        self._messages.append(message)

    def get_messages(self) -> List[Message]:
        return self._messages[-self._buffer_size :]

    def clear(self) -> None:
        self._messages = []

    def save_state(self) -> Mapping[str, Any]:
        return {
            "messages": [message for message in self._messages],
            "buffer_size": self._buffer_size,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = state["messages"]
        self._buffer_size = state["buffer_size"]
