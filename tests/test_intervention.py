from dataclasses import dataclass

import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import Agent, AgentRuntime, CancellationToken
from agnext.core.exceptions import MessageDroppedException
from agnext.core.intervention import DefaultInterventionHandler, DropMessage


@dataclass
class MessageType:
    ...

class LoopbackAgent(TypeRoutedAgent): # type: ignore
    def __init__(self, name: str, router: AgentRuntime) -> None: # type: ignore
        super().__init__(name, "A loop back agent.", router)
        self.num_calls = 0


    @message_handler() # type: ignore
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType: # type: ignore
        self.num_calls += 1
        return message

@pytest.mark.asyncio
async def test_intervention_count_messages() -> None:

    class DebugInterventionHandler(DefaultInterventionHandler): # type: ignore
        def __init__(self) -> None:
            self.num_messages = 0

        async def on_send(self, message: MessageType, *, sender: Agent | None, recipient: Agent) -> MessageType: # type: ignore
            self.num_messages += 1
            return message

    handler = DebugInterventionHandler()
    runtime = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", runtime)
    response = runtime.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await runtime.process_next()

    assert handler.num_messages == 1
    assert long_running.num_calls == 1

@pytest.mark.asyncio
async def test_intervention_drop_send() -> None:

    class DropSendInterventionHandler(DefaultInterventionHandler): # type: ignore
        async def on_send(self, message: MessageType, *, sender: Agent | None, recipient: Agent) -> MessageType | type[DropMessage]: # type: ignore
            return DropMessage # type: ignore

    handler = DropSendInterventionHandler()
    runtime = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", runtime)
    response = runtime.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await runtime.process_next()

    with pytest.raises(MessageDroppedException):
        await response

    assert long_running.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_drop_response() -> None:

    class DropResponseInterventionHandler(DefaultInterventionHandler): # type: ignore
        async def on_response(self, message: MessageType, *, sender: Agent, recipient: Agent | None) -> MessageType | type[DropMessage]: # type: ignore
            return DropMessage # type: ignore

    handler = DropResponseInterventionHandler()
    runtime = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", runtime)
    response = runtime.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await runtime.process_next()

    with pytest.raises(MessageDroppedException):
        await response

    assert long_running.num_calls == 1

@pytest.mark.asyncio
async def test_intervention_raise_exception_on_send() -> None:

    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler): # type: ignore
        async def on_send(self, message: MessageType, *, sender: Agent | None, recipient: Agent) -> MessageType | type[DropMessage]: # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", runtime)
    response = runtime.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await runtime.process_next()

    with pytest.raises(InterventionException):
        await response

    assert long_running.num_calls == 0

@pytest.mark.asyncio
async def test_intervention_raise_exception_on_respond() -> None:

    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler): # type: ignore
        async def on_response(self, message: MessageType, *, sender: Agent, recipient: Agent | None) -> MessageType | type[DropMessage]: # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(before_send=handler)

    long_running = LoopbackAgent("name", runtime)
    response = runtime.send_message(MessageType(), recipient=long_running)

    while not response.done():
        await runtime.process_next()

    with pytest.raises(InterventionException):
        await response

    assert long_running.num_calls == 1
