from typing import Any, List, Mapping, Protocol

from ..types import Message


class ChatMemory(Protocol):
    """A protocol for defining the interface of a chat memory. A chat memory
    lets agents to store and retrieve messages. It can be implemented with
    different memory recall strategies."""

    async def add_message(self, message: Message) -> None: ...

    async def get_messages(self) -> List[Message]: ...

    async def clear(self) -> None: ...

    def save_state(self) -> Mapping[str, Any]: ...

    def load_state(self, state: Mapping[str, Any]) -> None: ...
