from dataclasses import dataclass
from typing import Any

from autogen_core.base import BaseAgent, MessageContext
from autogen_core.components import DefaultTopicId, RoutedAgent, default_subscription, message_handler


@dataclass
class MessageType: ...


@dataclass
class CascadingMessageType:
    round: int


class LoopbackAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A loop back agent.")
        self.num_calls = 0

    @message_handler
    async def on_new_message(self, message: MessageType, ctx: MessageContext) -> MessageType:
        self.num_calls += 1
        return message


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


@dataclass
class MyMessage:
    content: str


@default_subscription
class MyAgent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__("My agent")
        self._name = name
        self._counter = 0

    @message_handler
    async def my_message_handler(self, message: MyMessage, ctx: MessageContext) -> None:
        self._counter += 1
        if self._counter > 5:
            return
        content = f"{self._name}: Hello x {self._counter}"
        await self.publish_message(MyMessage(content=content), DefaultTopicId())
