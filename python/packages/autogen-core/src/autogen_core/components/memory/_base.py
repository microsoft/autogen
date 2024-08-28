from typing import List, Mapping, Protocol, TypeVar

T = TypeVar("T")


class ChatMemory(Protocol[T]):
    """A protocol for defining the interface of a chat memory. A chat memory
    lets agents store and retrieve messages. It can be implemented with
    different memory recall strategies."""

    async def add_message(self, message: T) -> None: ...

    async def get_messages(self) -> List[T]: ...

    async def clear(self) -> None: ...

    def save_state(self) -> Mapping[str, T]: ...

    def load_state(self, state: Mapping[str, T]) -> None: ...
