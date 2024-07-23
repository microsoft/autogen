import asyncio
from dataclasses import dataclass

import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentId, CancellationToken


@dataclass
class MessageType:
    ...

# Note for future reader:
# To do cancellation, only the token should be interacted with as a user
# If you cancel a future, it may not work as you expect.

class LongRunningAgent(TypeRoutedAgent):
    def __init__(self) -> None:
        super().__init__("A long running agent")
        self.called = False
        self.cancelled = False

    @message_handler
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
    def __init__(self, nested_agent: AgentId) -> None:
        super().__init__("A nesting long running agent")
        self.called = False
        self.cancelled = False
        self._nested_agent = nested_agent

    @message_handler
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        self.called = True
        response = self.send_message(message, self._nested_agent, cancellation_token=cancellation_token)
        try:
            val = await response
            assert isinstance(val, MessageType)
            return val
        except asyncio.CancelledError:
            self.cancelled = True
            raise


@pytest.mark.asyncio
async def test_cancellation_with_token() -> None:
    runtime = SingleThreadedAgentRuntime()

    long_running = await runtime.register_and_get("long_running", LongRunningAgent)
    token = CancellationToken()
    response = asyncio.create_task(runtime.send_message(MessageType(), recipient=long_running, cancellation_token=token))
    assert not response.done()

    while len(runtime.unprocessed_messages) == 0:
        await asyncio.sleep(0.01)

    await runtime.process_next()

    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    long_running_agent: LongRunningAgent = await runtime._get_agent(long_running) # type: ignore
    assert long_running_agent.called
    assert long_running_agent.cancelled



@pytest.mark.asyncio
async def test_nested_cancellation_only_outer_called() -> None:
    runtime = SingleThreadedAgentRuntime()

    long_running = await runtime.register_and_get("long_running", LongRunningAgent)
    nested = await runtime.register_and_get("nested", lambda: NestingLongRunningAgent(long_running))

    token = CancellationToken()
    response = asyncio.create_task(runtime.send_message(MessageType(), nested, cancellation_token=token))
    assert not response.done()

    while len(runtime.unprocessed_messages) == 0:
        await asyncio.sleep(0.01)

    await runtime.process_next()
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    nested_agent: NestingLongRunningAgent = await runtime._get_agent(nested) # type: ignore
    assert nested_agent.called
    assert nested_agent.cancelled
    long_running_agent: LongRunningAgent = await runtime._get_agent(long_running) # type: ignore
    assert long_running_agent.called is False
    assert long_running_agent.cancelled is False

@pytest.mark.asyncio
async def test_nested_cancellation_inner_called() -> None:
    runtime = SingleThreadedAgentRuntime()

    long_running = await runtime.register_and_get("long_running", LongRunningAgent )
    nested = await runtime.register_and_get("nested", lambda: NestingLongRunningAgent(long_running))

    token = CancellationToken()
    response = asyncio.create_task(runtime.send_message(MessageType(), nested, cancellation_token=token))
    assert not response.done()

    while len(runtime.unprocessed_messages) == 0:
        await asyncio.sleep(0.01)

    await runtime.process_next()
    # allow the inner agent to process
    await runtime.process_next()
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    nested_agent: NestingLongRunningAgent = await runtime._get_agent(nested) # type: ignore
    assert nested_agent.called
    assert nested_agent.cancelled
    long_running_agent: LongRunningAgent = await runtime._get_agent(long_running) # type: ignore
    assert long_running_agent.called
    assert long_running_agent.cancelled
