"""Channel termination, half-close and partial startup contracts."""

# Ownership assertions intentionally inspect tasks and transport state.
# pyright: reportPrivateUsage=false

import asyncio
from typing import Any, AsyncIterator

import grpc.aio
import pytest
import pytest_asyncio
from autogen_core import AgentId, try_get_known_serializers_for_type
from autogen_ext.runtimes.grpc._worker_runtime import GrpcWorkerAgentRuntime, HostConnection
from autogen_ext.runtimes.grpc._worker_runtime_host_servicer import CallbackChannelConnection
from autogen_ext.runtimes.grpc.protos import agent_worker_pb2, agent_worker_pb2_grpc
from autogen_test_utils import MessageType

from .test_grpc_lifecycle import LocalCluster, wait_until

pytestmark = [pytest.mark.grpc, pytest.mark.asyncio]


@pytest_asyncio.fixture  # type: ignore
async def cluster(unused_tcp_port: int) -> AsyncIterator[LocalCluster]:
    cluster = LocalCluster(unused_tcp_port)
    cluster.host.start()
    try:
        yield cluster
    finally:
        await cluster.close()


async def test_close_wakes_every_blocked_receiver(cluster: LocalCluster) -> None:
    connection = await HostConnection.from_host_address(cluster.address)
    receivers = [asyncio.create_task(connection.recv()) for _ in range(3)]
    await asyncio.sleep(0)
    await asyncio.gather(connection.close(), connection.close())
    outcomes = await asyncio.wait_for(asyncio.gather(*receivers, return_exceptions=True), timeout=1)
    assert all(isinstance(outcome, ConnectionError) for outcome in outcomes)
    with pytest.raises(ConnectionError, match="closed"):
        await connection.send(agent_worker_pb2.Message())
    with pytest.raises(ConnectionError, match="closed"):
        await connection.recv()
    assert connection._connection_task is not None and connection._connection_task.done()


async def test_remote_shutdown_wakes_receiver_without_an_explicit_close(cluster: LocalCluster) -> None:
    connection = await HostConnection.from_host_address(cluster.address)
    try:
        receiver = asyncio.create_task(connection.recv())
        await cluster.host.stop(grace=0)
        with pytest.raises(ConnectionError):
            await asyncio.wait_for(receiver, timeout=1)
        with pytest.raises(ConnectionError):
            await connection.send(agent_worker_pb2.Message())
    finally:
        await connection.close()


async def test_transport_failure_during_connect_closes_the_native_channel(
    unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    channels: list[grpc.aio.Channel] = []  # type: ignore[no-any-unimported]
    original = grpc.aio.insecure_channel

    def create_channel(*args: Any, **kwargs: Any) -> grpc.aio.Channel:  # type: ignore[no-any-unimported]
        channel = original(*args, **kwargs)
        channels.append(channel)
        return channel

    monkeypatch.setattr(grpc.aio, "insecure_channel", create_channel)
    with pytest.raises(grpc.aio.AioRpcError):
        await asyncio.wait_for(HostConnection.from_host_address(f"127.0.0.1:{unused_tcp_port}"), timeout=2)
    assert len(channels) == 1
    assert channels[0].get_state() == grpc.ChannelConnectivity.SHUTDOWN


async def test_cancelled_connect_joins_partially_opened_connection(
    cluster: LocalCluster, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = asyncio.Event()
    connections: list[HostConnection] = []
    original = HostConnection._connect

    async def connect(connection: HostConnection) -> None:
        connections.append(connection)
        await original(connection)
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(HostConnection, "_connect", connect)
    opening = asyncio.create_task(HostConnection.from_host_address(cluster.address))
    await asyncio.wait_for(entered.wait(), timeout=1)
    opening.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(opening, timeout=1)
    assert connections[0]._channel.get_state() == grpc.ChannelConnectivity.SHUTDOWN
    assert connections[0]._connection_task is not None and connections[0]._connection_task.done()


async def test_half_closed_request_stream_can_receive_a_response(cluster: LocalCluster) -> None:
    # HTTP/2 half-close is not a disconnect: a client may finish sending before
    # the host has delivered its final response.
    async with grpc.aio.insecure_channel(cluster.address) as channel:
        stub: Any = agent_worker_pb2_grpc.AgentRpcStub(channel)
        call = stub.OpenChannel(metadata=[("client-id", "half-close")])
        await call.write(
            agent_worker_pb2.Message(
                request=agent_worker_pb2.RpcRequest(
                    request_id="one", target=agent_worker_pb2.AgentId(type="missing", key="default")
                )
            )
        )
        await call.done_writing()
        response = await asyncio.wait_for(call.read(), timeout=1)
        assert response.response.request_id == "one"
        assert "not found" in response.response.error
        call.cancel()


@pytest.mark.parametrize("control", [False, True])
async def test_duplicate_channel_does_not_replace_existing_owner(cluster: LocalCluster, control: bool) -> None:
    async with grpc.aio.insecure_channel(cluster.address) as channel:
        stub: Any = agent_worker_pb2_grpc.AgentRpcStub(channel)
        open_channel = stub.OpenControlChannel if control else stub.OpenChannel
        connections = (
            cluster.host._servicer._control_connections if control else cluster.host._servicer._data_connections
        )
        first = open_channel(metadata=[("client-id", "unique")])
        try:
            await first.wait_for_connection()
            await wait_until(lambda: "unique" in connections)
            owner = connections["unique"]
            duplicate = open_channel(metadata=[("client-id", "unique")])
            with pytest.raises(grpc.aio.AioRpcError) as error:
                await asyncio.wait_for(duplicate.read(), timeout=1)
            assert error.value.code() == grpc.StatusCode.ALREADY_EXISTS
            assert connections["unique"] is owner
        finally:
            first.cancel()
        await wait_until(lambda: not connections)
        assert owner._receiving_task.done()


async def test_channel_callback_failure_reaches_the_stream_consumer() -> None:
    async def messages() -> AsyncIterator[int]:
        yield 1

    async def callback(message: int) -> None:
        raise ValueError("invalid request envelope")

    connection = CallbackChannelConnection[int, int](messages(), "broken", callback)
    try:
        with pytest.raises(ValueError, match="invalid request envelope"):
            await asyncio.wait_for(anext(connection), timeout=1)
    finally:
        await connection.close()


@pytest.mark.parametrize("cancel_close", [False, True])
async def test_close_joins_request_iterator_finalizer(cancel_close: bool) -> None:
    entered, finalizing, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def messages() -> AsyncIterator[int]:
        try:
            entered.set()
            await asyncio.Event().wait()
            yield 1
        finally:
            finalizing.set()
            await release.wait()

    async def callback(message: int) -> None:
        pass

    connection = CallbackChannelConnection[int, int](messages(), "owned", callback)
    await entered.wait()
    closing = asyncio.create_task(connection.close())
    await finalizing.wait()
    second_close = asyncio.create_task(connection.close())
    await asyncio.sleep(0)
    if cancel_close:
        closing.cancel()
        await asyncio.sleep(0)
    assert not closing.done() and not second_close.done()
    release.set()
    outcomes = await asyncio.wait_for(asyncio.gather(closing, second_close, return_exceptions=True), timeout=1)
    assert outcomes[1] is None
    assert isinstance(outcomes[0], asyncio.CancelledError) if cancel_close else outcomes[0] is None
    with pytest.raises(StopAsyncIteration):
        await anext(connection)
    with pytest.raises(ConnectionError):
        await connection.send(2)


async def test_host_stop_survives_caller_cancellation(cluster: LocalCluster, monkeypatch: pytest.MonkeyPatch) -> None:
    await cluster.worker()
    entered, release = asyncio.Event(), asyncio.Event()
    original = cluster.host._server.stop

    async def stop(grace: float | None) -> None:
        entered.set()
        await release.wait()
        await original(grace)

    monkeypatch.setattr(cluster.host._server, "stop", stop)
    stopping = asyncio.create_task(cluster.host.stop(grace=0))
    await entered.wait()
    try:
        stopping.cancel()
        await asyncio.sleep(0)
        assert not stopping.done()
    finally:
        release.set()
        await asyncio.gather(stopping, return_exceptions=True)
    assert cluster.host._serve_task is None
    assert not cluster.host._servicer._data_connections
    assert not cluster.host._servicer._background_tasks


class ReplyThenClose(agent_worker_pb2_grpc.AgentRpcServicer):
    async def OpenChannel(
        self, request_iterator: AsyncIterator[agent_worker_pb2.Message], context: Any
    ) -> AsyncIterator[agent_worker_pb2.Message]:
        async for message in request_iterator:
            if message.HasField("request"):
                yield agent_worker_pb2.Message(
                    response=agent_worker_pb2.RpcResponse(
                        request_id=message.request.request_id, payload=message.request.payload
                    )
                )
                return


async def test_buffered_response_is_delivered_before_terminal_eof(unused_tcp_port: int) -> None:
    address = f"127.0.0.1:{unused_tcp_port}"
    server = grpc.aio.server()
    agent_worker_pb2_grpc.add_AgentRpcServicer_to_server(ReplyThenClose(), server)  # type: ignore[abstract]
    server.add_insecure_port(address)
    await server.start()
    worker = GrpcWorkerAgentRuntime(host_address=address)
    dispatch = asyncio.Event()
    original = worker._run_read_loop

    async def delayed_dispatch() -> None:
        await dispatch.wait()
        await original()

    worker._run_read_loop = delayed_dispatch  # type: ignore[method-assign]
    worker.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await worker.start()
    request = asyncio.create_task(worker.send_message(MessageType(), AgentId("echo", "default")))
    try:
        connection = worker._host_connection
        assert connection is not None and connection._connection_task is not None
        # The native transport has received both the reply and EOF while the
        # dispatcher was not scheduled. Their order must survive dispatch.
        await asyncio.wait_for(connection._connection_task, timeout=1)
        dispatch.set()
        assert isinstance(await asyncio.wait_for(request, timeout=1), MessageType)
    finally:
        dispatch.set()
        await worker.stop()
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)
        await server.stop(0)
