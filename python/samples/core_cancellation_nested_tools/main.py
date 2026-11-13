"""Demonstrate CancellationToken propagation through nested agent calls.

Run: ``python -m samples.core_cancellation_nested_tools.main``

When the outer handler delegates to another agent, pass
``cancellation_token=ctx.cancellation_token`` to ``send_message``. If you omit
it, cancelling the top-level request can succeed while the nested agent keeps
running.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

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
class Ping:
    """Empty payload for the demo."""


class SlowWorker(RoutedAgent):
    """Simulates a long-running nested operation."""

    def __init__(self) -> None:
        super().__init__("slow worker")
        self.started = False
        self.cancelled = False

    @message_handler
    async def on_ping(self, message: Ping, ctx: MessageContext) -> Ping:
        self.started = True
        sleep = asyncio.ensure_future(asyncio.sleep(100))
        ctx.cancellation_token.link_future(sleep)
        try:
            await sleep
            return Ping()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class Coordinator(RoutedAgent):
    """Forwards work to SlowWorker with the same cancellation token."""

    def __init__(self, worker_id: AgentId) -> None:
        super().__init__("coordinator")
        self.worker_id = worker_id
        self.cancelled = False

    @message_handler
    async def on_ping(self, message: Ping, ctx: MessageContext) -> Ping:
        response = self.send_message(
            message,
            self.worker_id,
            cancellation_token=ctx.cancellation_token,
        )
        try:
            return await response
        except asyncio.CancelledError:
            self.cancelled = True
            raise


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    await SlowWorker.register(runtime, "worker", SlowWorker)
    await Coordinator.register(
        runtime,
        "coordinator",
        lambda: Coordinator(
            AgentId("worker", key=AgentInstantiationContext.current_agent_id().key)
        ),
    )

    coordinator_id = AgentId("coordinator", key="default")
    worker_id = AgentId("worker", key="default")
    token = CancellationToken()

    task = asyncio.create_task(
        runtime.send_message(Ping(), coordinator_id, cancellation_token=token)
    )

    while runtime.unprocessed_messages_count == 0:
        await asyncio.sleep(0.01)
    await runtime.process_next()

    while runtime.unprocessed_messages_count == 0:
        await asyncio.sleep(0.01)
    await runtime.process_next()

    token.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("Top-level request cancelled (expected).")
    else:
        raise SystemExit("Expected cancellation to propagate.")

    coordinator = await runtime.try_get_underlying_agent_instance(
        coordinator_id, type=Coordinator
    )
    worker = await runtime.try_get_underlying_agent_instance(worker_id, type=SlowWorker)

    print(f"Coordinator cancelled: {coordinator.cancelled}")
    print(f"Worker started: {worker.started}, cancelled: {worker.cancelled}")

    if not (coordinator.cancelled and worker.started and worker.cancelled):
        raise SystemExit("Nested cancellation did not propagate as expected.")


if __name__ == "__main__":
    asyncio.run(main())
