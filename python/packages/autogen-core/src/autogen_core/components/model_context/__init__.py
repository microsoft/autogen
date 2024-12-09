from typing_extensions import deprecated

from ...model_context import BufferedChatCompletionContext as BufferedChatCompletionContextAlias
from ...model_context import ChatCompletionContext as ChatCompletionContextAlias
from ...model_context import HeadAndTailChatCompletionContext as HeadAndTailChatCompletionContextAlias

__all__ = [
    "ChatCompletionContext",
    "BufferedChatCompletionContext",
    "HeadAndTailChatCompletionContext",
]


@deprecated(
    "autogen_core.components.model_context.BufferedChatCompletionContextAlias moved to autogen_core.model_context.BufferedChatCompletionContextAlias. This alias will be removed in 0.4.0."
)
class BufferedChatCompletionContext(BufferedChatCompletionContextAlias):
    pass


@deprecated(
    "autogen_core.components.model_context.HeadAndTailChatCompletionContextAlias moved to autogen_core.model_context.HeadAndTailChatCompletionContextAlias. This alias will be removed in 0.4.0."
)
class HeadAndTailChatCompletionContext(HeadAndTailChatCompletionContextAlias):
    pass


@deprecated(
    "autogen_core.components.model_context.ChatCompletionContextAlias moved to autogen_core.model_context.ChatCompletionContextAlias. This alias will be removed in 0.4.0."
)
class ChatCompletionContext(ChatCompletionContextAlias):
    pass
