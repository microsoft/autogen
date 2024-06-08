from typing import Any, List, Mapping

from ..types import Message
from ._base import ChatMemory


class FullChatMemory(ChatMemory):
    def __init__(self) -> None:
        self._messages: List[Message] = []

    def add_message(self, message: Message) -> None:
        self._messages.append(message)

    def get_messages(self) -> List[Message]:
        return self._messages

    def clear(self) -> None:
        self._messages = []

    def save_state(self) -> Mapping[str, Any]:
        return {"messages": [message for message in self._messages]}

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = state["messages"]
