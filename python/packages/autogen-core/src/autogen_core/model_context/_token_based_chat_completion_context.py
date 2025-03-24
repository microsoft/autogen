from typing import List

from pydantic import BaseModel
from typing_extensions import Self
import tiktoken

from .._component_config import Component
from ..models import FunctionExecutionResultMessage, LLMMessage
from ._chat_completion_context import ChatCompletionContext


class TokenBasedChatCompletionContextConfig(BaseModel):
    token_limit: int
    model_family: str
    initial_messages: List[LLMMessage] | None = None


class TokenBasedChatCompletionContext(ChatCompletionContext, Component[TokenBasedChatCompletionContextConfig]):
    """A token based chat completion context maintains a view of the context up to a token limit,
    where n is the token limit. The token limit is set at initialization.

    Args:
        token_limit (int): Max tokens for context.
        initial_messages (List[LLMMessage] | None): The initial messages.
    """

    component_config_schema = TokenBasedChatCompletionContextConfig
    component_provider_override = "autogen_core.model_context.TokenBasedChatCompletionContext"

    def __init__(self, token_limit: int, model_family: str, initial_messages: List[LLMMessage] | None = None) -> None:
        super().__init__(initial_messages)
        if token_limit <= 0:
            raise ValueError("token_limit must be greater than 0.")
        self._token_limit = token_limit
        self._model_family = model_family

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `token_limit` tokens in recent messages."""
        token_count = count_chat_tokens(self._messages, self._model_family)
        while token_count > self._token_limit:
            middle_index = len(self._messages) // 2
            self._messages.pop(middle_index)
            token_count = count_chat_tokens(self._messages, self._model_family)
        messages = self._messages
        # Handle the first message is a function call result message.
        if messages and isinstance(messages[0], FunctionExecutionResultMessage):
            # Remove the first message from the list.
            messages = messages[1:]
        return messages

    def _to_config(self) -> TokenBasedChatCompletionContextConfig:
        return TokenBasedChatCompletionContextConfig(token_limit=self._token_limit, model_family=self._model_family, initial_messages=self._messages)

    @classmethod
    def _from_config(cls, config: TokenBasedChatCompletionContextConfig) -> Self:
        return cls(**config.model_dump())

def count_chat_tokens(messages: list, model: str = "gpt-4o") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    total_tokens = 0
    for message in messages:
        total_tokens += len(encoding.encode(message.content))

    return total_tokens