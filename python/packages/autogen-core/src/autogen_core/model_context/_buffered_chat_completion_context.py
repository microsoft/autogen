from typing import List

from ..models import FunctionExecutionResultMessage, LLMMessage
from ._chat_completion_context import ChatCompletionContext


class BufferedChatCompletionContext(ChatCompletionContext):
    """A buffered chat completion context that keeps a view of the last n messages,
    where n is the buffer size. The buffer size is set at initialization.

    Args:
        buffer_size (int): The size of the buffer.
        initial_messages (List[LLMMessage] | None): The initial messages.
    """

    def __init__(self, buffer_size: int, initial_messages: List[LLMMessage] | None = None) -> None:
        super().__init__(initial_messages)
        if buffer_size <= 0:
            raise ValueError("buffer_size must be greater than 0.")
        self._buffer_size = buffer_size

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `buffer_size` recent messages."""
        messages = self._messages[-self._buffer_size :]
        # Handle the first message is a function call result message.
        if messages and isinstance(messages[0], FunctionExecutionResultMessage):
            # Remove the first message from the list.
            messages = messages[1:]
        return messages
