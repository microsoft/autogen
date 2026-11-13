"""Exercise terminal RPC outcomes and connection ownership with local gRPC."""

# Ownership assertions intentionally inspect pending requests and cleanup tasks.
# pyright: reportPrivateUsage=false

import asyncio
from typing import AsyncIterator, Callable

import pytest
import pytest_asyncio
from autogen_core import (
    AgentId,
    CancellationToken,
    MessageContext,
    RoutedAgent,
    TopicId,
    TypeSubscription,
    message_handler,
    try_get_known_serializers_for_type,
)
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime, GrpcWorkerAgentRuntimeHost
from autogen_test_utils import MessageType

pytestmark = [pytest.mark.grpc, pytest.mark.asyncio]


async def wait_until(predicate: Callable[[], bool]) -> None:
    async def wait() -> None:
        while not predicate():
            await asyncio.sleep(0.001)

    await asyncio.wait_for(wait(), timeout=1)


class WaitingAgent(RoutedAgent):
    def __init__(self, started: asyncio.Event, release: asyncio.Event, *, fail: bool = False) -> None:
        super().__init__("Controlled local RPC handler")
        self.started = started
        self.release = release
        self.fail = fail

    @message_handler
    async def respond(self, message: MessageType, ctx: MessageContext) -> MessageType:
        self.started.set()
        await self.release.wait()
        if self.fail:
            raise ValueError("application failure")
        return message


class InvalidResultAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("An agent whose result has no registered serializer")

    @message_handler
    async def respond(self, message: MessageType, ctx: MessageContext) -> object:
        return object()


class LocalCluster:
    def __init__(self, port: int) -> None:
        self.address = f"127.0.0.1:{port}"
        self.host = GrpcWorkerAgentRuntimeHost(address=self.address)
        self.workers: list[GrpcWorkerAgentRuntime] = []
        self.release = asyncio.Event()
        self.started = asyncio.Event()

    async def worker(self) -> GrpcWorkerAgentRuntime:
        worker = GrpcWorkerAgentRuntime(host_address=self.address)
        worker.add_message_serializer(try_get_known_serializers_for_type(MessageType))
        await worker.start()
        self.workers.append(worker)
        return worker

    async def register_waiter(self, worker: GrpcWorkerAgentRuntime, *, fail: bool = False) -> None:
        await WaitingAgent.register(worker, "waiting", lambda: WaitingAgent(self.started, self.release, fail=fail))

    async def close(self) -> None:
        self.release.set()
        for worker in self.workers:
            try:
                await asyncio.wait_for(worker.stop(), timeout=1)
            except (Exception, asyncio.CancelledError):
                # Baseline regressions must not leave a live read loop behind
                # when the old stop path fails before reaching its cleanup.
                if worker._read_task is not None:
                    worker._read_task.cancel()
                    await asyncio.gather(worker._read_task, return_exceptions=True)
        if self.host._serve_task is not None:
            await self.host.stop(grace=0)


@pytest_asyncio.fixture  # type: ignore
async def cluster(unused_tcp_port: int) -> AsyncIterator[LocalCluster]:
    cluster = LocalCluster(unused_tcp_port)
    cluster.host.start()
    try:
        yield cluster
    finally:
        await cluster.close()


async def test_unknown_recipient_returns_an_rpc_error(cluster: LocalCluster) -> None:
    worker = await cluster.worker()
    with pytest.raises(Exception, match="not found|not registered|unavailable"):
        await asyncio.wait_for(worker.send_message(MessageType(), AgentId("missing", "default")), timeout=1)


async def test_handler_exception_reaches_the_requesting_worker(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver, fail=True)
    cluster.release.set()
    with pytest.raises(Exception, match="application failure"):
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("waiting", "default")), timeout=1)


async def test_host_loss_finishes_outstanding_rpc(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver)
    request = asyncio.create_task(sender.send_message(MessageType(), AgentId("waiting", "default")))
    try:
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        await cluster.host.stop(grace=0)
        with pytest.raises(Exception, match="closed|disconnect|unavailable|UNAVAILABLE"):
            await asyncio.wait_for(request, timeout=1)
    finally:
        cluster.release.set()
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)


async def test_stop_cancels_owned_handlers_and_finishes_callers(cluster: LocalCluster) -> None:
    worker = await cluster.worker()
    await cluster.register_waiter(worker)
    request = asyncio.create_task(worker.send_message(MessageType(), AgentId("waiting", "default")))
    try:
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        await asyncio.wait_for(worker.stop(), timeout=1)
        with pytest.raises(Exception, match="stopped|closed|disconnect"):
            await asyncio.wait_for(request, timeout=1)
    finally:
        cluster.release.set()
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)


async def test_restart_restores_rpc_dispatch_and_registered_factories(cluster: LocalCluster) -> None:
    worker = await cluster.worker()
    await cluster.register_waiter(worker)
    cluster.release.set()
    assert isinstance(await worker.send_message(MessageType(), AgentId("waiting", "default")), MessageType)
    await worker.stop()
    await worker.start()
    assert isinstance(
        await asyncio.wait_for(worker.send_message(MessageType(), AgentId("waiting", "default")), timeout=1),
        MessageType,
    )


async def test_target_stop_reports_failure_to_another_worker(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver)
    request = asyncio.create_task(sender.send_message(MessageType(), AgentId("waiting", "default")))
    try:
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        await asyncio.wait_for(receiver.stop(), timeout=1)
        with pytest.raises(Exception, match="stopped|closed|disconnect|cancel"):
            await asyncio.wait_for(request, timeout=1)
    finally:
        cluster.release.set()
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)


async def test_factory_failure_returns_an_rpc_error(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()

    def fail_factory() -> WaitingAgent:
        raise ValueError("factory failed")

    await receiver.register_factory("broken", fail_factory)
    with pytest.raises(Exception, match="factory failed"):
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("broken", "default")), timeout=1)


async def test_result_serialization_failure_returns_an_rpc_error(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await InvalidResultAgent.register(receiver, "broken", InvalidResultAgent)
    with pytest.raises(Exception, match="serializ|type|object"):
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("broken", "default")), timeout=1)


async def test_request_decode_failure_returns_an_rpc_error(cluster: LocalCluster) -> None:
    sender = await cluster.worker()
    # A legitimate worker can omit a message serializer; that failure must be
    # reported to the caller instead of leaving its RPC pending indefinitely.
    receiver = GrpcWorkerAgentRuntime(host_address=cluster.address)
    await receiver.start()
    cluster.workers.append(receiver)
    await receiver.register_factory("waiting", lambda: WaitingAgent(cluster.started, cluster.release))
    cluster.release.set()
    with pytest.raises(Exception, match="serializ|type|content"):
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("waiting", "default")), timeout=1)


async def test_token_cancellation_finishes_caller_and_late_reply_is_harmless(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver)
    token = CancellationToken()
    request = asyncio.create_task(
        sender.send_message(MessageType(), AgentId("waiting", "default"), cancellation_token=token)
    )
    try:
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        token.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(request, timeout=1)
        cluster.release.set()
        assert isinstance(
            await asyncio.wait_for(sender.send_message(MessageType(), AgentId("waiting", "default")), timeout=1),
            MessageType,
        )
    finally:
        cluster.release.set()
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)


async def test_restart_restores_subscriptions_for_remote_publish(cluster: LocalCluster) -> None:
    publisher, subscriber = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(subscriber)
    await subscriber.add_subscription(TypeSubscription("updates", "waiting"))
    subscription_ids = {subscription.id for subscription in subscriber._subscription_manager.subscriptions}
    cluster.release.set()
    for _ in range(3):
        await subscriber.stop()
        await subscriber.start()
        cluster.started.clear()
        await publisher.publish_message(MessageType(), TopicId("updates", "default"))
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        assert {
            subscription.id for subscription in cluster.host._servicer._subscription_manager.subscriptions
        } == subscription_ids


async def test_sender_disconnect_releases_host_relay_before_target_finishes(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver)
    request = asyncio.create_task(sender.send_message(MessageType(), AgentId("waiting", "default")))
    await asyncio.wait_for(cluster.started.wait(), timeout=1)
    await sender.stop()
    with pytest.raises(ConnectionError):
        await request
    await wait_until(lambda: not cluster.host._servicer._pending_responses)
    assert not cluster.host._servicer._response_owners
    # The target can still complete and publish a now-unclaimed response.
    cluster.release.set()
    await sender.start()
    assert isinstance(
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("waiting", "default")), timeout=1),
        MessageType,
    )


@pytest.mark.parametrize("shutdown", ["sender", "target", "host"])
async def test_disconnect_settles_all_pending_requests(cluster: LocalCluster, shutdown: str) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver)
    requests = [
        asyncio.create_task(sender.send_message(MessageType(), AgentId("waiting", str(index)))) for index in range(20)
    ]
    try:
        await wait_until(lambda: len(cluster.host._servicer._response_owners) == len(requests))
        if shutdown == "sender":
            await sender.stop()
        elif shutdown == "target":
            await receiver.stop()
        else:
            await cluster.host.stop(grace=0)
        outcomes = await asyncio.wait_for(asyncio.gather(*requests, return_exceptions=True), timeout=1)
        assert all(isinstance(outcome, Exception) for outcome in outcomes)
        assert not sender._pending_requests
        await wait_until(lambda: not cluster.host._servicer._response_owners)
        assert not cluster.host._servicer._pending_responses
    finally:
        for request in requests:
            request.cancel()
        await asyncio.gather(*requests, return_exceptions=True)


class CleanupAgent(RoutedAgent):
    def __init__(self, entered: asyncio.Event, cleanup_started: asyncio.Event, cleanup_release: asyncio.Event) -> None:
        super().__init__("A handler with asynchronous resource cleanup")
        self.entered = entered
        self.cleanup_started = cleanup_started
        self.cleanup_release = cleanup_release
        self.cleaned = asyncio.Event()

    @message_handler
    async def respond(self, message: MessageType, ctx: MessageContext) -> MessageType:
        try:
            self.entered.set()
            await asyncio.Event().wait()
            return message
        finally:
            self.cleanup_started.set()
            await self.cleanup_release.wait()
            self.cleaned.set()


async def test_cancelling_stop_still_joins_handler_cleanup(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()
    await CleanupAgent.register(
        receiver, "cleanup", lambda: CleanupAgent(cluster.started, cleanup_started, cleanup_release)
    )
    request = asyncio.create_task(sender.send_message(MessageType(), AgentId("cleanup", "default")))
    stopping: asyncio.Task[None] | None = None
    try:
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        stopping = asyncio.create_task(receiver.stop())
        await asyncio.wait_for(cleanup_started.wait(), timeout=1)
        for _ in range(2):
            stopping.cancel()
            await asyncio.sleep(0)
            assert not stopping.done()
        cleanup_release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(stopping, timeout=1)
        assert receiver._read_task is None
        assert not receiver._background_tasks
        assert receiver._host_connection is None
        with pytest.raises(Exception, match="disconnect"):
            await asyncio.wait_for(request, timeout=1)
        await receiver.start()
        await receiver.stop()
    finally:
        cleanup_release.set()
        if stopping is not None:
            await asyncio.gather(stopping, return_exceptions=True)
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)


async def test_failed_restart_rolls_back_connection_and_can_retry(cluster: LocalCluster) -> None:
    original = await cluster.worker()
    await cluster.register_waiter(original)
    await original.stop()
    replacement = await cluster.worker()
    await cluster.register_waiter(replacement)
    with pytest.raises(Exception, match="already registered"):
        await original.start()
    assert original._host_connection is None
    assert original._read_task is None
    await replacement.stop()
    await original.start()
    cluster.release.set()
    assert isinstance(
        await asyncio.wait_for(original.send_message(MessageType(), AgentId("waiting", "default")), timeout=1),
        MessageType,
    )


async def test_concurrent_start_has_one_owner(cluster: LocalCluster) -> None:
    worker = GrpcWorkerAgentRuntime(host_address=cluster.address)
    cluster.workers.append(worker)
    outcomes = await asyncio.gather(worker.start(), worker.start(), return_exceptions=True)
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, ValueError) for outcome in outcomes) == 1
    await worker.stop()
    await wait_until(lambda: not cluster.host._servicer._data_connections)


async def test_unserializable_outbound_message_does_not_allocate_pending_rpc(cluster: LocalCluster) -> None:
    worker = await cluster.worker()
    with pytest.raises(ValueError, match="Unknown type"):
        await worker.send_message(object(), AgentId("waiting", "default"))
    assert not worker._pending_requests


async def test_already_cancelled_token_does_not_invoke_remote_agent(cluster: LocalCluster) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await cluster.register_waiter(receiver)
    token = CancellationToken()
    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await sender.send_message(MessageType(), AgentId("waiting", "default"), cancellation_token=token)
    assert not sender._pending_requests
    cluster.release.set()
    # A later RPC is an ordered barrier for messages sent on this stream.
    with pytest.raises(Exception, match="not found"):
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("missing", "default")), timeout=1)
    assert not cluster.started.is_set()


class CancelledAgent(RoutedAgent):
    def __init__(self, mode: str) -> None:
        super().__init__("An independently cancelled provider operation")
        self.mode = mode

    @message_handler
    async def respond(self, message: MessageType, ctx: MessageContext) -> MessageType:
        if self.mode == "future":
            future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
            future.cancel()
            await future
        elif self.mode == "self":
            task = asyncio.current_task()
            assert task is not None
            task.cancel()
            await asyncio.sleep(0)
        raise asyncio.CancelledError("provider cancelled")


@pytest.mark.parametrize("mode", ["raise", "future", "self"])
async def test_handler_local_cancellation_has_a_terminal_response(cluster: LocalCluster, mode: str) -> None:
    sender, receiver = await cluster.worker(), await cluster.worker()
    await CancelledAgent.register(receiver, "cancelled", lambda: CancelledAgent(mode))
    with pytest.raises(Exception, match="cancelled|CancelledError"):
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("cancelled", "default")), timeout=1)
    await wait_until(lambda: not cluster.host._servicer._pending_responses)
    await cluster.register_waiter(receiver)
    cluster.release.set()
    assert isinstance(
        await asyncio.wait_for(sender.send_message(MessageType(), AgentId("waiting", "default")), timeout=1),
        MessageType,
    )


async def test_stop_during_disconnect_does_not_cancel_handler_cleanup_twice(cluster: LocalCluster) -> None:
    worker = await cluster.worker()
    cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()
    await CleanupAgent.register(
        worker, "cleanup", lambda: CleanupAgent(cluster.started, cleanup_started, cleanup_release)
    )
    instance = await worker.try_get_underlying_agent_instance(AgentId("cleanup", "default"), CleanupAgent)
    request = asyncio.create_task(worker.send_message(MessageType(), AgentId("cleanup", "default")))
    stopping: asyncio.Task[None] | None = None
    try:
        await asyncio.wait_for(cluster.started.wait(), timeout=1)
        await cluster.host.stop(grace=0)
        await asyncio.wait_for(cleanup_started.wait(), timeout=1)
        stopping = asyncio.create_task(worker.stop())
        # Permit shutdown to reach its read-task join without releasing the
        # handler's resource finalizer. The cleanup must still own that task.
        await asyncio.sleep(0.02)
        assert not stopping.done()
    finally:
        cleanup_release.set()
        if stopping is not None:
            await asyncio.wait_for(stopping, timeout=1)
        await asyncio.gather(request, return_exceptions=True)
    assert instance.cleaned.is_set()
