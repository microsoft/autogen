from dataclasses import dataclass
from typing import Any, List

from autogen_core.base import BaseAgent, MessageContext
from autogen_core.components import DefaultTopicId, RoutedAgent, default_subscription, message_handler
from autogen_core.components.models._model_client import ChatCompletionClient
from autogen_core.components.models._types import SystemMessage


@dataclass
class MessageType: ...


@dataclass
class CascadingMessageType:
    round: int


@dataclass
class ContentMessage:
    content: str


class LoopbackAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A loop back agent.")
        self.num_calls = 0

    @message_handler
    async def on_new_message(
        self, message: MessageType | ContentMessage, ctx: MessageContext
    ) -> MessageType | ContentMessage:
        self.num_calls += 1
        return message


@default_subscription
class LoopbackAgentWithDefaultSubscription(LoopbackAgent): ...


@default_subscription
class CascadingAgent(RoutedAgent):
    def __init__(self, max_rounds: int) -> None:
        super().__init__("A cascading agent.")
        self.num_calls = 0
        self.max_rounds = max_rounds

    @message_handler
    async def on_new_message(self, message: CascadingMessageType, ctx: MessageContext) -> None:
        self.num_calls += 1
        if message.round == self.max_rounds:
            return
        await self.publish_message(CascadingMessageType(round=message.round + 1), topic_id=DefaultTopicId())


class NoopAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("A no op agent")

    async def on_message(self, message: Any, ctx: MessageContext) -> Any:
        raise NotImplementedError


class LLMAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("LLM Agent!")
        self._chat_history: List[ContentMessage] = []
        self._model_client = model_client
        self.num_calls = 0

    @message_handler
    async def on_new_message(self, message: ContentMessage, ctx: MessageContext) -> None:
        self._chat_history.append(message)
        self.num_calls += 1
        completion = await self._model_client.create(messages=self._fixed_message_history_type)
        if isinstance(completion.content, str):
            await self.publish_message(ContentMessage(content=completion.content), DefaultTopicId())
        else:
            raise TypeError(f"Completion content of type {type(completion.content)} is not supported")

    @property
    def _fixed_message_history_type(self) -> List[SystemMessage]:
        return [SystemMessage(msg.content) for msg in self._chat_history]


@default_subscription
class LLMAgentWithDefaultSubscription(LLMAgent): ...
