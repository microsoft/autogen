from typing import List

from pydantic import BaseModel
from typing_extensions import Self

from autogen_core import ComponentModel

from .._component_config import Component
from ..models import LLMMessage
from ..tools._base import BaseTool
from ._chat_completion_context import ChatCompletionContext
from .conditions import MessageCompletionCondition, SummarizngFunction, SummaryFunction


class SummarizedChatCompletionContextConfig(BaseModel):
    summarizing_func: ComponentModel
    summarizing_condition: ComponentModel
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

    Example:
        .. code-block:: python

            from typing import List

            from autogen_core.model_context import SummarizedChatCompletionContext
            from autogen_core.models import LLMMessage


            def summarizing_func(messages: List[LLMMessage]) -> List[LLMMessage]:
                # Implement your summarizing function here.
                return messages


            summarizing_condition = MessageCompletionCondition()

            context = SummarizedChatCompletionContext(
                summarizing_func=summarizing_func,
                summarizing_condition=summarizing_condition,
            )

        .. code-block:: python
            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.model_context import SummarizedChatCompletionContext
            from autogen_core.model_context.conditions import MaxMessageCompletion
            from autogen_ext.summary import buffered_summary, buffered_summarized_chat_completion_context


            client = OpenAIChatCompletionClient(model="claude-3-haiku-20240307")

            context = SummarizedChatCompletionContext(
                summarizing_func=buffered_summary(buffer_count=2), summarizing_condition=MaxMessageCompletion(max_messages=2)
            )

            agent = AssistantAgent(
                "helper", model_client=client, system_message="You are a helpful agent", model_context=context
            )

    """

    component_config_schema = SummarizedChatCompletionContextConfig
    component_provider_override = "autogen_core.model_context.SummarizedChatCompletionContext"

    def __init__(
        self,
        summarizing_func: SummaryFunction | SummarizngFunction,
        summarizing_condition: MessageCompletionCondition,
        initial_messages: List[LLMMessage] | None = None,
        non_summarized_messages: List[LLMMessage] | None = None,
    ) -> None:
        super().__init__(initial_messages)

        self._non_summarized_messages: List[LLMMessage] = []
        if non_summarized_messages is not None:
            self._non_summarized_messages.extend(non_summarized_messages)

        self._non_summarized_messages.extend(self._messages)

        self._summarizing_func: SummaryFunction
        if isinstance(summarizing_func, BaseTool):
            # If the summarizing function is a tool, use it directly.
            self._summarizing_func = summarizing_func
        elif callable(summarizing_func):
            self._summarizing_func = SummaryFunction(summarizing_func)
        else:
            raise ValueError("summarizing_func must be a callable or a tool.")
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
            await self._summarizing_condition.reset()

    async def get_messages(self) -> List[LLMMessage]:
        return self._messages

    async def summary(self) -> None:
        summarized_message = self._summarizing_func.run(self._messages, self._non_summarized_messages)
        self._messages = summarized_message

    def _to_config(self) -> SummarizedChatCompletionContextConfig:
        return SummarizedChatCompletionContextConfig(
            summarizing_func=self._summarizing_func.dump_component(),
            summarizing_condition=self._summarizing_condition.dump_component(),
            initial_messages=self._initial_messages,
        )

    @classmethod
    def _from_config(cls, config: SummarizedChatCompletionContextConfig) -> Self:
        return cls(
            summarizing_func=SummaryFunction.load_component(config.summarizing_func),
            summarizing_condition=MessageCompletionCondition.load_component(config.summarizing_condition),
            initial_messages=config.initial_messages,
            non_summarized_messages=config.non_summarized_messages,
        )
