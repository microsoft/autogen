import asyncio
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

STOP_WHEN_IDLE_TIMEOUT = 10


async def _stop_when_idle_or_fail(runtime: SingleThreadedAgentRuntime) -> None:
    """Stop the runtime when idle, failing fast if the queue accounting is broken.

    A regression in queue accounting (e.g., a dropped message never calling
    task_done()) makes Queue.join() hang forever; the timeout turns that hang
    into a test failure instead of stalling the test suite.
    """
    try:
        await asyncio.wait_for(runtime.stop_when_idle(), timeout=STOP_WHEN_IDLE_TIMEOUT)
    except asyncio.TimeoutError:
        pytest.fail(
            "stop_when_idle() did not return in time: the message queue accounting is "
            "likely broken (task_done() not called for a dropped or failed message)."
        )


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

    await _stop_when_idle_or_fail(runtime)

    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_drop_publish() -> None:
    class DropPublishInterventionHandler(DefaultInterventionHandler):
        async def on_publish(self, message: MessageType, *, message_context: MessageContext) -> Any:
            return DropMessage

    handler = DropPublishInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()
    await runtime.add_subscription(DefaultSubscription(agent_type="name"))

    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())

    # Regression test: a dropped published message must release its queue slot,
    # otherwise stop_when_idle() hangs forever on Queue.join().
    await _stop_when_idle_or_fail(runtime)

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

    await _stop_when_idle_or_fail(runtime)


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

    await _stop_when_idle_or_fail(runtime)

    long_running_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_raise_exception_on_publish() -> None:
    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler):  # type: ignore
        async def on_publish(self, message: MessageType, *, message_context: MessageContext) -> Any:  # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()
    await runtime.add_subscription(DefaultSubscription(agent_type="name"))

    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())

    # Regression test: an intervention handler raising on a published message
    # must still release the queue slot, otherwise stop_when_idle() hangs forever.
    await _stop_when_idle_or_fail(runtime)

    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 0


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

    await _stop_when_idle_or_fail(runtime)

    long_running_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1
