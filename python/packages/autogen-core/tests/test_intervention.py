import pytest
from autogen_core import AgentId
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base.intervention import DefaultInterventionHandler, DropMessage
from autogen_core.exceptions import MessageDroppedException
from test_utils import LoopbackAgent, MessageType


@pytest.mark.asyncio
async def test_intervention_count_messages() -> None:
    class DebugInterventionHandler(DefaultInterventionHandler):
        def __init__(self) -> None:
            self.num_messages = 0

        async def on_send(self, message: MessageType, *, sender: AgentId | None, recipient: AgentId) -> MessageType:
            self.num_messages += 1
            return message

    handler = DebugInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])
    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    _response = await runtime.send_message(MessageType(), recipient=loopback)

    await runtime.stop()

    assert handler.num_messages == 1
    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 1


@pytest.mark.asyncio
async def test_intervention_drop_send() -> None:
    class DropSendInterventionHandler(DefaultInterventionHandler):
        async def on_send(
            self, message: MessageType, *, sender: AgentId | None, recipient: AgentId
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
            self, message: MessageType, *, sender: AgentId | None, recipient: AgentId
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
