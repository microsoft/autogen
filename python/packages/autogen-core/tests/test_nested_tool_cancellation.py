import asyncio
from dataclasses import dataclass, field

import pytest
from autogen_core import (
    AgentId,
    CancellationToken,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)
from autogen_core.tools import FunctionTool, StaticWorkbench, Workbench


@dataclass
class WorkRequest:
    pass


@dataclass
class NestedWorkState:
    started: asyncio.Event = field(default_factory=asyncio.Event)
    finished: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: bool = False
    completed: bool = False


def _cancellable_inner_tool(state: NestedWorkState, delay: float) -> FunctionTool:
    async def inner_compute(cancellation_token: CancellationToken) -> str:
        sleep = asyncio.ensure_future(asyncio.sleep(delay))
        cancellation_token.link_future(sleep)
        state.started.set()
        try:
            await sleep
            state.completed = True
            return "completed"
        except asyncio.CancelledError:
            state.cancelled = True
            raise
        finally:
            state.finished.set()

    return FunctionTool(inner_compute, description="A nested cancellable operation.")


class NestedWorkbenchAgent(RoutedAgent):
    def __init__(self, workbench: Workbench, *, forward_token: bool) -> None:
        super().__init__("An agent that calls a nested workbench tool")
        self._workbench = workbench
        self._forward_token = forward_token

    @message_handler
    async def on_work_request(self, message: WorkRequest, ctx: MessageContext) -> str:
        token = ctx.cancellation_token if self._forward_token else None
        result = await self._workbench.call_tool("inner_compute", {}, cancellation_token=token)
        return result.to_text()


@pytest.mark.asyncio
async def test_nested_function_tool_through_workbench_observes_cancellation() -> None:
    """Forwarding the same token into a nested FunctionTool cancels the inner operation."""
    inner_state = NestedWorkState()
    inner_tool = _cancellable_inner_tool(inner_state, delay=30)

    async def outer_compute(cancellation_token: CancellationToken) -> str:
        return await inner_tool.run_json({}, cancellation_token)

    outer_tool = FunctionTool(outer_compute, description="Forwards the token to inner_compute.")
    cancellation_token = CancellationToken()

    async with StaticWorkbench(tools=[outer_tool]) as workbench:
        call = asyncio.create_task(workbench.call_tool("outer_compute", {}, cancellation_token=cancellation_token))
        await inner_state.started.wait()
        cancellation_token.cancel()
        with pytest.raises(asyncio.CancelledError):
            await call

    await asyncio.wait_for(inner_state.finished.wait(), timeout=2)
    assert inner_state.cancelled
    assert not inner_state.completed
    assert cancellation_token.is_cancelled()


@pytest.mark.asyncio
async def test_message_handler_forwards_token_through_workbench() -> None:
    """A message handler must pass ctx.cancellation_token into Workbench.call_tool."""
    inner_state = NestedWorkState()
    inner_tool = _cancellable_inner_tool(inner_state, delay=30)

    async with StaticWorkbench(tools=[inner_tool]) as workbench:
        runtime = SingleThreadedAgentRuntime()
        await NestedWorkbenchAgent.register(
            runtime,
            "nested_workbench_agent",
            lambda: NestedWorkbenchAgent(workbench, forward_token=True),
        )
        agent_id = AgentId("nested_workbench_agent", "default")
        runtime.start()
        try:
            cancellation_token = CancellationToken()
            response = asyncio.create_task(
                runtime.send_message(WorkRequest(), recipient=agent_id, cancellation_token=cancellation_token)
            )
            await inner_state.started.wait()
            cancellation_token.cancel()
            with pytest.raises(asyncio.CancelledError):
                await response
            await asyncio.wait_for(inner_state.finished.wait(), timeout=2)
        finally:
            await runtime.stop()

    assert inner_state.cancelled
    assert not inner_state.completed


@pytest.mark.asyncio
async def test_omitting_token_at_workbench_leaves_nested_work_running() -> None:
    """Omitting the handler token creates a new workbench token outside the caller's boundary.

    `send_message` still raises CancelledError because the runtime links the
    response future, but the nested tool continues until its own token is cancelled.
    """
    inner_state = NestedWorkState()
    inner_tool = _cancellable_inner_tool(inner_state, delay=0.2)

    async with StaticWorkbench(tools=[inner_tool]) as workbench:
        runtime = SingleThreadedAgentRuntime()
        await NestedWorkbenchAgent.register(
            runtime,
            "nested_workbench_agent",
            lambda: NestedWorkbenchAgent(workbench, forward_token=False),
        )
        agent_id = AgentId("nested_workbench_agent", "default")
        runtime.start()
        try:
            cancellation_token = CancellationToken()
            response = asyncio.create_task(
                runtime.send_message(WorkRequest(), recipient=agent_id, cancellation_token=cancellation_token)
            )
            await inner_state.started.wait()
            cancellation_token.cancel()
            with pytest.raises(asyncio.CancelledError):
                await response
            await asyncio.wait_for(inner_state.finished.wait(), timeout=2)
        finally:
            await runtime.stop()

    assert not inner_state.cancelled
    assert inner_state.completed
