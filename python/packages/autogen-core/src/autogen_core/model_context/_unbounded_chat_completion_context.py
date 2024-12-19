from typing import List

from ..models import LLMMessage
from ._chat_completion_context import ChatCompletionContext


class UnboundedChatCompletionContext(ChatCompletionContext):
    """An unbounded chat completion context that keeps a view of the all the messages."""

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `buffer_size` recent messages."""
        return self._messages
