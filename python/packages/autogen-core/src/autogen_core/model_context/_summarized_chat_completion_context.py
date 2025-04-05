from typing import Callable, List

from pydantic import BaseModel
from typing_extensions import Self

from .._component_config import Component
from ..models import LLMMessage
from ._chat_completion_context import ChatCompletionContext
from ._conditions import MessageCompletionCondition


class SummarizedChatCompletionContextConfig(BaseModel):
    summarizing_func: Callable[[List[LLMMessage], List[LLMMessage]], List[LLMMessage]]
    summarizing_condition: "MessageCompletionCondition"
    initial_messages: List[LLMMessage] | None = None
    non_summarized_messages: List[LLMMessage] | None = None


class SummarizedChatCompletionContext(ChatCompletionContext, Component[SummarizedChatCompletionContextConfig]):
    """A summarized chat completion context that summarizes the messages in the context
    using a summarizing function. The summarizing function is set at initialization.
    The summarizing condition is used to determine when to summarize the messages.

    Args:
        summarizing_func (Callable[[List[LLMMessage]], List[LLMMessage]]): The function to summarize the messages.
        summarizing_condition (MessageCompletionCondition): The condition to determine when to summarize the messages.
        initial_messages (List[LLMMessage] | None): The initial messages.
    """

    component_config_schema = SummarizedChatCompletionContextConfig
    component_provider_override = "autogen_core.model_context.SummarizedChatCompletionContext"

    def __init__(
        self,
        summarizing_func: Callable[[List[LLMMessage], List[LLMMessage]], List[LLMMessage]],
        summarizing_condition: "MessageCompletionCondition",
        initial_messages: List[LLMMessage] | None = None,
        non_summarized_messages: List[LLMMessage] | None = None,
    ) -> None:
        self._non_summarized_messages: List[LLMMessage] = []
        super().__init__(initial_messages)
        if non_summarized_messages is None:
            self._non_summarized_messages.extend(self._messages)
        else:
            self._non_summarized_messages.extend(non_summarized_messages)

        self._summarizing_func = summarizing_func
        self._summarizing_condition = summarizing_condition

    async def add_message(self, message: LLMMessage) -> None:
        """Add a message to the context."""
        self._non_summarized_messages.append(message)
        await super().add_message(message)

        # Check if the summarizing condition is met.
        await self._summarizing_condition(self._messages)
        if self._summarizing_condition.triggered:
            # If the condition is met, summarize the messages.
            await self.summary()

    async def get_messages(self) -> List[LLMMessage]:
        return self._messages

    async def summary(self) -> None:
        summarized_message = self._summarizing_func(self._messages, self._non_summarized_messages)
        self._messages = summarized_message

    def _to_config(self) -> SummarizedChatCompletionContextConfig:
        return SummarizedChatCompletionContextConfig(
            summarizing_func=self._summarizing_func,
            summarizing_condition=self._summarizing_condition,
            initial_messages=self._initial_messages,
        )

    @classmethod
    def _from_config(cls, config: SummarizedChatCompletionContextConfig) -> Self:
        return cls(
            summarizing_func=config.summarizing_func,
            summarizing_condition=config.summarizing_condition,
            initial_messages=config.initial_messages,
            non_summarized_messages=config.non_summarized_messages,
        )
