import asyncio
import threading
from dataclasses import dataclass
from functools import partial
from typing import Callable

import pytest
from autogen_core import (
    AgentId,
    AgentInstantiationContext,
    CancellationToken,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)


@dataclass
class MessageType: ...


def _run_without_deadlock(operation: Callable[[], None]) -> None:
    errors: list[BaseException] = []

    def run() -> None:
        try:
            operation()
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive(), "Cancellation callback deadlocked"
    assert not errors


@pytest.mark.parametrize("already_cancelled", [False, True])
@pytest.mark.parametrize("action", ["query", "cancel", "register"])
def test_cancellation_callbacks_can_reenter_token(already_cancelled: bool, action: str) -> None:
    token = CancellationToken()
    calls: list[str] = []

    def callback() -> None:
        calls.append("outer")
        if action == "query":
            assert token.is_cancelled()
        elif action == "cancel":
            token.cancel()
        else:
            token.add_callback(lambda: calls.append("inner"))

    def cancel() -> None:
        if already_cancelled:
            token.cancel()
            token.add_callback(callback)
        else:
            token.add_callback(callback)
            token.cancel()
        token.cancel()

    _run_without_deadlock(cancel)
    assert calls == (["outer", "inner"] if action == "register" else ["outer"])


def test_cancellation_propagation_can_query_parent_token() -> None:
    parent = CancellationToken()
    child = CancellationToken()
    observed: list[bool] = []
    parent.add_callback(child.cancel)
    child.add_callback(lambda: observed.append(parent.is_cancelled()))

    _run_without_deadlock(parent.cancel)

    assert parent.is_cancelled()
    assert child.is_cancelled()
    assert observed == [True]


def test_cancellation_callbacks_keep_registration_order_and_run_once() -> None:
    token = CancellationToken()
    calls: list[int] = []
    for value in range(3):
        token.add_callback(partial(calls.append, value))

    token.cancel()
    token.cancel()
    token.add_callback(lambda: calls.append(3))

    assert calls == [0, 1, 2, 3]


def test_callbacks_are_not_lost_when_registration_races_with_cancellation() -> None:
    token = CancellationToken()
    barrier = threading.Barrier(10)
    calls: list[int] = []
    errors: list[BaseException] = []
    calls_lock = threading.Lock()

    def record(value: int) -> None:
        with calls_lock:
            calls.append(value)

    def register_or_cancel(value: int) -> None:
        try:
            barrier.wait(timeout=5)
            if value < 8:
                token.add_callback(lambda: record(value))
            else:
                token.cancel()
        except BaseException as exc:
            errors.append(exc)

    workers = [threading.Thread(target=register_or_cancel, args=(value,), daemon=True) for value in range(10)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5)

    assert all(not worker.is_alive() for worker in workers)
    assert not errors
    assert sorted(calls) == list(range(8))


# Note for future reader:
# To do cancellation, only the token should be interacted with as a user
# If you cancel a future, it may not work as you expect.


class LongRunningAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A long running agent")
        self.called = False
        self.cancelled = False

    @message_handler
    async def on_new_message(self, message: MessageType, ctx: MessageContext) -> MessageType:
        self.called = True
        sleep = asyncio.ensure_future(asyncio.sleep(100))
        ctx.cancellation_token.link_future(sleep)
        try:
            await sleep
            return MessageType()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class NestingLongRunningAgent(RoutedAgent):
    def __init__(self, nested_agent: AgentId) -> None:
        super().__init__("A nesting long running agent")
        self.called = False
        self.cancelled = False
        self._nested_agent = nested_agent

    @message_handler
    async def on_new_message(self, message: MessageType, ctx: MessageContext) -> MessageType:
        self.called = True
        response = self.send_message(message, self._nested_agent, cancellation_token=ctx.cancellation_token)
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

    await LongRunningAgent.register(runtime, "long_running", LongRunningAgent)
    agent_id = AgentId("long_running", key="default")
    token = CancellationToken()
    response = asyncio.create_task(runtime.send_message(MessageType(), recipient=agent_id, cancellation_token=token))
    assert not response.done()

    while runtime.unprocessed_messages_count == 0:
        await asyncio.sleep(0.01)

    await runtime._process_next()  # type: ignore

    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LongRunningAgent)
    assert long_running_agent.called
    assert long_running_agent.cancelled


@pytest.mark.asyncio
async def test_nested_cancellation_only_outer_called() -> None:
    runtime = SingleThreadedAgentRuntime()

    await LongRunningAgent.register(runtime, "long_running", LongRunningAgent)
    await NestingLongRunningAgent.register(
        runtime,
        "nested",
        lambda: NestingLongRunningAgent(AgentId("long_running", key=AgentInstantiationContext.current_agent_id().key)),
    )

    long_running_id = AgentId("long_running", key="default")
    nested_id = AgentId("nested", key="default")
    token = CancellationToken()
    response = asyncio.create_task(runtime.send_message(MessageType(), nested_id, cancellation_token=token))
    assert not response.done()

    while runtime.unprocessed_messages_count == 0:
        await asyncio.sleep(0.01)

    await runtime._process_next()  # type: ignore
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    nested_agent = await runtime.try_get_underlying_agent_instance(nested_id, type=NestingLongRunningAgent)
    assert nested_agent.called
    assert nested_agent.cancelled
    long_running_agent = await runtime.try_get_underlying_agent_instance(long_running_id, type=LongRunningAgent)
    assert long_running_agent.called is False
    assert long_running_agent.cancelled is False


@pytest.mark.asyncio
async def test_nested_cancellation_inner_called() -> None:
    runtime = SingleThreadedAgentRuntime()

    await LongRunningAgent.register(runtime, "long_running", LongRunningAgent)
    await NestingLongRunningAgent.register(
        runtime,
        "nested",
        lambda: NestingLongRunningAgent(AgentId("long_running", key=AgentInstantiationContext.current_agent_id().key)),
    )

    long_running_id = AgentId("long_running", key="default")
    nested_id = AgentId("nested", key="default")

    token = CancellationToken()
    response = asyncio.create_task(runtime.send_message(MessageType(), nested_id, cancellation_token=token))
    assert not response.done()

    while runtime.unprocessed_messages_count == 0:
        await asyncio.sleep(0.01)

    await runtime._process_next()  # type: ignore
    # allow the inner agent to process
    await runtime._process_next()  # type: ignore
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await response

    assert response.done()
    nested_agent = await runtime.try_get_underlying_agent_instance(nested_id, type=NestingLongRunningAgent)
    assert nested_agent.called
    assert nested_agent.cancelled
    long_running_agent = await runtime.try_get_underlying_agent_instance(long_running_id, type=LongRunningAgent)
    assert long_running_agent.called
    assert long_running_agent.cancelled
