import logging
from dataclasses import dataclass
from typing import Callable, cast

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext, TopicId
from autogen_core.components import RoutedAgent, TypeSubscription, message_handler
from test_utils import LoopbackAgent


@dataclass
class UnhandledMessageType: ...


@dataclass
class MessageType: ...


class CounterAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A loop back agent.")
        self.num_calls_rpc = 0
        self.num_calls_broadcast = 0

    @message_handler(match=lambda _, ctx: ctx.is_rpc)
    async def on_rpc_message(self, message: MessageType, ctx: MessageContext) -> MessageType:
        self.num_calls_rpc += 1
        return message

    @message_handler(match=lambda _, ctx: not ctx.is_rpc)
    async def on_broadcast_message(self, message: MessageType, ctx: MessageContext) -> None:
        self.num_calls_broadcast += 1


@pytest.mark.asyncio
async def test_routed_agent(caplog: pytest.LogCaptureFixture) -> None:
    runtime = SingleThreadedAgentRuntime()
    with caplog.at_level(logging.INFO):
        await runtime.register("loopback", LoopbackAgent, lambda: [TypeSubscription("default", "loopback")])
        runtime.start()
        await runtime.publish_message(UnhandledMessageType(), topic_id=TopicId("default", "default"))
        await runtime.stop_when_idle()
    assert any("Unhandled message: " in e.message for e in caplog.records)


@pytest.mark.asyncio
async def test_message_handler_router() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register("counter", CounterAgent, lambda: [TypeSubscription("default", "counter")])
    agent_id = AgentId(type="counter", key="default")

    # Send a broadcast message.
    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=TopicId("default", "default"))
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=CounterAgent)
    assert agent.num_calls_broadcast == 1
    assert agent.num_calls_rpc == 0

    # Send an RPC message.
    runtime.start()
    await runtime.send_message(MessageType(), recipient=agent_id)
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=CounterAgent)
    assert agent.num_calls_broadcast == 1
    assert agent.num_calls_rpc == 1


@dataclass
class TestMessage:
    value: str


class RoutedAgentMessageCustomMatch(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("")
        self.handler_one_called = False
        self.handler_two_called = False

    @staticmethod
    def match_one(message: TestMessage, ctx: MessageContext) -> bool:
        return message.value == "one"

    @message_handler(match=match_one)
    async def handler_one(self, message: TestMessage, ctx: MessageContext) -> None:
        self.handler_one_called = True

    @message_handler(match=cast(Callable[[TestMessage, MessageContext], bool], lambda msg, ctx: msg.value == "two"))
    async def handler_two(self, message: TestMessage, ctx: MessageContext) -> None:
        self.handler_two_called = True


@pytest.mark.asyncio
async def test_routed_agent_message_matching() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register("message_match", RoutedAgentMessageCustomMatch)
    agent_id = AgentId(type="message_match", key="default")

    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=RoutedAgentMessageCustomMatch)
    assert agent is not None
    assert agent.handler_one_called is False
    assert agent.handler_two_called is False

    runtime.start()
    await runtime.send_message(TestMessage("one"), recipient=agent_id)
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=RoutedAgentMessageCustomMatch)
    assert agent.handler_one_called is True
    assert agent.handler_two_called is False

    runtime.start()
    await runtime.send_message(TestMessage("two"), recipient=agent_id)
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=RoutedAgentMessageCustomMatch)
    assert agent.handler_one_called is True
    assert agent.handler_two_called is True
