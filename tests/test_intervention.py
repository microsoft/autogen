import pytest
from dataclasses import dataclass

from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.application_components import SingleThreadedAgentRuntime
from agnext.core import Agent
from agnext.core import AgentRuntime
from agnext.core import CancellationToken
from agnext.core.exceptions import MessageDroppedException
from agnext.core.intervention import DefaultInterventionHandler, DropMessage

@dataclass
class MessageType:
    ...

class LoopbackAgent(TypeRoutedAgent):
    def __init__(self, name: str, router: AgentRuntime) -> None:
        super().__init__(name, router)
        self.num_calls = 0


    @message_handler(MessageType)
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        self.num_calls += 1
        return message

@pytest.mark.asyncio
async def test_intervention_count_messages() -> None:

    class DebugInterventionHandler(DefaultInterventionHandler):
        def __init__(self) -> None:
            self.num_messages = 0

        async def on_send(self, message: MessageType, *, sender: Agent | None, recipient: Agent) -> MessageType:
            self.num_messages += 1
            return message

    handler = DebugInterventionHandler()
    router = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", router)
    response = router.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await router.process_next()

    assert handler.num_messages == 1
    assert long_running.num_calls == 1

@pytest.mark.asyncio
async def test_intervention_drop_send() -> None:

    class DropSendInterventionHandler(DefaultInterventionHandler):
        async def on_send(self, message: MessageType, *, sender: Agent | None, recipient: Agent) -> MessageType | type[DropMessage]:
            return DropMessage

    handler = DropSendInterventionHandler()
    router = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", router)
    response = router.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await router.process_next()

    with pytest.raises(MessageDroppedException):
        await response

    assert long_running.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_drop_response() -> None:

    class DropResponseInterventionHandler(DefaultInterventionHandler):
        async def on_response(self, message: MessageType, *, sender: Agent, recipient: Agent | None) -> MessageType | type[DropMessage]:
            return DropMessage

    handler = DropResponseInterventionHandler()
    router = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", router)
    response = router.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await router.process_next()

    with pytest.raises(MessageDroppedException):
        await response

    assert long_running.num_calls == 1
