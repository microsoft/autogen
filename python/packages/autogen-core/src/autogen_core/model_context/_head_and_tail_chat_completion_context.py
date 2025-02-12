from typing import List

from pydantic import BaseModel
from typing_extensions import Self

from .._component_config import Component
from .._types import FunctionCall
from ..models import AssistantMessage, FunctionExecutionResultMessage, LLMMessage, UserMessage
from ._chat_completion_context import ChatCompletionContext


class HeadAndTailChatCompletionContextConfig(BaseModel):
    head_size: int
    tail_size: int
    initial_messages: List[LLMMessage] | None = None


class HeadAndTailChatCompletionContext(ChatCompletionContext, Component[HeadAndTailChatCompletionContextConfig]):
    """A chat completion context that keeps a view of the first n and last m messages,
    where n is the head size and m is the tail size. The head and tail sizes
    are set at initialization.

    Args:
        head_size (int): The size of the head.
        tail_size (int): The size of the tail.
        initial_messages (List[LLMMessage] | None): The initial messages.
    """

    component_config_schema = HeadAndTailChatCompletionContextConfig
    component_provider_override = "autogen_core.model_context.HeadAndTailChatCompletionContext"

    def __init__(self, head_size: int, tail_size: int, initial_messages: List[LLMMessage] | None = None) -> None:
        super().__init__(initial_messages)
        if head_size <= 0:
            raise ValueError("head_size must be greater than 0.")
        if tail_size <= 0:
            raise ValueError("tail_size must be greater than 0.")
        self._head_size = head_size
        self._tail_size = tail_size

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

    def _to_config(self) -> HeadAndTailChatCompletionContextConfig:
        return HeadAndTailChatCompletionContextConfig(
            head_size=self._head_size, tail_size=self._tail_size, initial_messages=self._messages
        )

    @classmethod
    def _from_config(cls, config: HeadAndTailChatCompletionContextConfig) -> Self:
        return cls(head_size=config.head_size, tail_size=config.tail_size, initial_messages=config.initial_messages)
