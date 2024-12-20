from typing import Any

import pytest
from autogen_core import AgentId, DropMessage, MessageContext, SingleThreadedAgentRuntime
from autogen_core._well_known_topics import is_rpc_request, is_rpc_response
from autogen_core.exceptions import MessageDroppedException
from autogen_test_utils import LoopbackAgent, MessageType


@pytest.mark.asyncio
async def test_intervention_count_messages() -> None:
    class DebugInterventionHandler:
        def __init__(self) -> None:
            self.num_messages = 0

        async def __call__(self, message: MessageType, message_context: MessageContext) -> MessageType:
            self.num_messages += 1
            return message

    handler = DebugInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])
    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    _response = await runtime.send_message(MessageType(), recipient=loopback, timeout=120)

    await runtime.stop()

    # 2 since request and response
    assert handler.num_messages == 2
    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 1


@pytest.mark.asyncio
async def test_intervention_drop_rpc_request() -> None:
    async def handler(message: Any, message_context: MessageContext) -> Any | type[DropMessage]:
        if is_rpc_request(message_context.topic_id.type):
            return DropMessage
        return message

    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    with pytest.raises(MessageDroppedException):
        _response = await runtime.send_message(MessageType(), recipient=loopback, timeout=120)

    await runtime.stop()

    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_drop_rpc_esponse() -> None:
    async def handler(message: Any, message_context: MessageContext) -> Any | type[DropMessage]:
        # Only drop the response and not the request!
        if is_rpc_response(message_context.topic_id.type):
            return DropMessage

        return message

    runtime = SingleThreadedAgentRuntime(intervention_handlers=[handler])

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    runtime.start()

    with pytest.raises(MessageDroppedException):
        _response = await runtime.send_message(MessageType(), recipient=loopback, timeout=120)

    await runtime.stop()
