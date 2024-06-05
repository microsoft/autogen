import asyncio
from dataclasses import dataclass

import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import Agent, AgentRuntime, CancellationToken


@dataclass
class MessageType:
    ...

# Note for future reader:
# To do cancellation, only the token should be interacted with as a user
# If you cancel a future, it may not work as you expect.

class LongRunningAgent(TypeRoutedAgent):
    def __init__(self, name: str, router: AgentRuntime) -> None:
        super().__init__(name, router)
        self.called = False
        self.cancelled = False

    @message_handler()
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

class NestingLongRunningAgent(TypeRoutedAgent):
    def __init__(self, name: str, router: AgentRuntime, nested_agent: Agent) -> None:
        super().__init__(name, router)
        self.called = False
        self.cancelled = False
        self._nested_agent = nested_agent

    @message_handler()
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        self.called = True
        response = self._send_message(message, self._nested_agent, cancellation_token=cancellation_token)
        try:
            val = await response
            assert isinstance(val, MessageType)
            return val
        except asyncio.CancelledError:
            self.cancelled = True
            raise


@pytest.mark.asyncio
async def test_cancellation_with_token() -> None:
    router = SingleThreadedAgentRuntime()

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
    router = SingleThreadedAgentRuntime()

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
    assert long_running.called is False
    assert long_running.cancelled is False

@pytest.mark.asyncio
async def test_nested_cancellation_inner_called() -> None:
    router = SingleThreadedAgentRuntime()

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
