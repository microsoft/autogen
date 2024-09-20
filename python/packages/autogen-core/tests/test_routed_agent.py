import logging
from dataclasses import dataclass
from typing import Callable, cast

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext, TopicId
from autogen_core.components import RoutedAgent, TypeSubscription, event, message_handler, rpc
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

    @message_handler(match=cast(Callable[[TestMessage, MessageContext], bool], lambda msg, ctx: msg.value == "two"))  # type: ignore
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


class EventAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("An event agent.")
        self.num_calls = [0, 0]

    @event(match=lambda msg, ctx: msg.value == "one")  # type: ignore
    async def on_event_one(self, message: TestMessage, ctx: MessageContext) -> None:
        self.num_calls[0] += 1

    @event(match=lambda msg, ctx: msg.value == "two")  # type: ignore
    async def on_event_two(self, message: TestMessage, ctx: MessageContext) -> None:
        self.num_calls[1] += 1


@pytest.mark.asyncio
async def test_event() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register("counter", EventAgent, lambda: [TypeSubscription("default", "counter")])
    agent_id = AgentId(type="counter", key="default")

    # Send a broadcast message.
    runtime.start()
    await runtime.publish_message(TestMessage("one"), topic_id=TopicId("default", "default"))
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=EventAgent)
    assert agent.num_calls[0] == 1
    assert agent.num_calls[1] == 0

    # Send another broadcast message.
    runtime.start()
    await runtime.publish_message(TestMessage("two"), topic_id=TopicId("default", "default"))
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=EventAgent)
    assert agent.num_calls[0] == 1
    assert agent.num_calls[1] == 1

    # Send an RPC message, expect no change.
    runtime.start()
    await runtime.send_message(TestMessage("one"), recipient=agent_id)
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=EventAgent)
    assert agent.num_calls[0] == 1
    assert agent.num_calls[1] == 1


class RPCAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("An RPC agent.")
        self.num_calls = [0, 0]

    @rpc(match=lambda msg, ctx: msg.value == "one")  # type: ignore
    async def on_rpc_one(self, message: TestMessage, ctx: MessageContext) -> TestMessage:
        self.num_calls[0] += 1
        return message

    @rpc(match=lambda msg, ctx: msg.value == "two")  # type: ignore
    async def on_rpc_two(self, message: TestMessage, ctx: MessageContext) -> TestMessage:
        self.num_calls[1] += 1
        return message


@pytest.mark.asyncio
async def test_rpc() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register("counter", RPCAgent, lambda: [TypeSubscription("default", "counter")])
    agent_id = AgentId(type="counter", key="default")

    # Send an RPC message.
    runtime.start()
    await runtime.send_message(TestMessage("one"), recipient=agent_id)
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=RPCAgent)
    assert agent.num_calls[0] == 1
    assert agent.num_calls[1] == 0

    # Send another RPC message.
    runtime.start()
    await runtime.send_message(TestMessage("two"), recipient=agent_id)
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=RPCAgent)
    assert agent.num_calls[0] == 1
    assert agent.num_calls[1] == 1

    # Send a broadcast message, expect no change.
    runtime.start()
    await runtime.publish_message(TestMessage("one"), topic_id=TopicId("default", "default"))
    await runtime.stop_when_idle()
    agent = await runtime.try_get_underlying_agent_instance(agent_id, type=RPCAgent)
    assert agent.num_calls[0] == 1
    assert agent.num_calls[1] == 1
