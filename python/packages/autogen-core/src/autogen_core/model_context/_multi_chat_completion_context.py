from typing import List
from ._chat_completion_context import ChatCompletionContext
from ..models import LLMMessage


class MultiChatCompletionContext(ChatCompletionContext):
    """
    A wrapper context that chains multiple `ChatCompletionContext` objects.

    This allows combining multiple message management strategies (e.g.
    `UnboundedChatCompletionContext`, `TokenLimitedChatCompletionContext`) into
    a single unified context that can be passed to an `AssistantAgent`.

    Each context in the chain will process the message list sequentially.

    Example:
        .. code-block:: python

            from autogen_core.model_context import (
                MultiChatCompletionContext,
                UnboundedChatCompletionContext,
                TokenLimitedChatCompletionContext,
            )

            ctx = MultiChatCompletionContext([
                UnboundedChatCompletionContext(),
                TokenLimitedChatCompletionContext(max_tokens=4096),
            ])
            messages = await ctx.get_messages()
    """

    def __init__(self, contexts: List[ChatCompletionContext]):
        super().__init__()
        self._contexts = contexts

    async def get_messages(self) -> List[LLMMessage]:
        messages = self._messages
        for ctx in self._contexts:
            ctx._messages = messages
            messages = await ctx.get_messages()
        return messages
