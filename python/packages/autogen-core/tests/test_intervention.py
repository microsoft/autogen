from typing import Any

import pytest
from autogen_core import (
    AgentId,
    DefaultInterventionHandler,
    DefaultSubscription,
    DefaultTopicId,
    DropMessage,
    MessageContext,
    SingleThreadedAgentRuntime,
)
from autogen_core.exceptions import MessageDroppedException
from autogen_test_utils import LoopbackAgent, MessageType


@pytest.mark.asyncio
async def test_intervention_count_messages() -> None:
    class DebugInterventionHandler(DefaultInterventionHandler):
        def __init__(self) -> None:
            self.num_send_messages = 0
            self.num_publish_messages = 0
            self.num_response_messages = 0

        async def on_send(self, message: Any, *, message_context: MessageContext, recipient: AgentId) -> Any:
            self.num_send_messages += 1
            return message

        async def on_publish(self, message: Any, *, message_context: MessageContext) -> Any:
            self.num_publish_messages += 1
            return message

        async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any:
            self.num_response_messages += 1
            return message

    handler = DebugInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])
    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    _response = await runtime.send_message(MessageType(), recipient=loopback)

    await runtime.stop_when_idle()

    assert handler.num_send_messages == 1
    assert handler.num_response_messages == 1
    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 1

    runtime.start()
    await runtime.add_subscription(DefaultSubscription(agent_type="name"))

    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())

    await runtime.stop_when_idle()
    assert loopback_agent.num_calls == 2
    assert handler.num_publish_messages == 1


@pytest.mark.asyncio
async def test_intervention_drop_send() -> None:
    class DropSendInterventionHandler(DefaultInterventionHandler):
        async def on_send(
            self, message: MessageType, *, message_context: MessageContext, recipient: AgentId
        ) -> MessageType | type[DropMessage]:
            return DropMessage

    handler = DropSendInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    with pytest.raises(MessageDroppedException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await runtime.stop()

    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_drop_response() -> None:
    class DropResponseInterventionHandler(DefaultInterventionHandler):
        async def on_response(
            self, message: MessageType, *, sender: AgentId, recipient: AgentId | None
        ) -> MessageType | type[DropMessage]:
            return DropMessage

    handler = DropResponseInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    with pytest.raises(MessageDroppedException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await runtime.stop()


@pytest.mark.asyncio
async def test_intervention_raise_exception_on_send() -> None:
    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler):  # type: ignore
        async def on_send(
            self, message: MessageType, *, message_context: MessageContext, recipient: AgentId
        ) -> MessageType | type[DropMessage]:  # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    with pytest.raises(InterventionException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await runtime.stop()

    long_running_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_raise_exception_on_respond() -> None:
    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler):  # type: ignore
        async def on_response(
            self, message: MessageType, *, sender: AgentId, recipient: AgentId | None
        ) -> MessageType | type[DropMessage]:  # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()
    with pytest.raises(InterventionException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await runtime.stop()

    long_running_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1
