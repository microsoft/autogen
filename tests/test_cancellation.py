import asyncio
import pytest
from dataclasses import dataclass

from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.application_components.single_threaded_agent_runtime import SingleThreadedAgentRuntime
from agnext.core.agent import Agent
from agnext.core.agent_runtime import AgentRuntime
from agnext.core.cancellation_token import CancellationToken

@dataclass
class MessageType:
    ...

# Note for future reader:
# To do cancellation, only the token should be interacted with as a user
# If you cancel a future, it may not work as you expect.

class LongRunningAgent(TypeRoutedAgent[MessageType]):
    def __init__(self, name: str, router: AgentRuntime[MessageType]) -> None:
        super().__init__(name, router)
        self.called = False
        self.cancelled = False

    @message_handler(MessageType)
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        self.called = True
        sleep = asyncio.ensure_future(asyncio.sleep(100))
        cancellation_token.link_future(sleep)
        try:
            await sleep
            return MessageType()
        except asyncio.CancelledError:
            self.cancelled = True
            raise

class NestingLongRunningAgent(TypeRoutedAgent[MessageType]):
    def __init__(self, name: str, router: AgentRuntime[MessageType], nested_agent: Agent[MessageType]) -> None:
        super().__init__(name, router)
        self.called = False
        self.cancelled = False
        self._nested_agent = nested_agent

    @message_handler(MessageType)
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        self.called = True
        response = self._send_message(message, self._nested_agent, cancellation_token)
        try:
            return await response
        except asyncio.CancelledError:
            self.cancelled = True
            raise


@pytest.mark.asyncio
async def test_cancellation_with_token() -> None:
    router = SingleThreadedAgentRuntime[MessageType]()

    long_running = LongRunningAgent("name", router)
    token = CancellationToken()
    response = router.send_message(MessageType(), recipient=long_running, cancellation_token=token)
    assert not response.done()

    await router.process_next()
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    assert long_running.called
    assert long_running.cancelled



@pytest.mark.asyncio
async def test_nested_cancellation_only_outer_called() -> None:
    router = SingleThreadedAgentRuntime[MessageType]()

    long_running = LongRunningAgent("name", router)
    nested = NestingLongRunningAgent("nested", router, long_running)

    token = CancellationToken()
    response = router.send_message(MessageType(), nested, cancellation_token=token)
    assert not response.done()

    await router.process_next()
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    assert nested.called
    assert nested.cancelled
    assert long_running.called == False
    assert long_running.cancelled == False

@pytest.mark.asyncio
async def test_nested_cancellation_inner_called() -> None:
    router = SingleThreadedAgentRuntime[MessageType]()

    long_running = LongRunningAgent("name", router)
    nested = NestingLongRunningAgent("nested", router, long_running)

    token = CancellationToken()
    response = router.send_message(MessageType(), nested, cancellation_token=token)
    assert not response.done()

    await router.process_next()
    # allow the inner agent to process
    await router.process_next()
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    assert nested.called
    assert nested.cancelled
    assert long_running.called
    assert long_running.cancelled