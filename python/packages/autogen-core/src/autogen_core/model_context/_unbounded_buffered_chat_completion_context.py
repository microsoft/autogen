from typing import Any, List, Mapping

from ..models import LLMMessage
from ._chat_completion_context import ChatCompletionContext


class UnboundedBufferedChatCompletionContext(ChatCompletionContext):
    """An unbounded buffered chat completion context that keeps a view of the all the messages."""

    def __init__(self, initial_messages: List[LLMMessage] | None = None) -> None:
        self._messages: List[LLMMessage] = initial_messages or []

    async def add_message(self, message: LLMMessage) -> None:
        """Add a message to the memory."""
        self._messages.append(message)

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `buffer_size` recent messages."""
        return self._messages

    async def clear(self) -> None:
        """Clear the message memory."""
        self._messages = []

    def save_state(self) -> Mapping[str, Any]:
        return {
            "messages": [message for message in self._messages],
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = state["messages"]
