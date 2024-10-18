from typing import List, Mapping, Protocol

from ..models import LLMMessage


class ChatCompletionContext(Protocol):
    """A protocol for defining the interface of a chat completion context.
    A chat completion context lets agents store and retrieve LLM messages.
    It can be implemented with different recall strategies."""

    async def add_message(self, message: LLMMessage) -> None: ...

    async def get_messages(self) -> List[LLMMessage]: ...

    async def clear(self) -> None: ...

    def save_state(self) -> Mapping[str, LLMMessage]: ...

    def load_state(self, state: Mapping[str, LLMMessage]) -> None: ...
