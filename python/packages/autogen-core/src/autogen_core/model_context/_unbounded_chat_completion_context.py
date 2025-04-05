from typing import List

from pydantic import BaseModel
from typing_extensions import Self

from .._component_config import Component
from ..models import LLMMessage
from ._chat_completion_context import ChatCompletionContext


class UnboundedChatCompletionContextConfig(BaseModel):
    initial_messages: List[LLMMessage] | None = None


class UnboundedChatCompletionContext(ChatCompletionContext, Component[UnboundedChatCompletionContextConfig]):
    """An unbounded chat completion context that keeps a view of the all the messages."""

    component_config_schema = UnboundedChatCompletionContextConfig
    component_provider_override = "autogen_core.model_context.UnboundedChatCompletionContext"

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `buffer_size` recent messages."""
        return self._messages

    def _to_config(self) -> UnboundedChatCompletionContextConfig:
        return UnboundedChatCompletionContextConfig(initial_messages=self._initial_messages)

    @classmethod
    def _from_config(cls, config: UnboundedChatCompletionContextConfig) -> Self:
        return cls(initial_messages=config.initial_messages)
