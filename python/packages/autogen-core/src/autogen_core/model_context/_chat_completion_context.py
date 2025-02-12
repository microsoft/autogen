from abc import ABC, abstractmethod
from typing import Any, List, Mapping

from pydantic import BaseModel, Field

from .._component_config import ComponentBase
from ..models import LLMMessage


class ChatCompletionContext(ABC, ComponentBase[BaseModel]):
    """An abstract base class for defining the interface of a chat completion context.
    A chat completion context lets agents store and retrieve LLM messages.
    It can be implemented with different recall strategies.

    Args:
        initial_messages (List[LLMMessage] | None): The initial messages.
    """

    component_type = "chat_completion_context"

    def __init__(self, initial_messages: List[LLMMessage] | None = None) -> None:
        self._messages: List[LLMMessage] = initial_messages or []

    async def add_message(self, message: LLMMessage) -> None:
        """Add a message to the context."""
        self._messages.append(message)

    @abstractmethod
    async def get_messages(self) -> List[LLMMessage]: ...

    async def clear(self) -> None:
        """Clear the context."""
        self._messages = []

    async def save_state(self) -> Mapping[str, Any]:
        return ChatCompletionContextState(messages=self._messages).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = ChatCompletionContextState.model_validate(state).messages


class ChatCompletionContextState(BaseModel):
    messages: List[LLMMessage] = Field(default_factory=list)
