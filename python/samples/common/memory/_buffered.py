from typing import Any, List, Mapping

from agnext.components.memory import ChatMemory
from agnext.components.models import FunctionExecutionResultMessage

from ..types import Message


class BufferedChatMemory(ChatMemory[Message]):
    """A buffered chat memory that keeps a view of the last n messages,
    where n is the buffer size. The buffer size is set at initialization.

    Args:
        buffer_size (int): The size of the buffer.

    """

    def __init__(self, buffer_size: int) -> None:
        self._messages: List[Message] = []
        self._buffer_size = buffer_size

    async def add_message(self, message: Message) -> None:
        """Add a message to the memory."""
        self._messages.append(message)

    async def get_messages(self) -> List[Message]:
        """Get at most `buffer_size` recent messages."""
        messages = self._messages[-self._buffer_size :]
        # Handle the first message is a function call result message.
        if messages and isinstance(messages[0], FunctionExecutionResultMessage):
            # Remove the first message from the list.
            messages = messages[1:]
        return messages

    async def clear(self) -> None:
        """Clear the message memory."""
        self._messages = []

    def save_state(self) -> Mapping[str, Any]:
        return {
            "messages": [message for message in self._messages],
            "buffer_size": self._buffer_size,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = state["messages"]
        self._buffer_size = state["buffer_size"]
