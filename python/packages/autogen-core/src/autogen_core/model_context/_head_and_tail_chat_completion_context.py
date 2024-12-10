from typing import Any, List, Mapping

from .._types import FunctionCall
from ..models import AssistantMessage, FunctionExecutionResultMessage, LLMMessage, UserMessage
from ._chat_completion_context import ChatCompletionContext


class HeadAndTailChatCompletionContext(ChatCompletionContext):
    """A chat completion context that keeps a view of the first n and last m messages,
    where n is the head size and m is the tail size. The head and tail sizes
    are set at initialization.

    Args:
        head_size (int): The size of the head.
        tail_size (int): The size of the tail.
    """

    def __init__(self, head_size: int, tail_size: int) -> None:
        self._messages: List[LLMMessage] = []
        self._head_size = head_size
        self._tail_size = tail_size

    async def add_message(self, message: LLMMessage) -> None:
        """Add a message to the memory."""
        self._messages.append(message)

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `head_size` recent messages and `tail_size` oldest messages."""
        head_messages = self._messages[: self._head_size]
        # Handle the last message is a function call message.
        if (
            head_messages
            and isinstance(head_messages[-1], AssistantMessage)
            and isinstance(head_messages[-1].content, list)
            and all(isinstance(item, FunctionCall) for item in head_messages[-1].content)
        ):
            # Remove the last message from the head.
            head_messages = head_messages[:-1]

        tail_messages = self._messages[-self._tail_size :]
        # Handle the first message is a function call result message.
        if tail_messages and isinstance(tail_messages[0], FunctionExecutionResultMessage):
            # Remove the first message from the tail.
            tail_messages = tail_messages[1:]

        num_skipped = len(self._messages) - self._head_size - self._tail_size
        if num_skipped <= 0:
            # If there are not enough messages to fill the head and tail,
            # return all messages.
            return self._messages

        placeholder_messages = [UserMessage(content=f"Skipped {num_skipped} messages.", source="System")]
        return head_messages + placeholder_messages + tail_messages

    async def clear(self) -> None:
        """Clear the message memory."""
        self._messages = []

    def save_state(self) -> Mapping[str, Any]:
        return {
            "messages": [message for message in self._messages],
            "head_size": self._head_size,
            "tail_size": self._tail_size,
            "placeholder_message": self._placeholder_message,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = state["messages"]
        self._head_size = state["head_size"]
        self._tail_size = state["tail_size"]
        self._placeholder_message = state["placeholder_message"]
