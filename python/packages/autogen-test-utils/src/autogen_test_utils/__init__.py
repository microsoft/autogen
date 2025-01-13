from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autogen_core import (
    BaseAgent,
    Component,
    ComponentBase,
    ComponentModel,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    default_subscription,
    message_handler,
)
from pydantic import BaseModel


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
        self.received_messages: list[Any] = []

    @message_handler
    async def on_new_message(
        self, message: MessageType | ContentMessage, ctx: MessageContext
    ) -> MessageType | ContentMessage:
        self.num_calls += 1
        self.received_messages.append(message)
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

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any:
        raise NotImplementedError


class MyInnerConfig(BaseModel):
    inner_message: str


class MyInnerComponent(ComponentBase[MyInnerConfig], Component[MyInnerConfig]):
    component_config_schema = MyInnerConfig
    component_type = "custom"

    def __init__(self, inner_message: str):
        self.inner_message = inner_message

    def _to_config(self) -> MyInnerConfig:
        return MyInnerConfig(inner_message=self.inner_message)

    @classmethod
    def _from_config(cls, config: MyInnerConfig) -> MyInnerComponent:
        return cls(inner_message=config.inner_message)


class MyOuterConfig(BaseModel):
    outer_message: str
    inner_class: ComponentModel


class MyOuterComponent(ComponentBase[MyOuterConfig], Component[MyOuterConfig]):
    component_config_schema = MyOuterConfig
    component_type = "custom"

    def __init__(self, outer_message: str, inner_class: MyInnerComponent):
        self.outer_message = outer_message
        self.inner_class = inner_class

    def _to_config(self) -> MyOuterConfig:
        inner_component_config = self.inner_class.dump_component()
        return MyOuterConfig(outer_message=self.outer_message, inner_class=inner_component_config)

    @classmethod
    def _from_config(cls, config: MyOuterConfig) -> MyOuterComponent:
        inner = MyInnerComponent.load_component(config.inner_class)
        return cls(outer_message=config.outer_message, inner_class=inner)
