from __future__ import annotations

import asyncio
import inspect
import json
import logging
import signal
import uuid
import warnings
from asyncio import Future, Task
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    ClassVar,
    DefaultDict,
    Dict,
    List,
    Literal,
    Mapping,
    ParamSpec,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from autogen_core import (
    JSON_DATA_CONTENT_TYPE,
    PROTOBUF_DATA_CONTENT_TYPE,
    Agent,
    AgentId,
    AgentInstantiationContext,
    AgentMetadata,
    AgentRuntime,
    AgentType,
    CancellationToken,
    MessageContext,
    MessageHandlerContext,
    MessageSerializer,
    Subscription,
    TopicId,
)
from autogen_core._runtime_impl_helpers import SubscriptionManager, get_impl
from autogen_core._serialization import (
    SerializationRegistry,
)
from autogen_core._telemetry import MessageRuntimeTracingConfig, TraceHelper, get_telemetry_grpc_metadata
from google.protobuf import any_pb2
from opentelemetry.trace import TracerProvider
from typing_extensions import Self

from autogen_ext.runtimes.grpc._utils import await_cleanup, subscription_to_proto

from . import _constants
from ._constants import GRPC_IMPORT_ERROR_STR
from ._type_helpers import ChannelArgumentType
from .protos import agent_worker_pb2, agent_worker_pb2_grpc, cloudevent_pb2

try:
    import grpc.aio
except ImportError as e:
    raise ImportError(GRPC_IMPORT_ERROR_STR) from e

if TYPE_CHECKING:
    from .protos.agent_worker_pb2_grpc import AgentRpcAsyncStub

logger = logging.getLogger("autogen_core")
event_logger = logging.getLogger("autogen_core.events")

P = ParamSpec("P")
T = TypeVar("T", bound=Agent)


type_func_alias = type


class QueueAsyncIterable(AsyncIterator[Any], AsyncIterable[Any]):
    def __init__(self, queue: asyncio.Queue[Any]) -> None:
        self._queue = queue

    async def __anext__(self) -> Any:
        message = await self._queue.get()
        if message is None:
            raise StopAsyncIteration
        return message

    def __aiter__(self) -> AsyncIterator[Any]:
        return self


class HostConnection:
    DEFAULT_GRPC_CONFIG: ClassVar[ChannelArgumentType] = [
        (
            "grpc.service_config",
            json.dumps(
                {
                    "methodConfig": [
                        {
                            "name": [{}],
                            "retryPolicy": {
                                "maxAttempts": 3,
                                "initialBackoff": "0.01s",
                                "maxBackoff": "5s",
                                "backoffMultiplier": 2,
                                "retryableStatusCodes": ["UNAVAILABLE"],
                            },
                        }
                    ],
                }
            ),
        )
    ]

    def __init__(self, channel: grpc.aio.Channel, stub: Any) -> None:  # type: ignore
        self._channel = channel
        self._send_queue = asyncio.Queue[agent_worker_pb2.Message | None]()
        self._recv_queue = asyncio.Queue[agent_worker_pb2.Message | None]()
        self._connection_task: Task[None] | None = None
        self._close_task: Task[None] | None = None
        self._stream: grpc.aio.StreamStreamCall[agent_worker_pb2.Message, agent_worker_pb2.Message] | None = None  # type: ignore[no-any-unimported]
        self._terminal_error: ConnectionError | None = None
        self._stub: AgentRpcAsyncStub = stub
        self._client_id = str(uuid.uuid4())

    @property
    def stub(self) -> Any:
        return self._stub

    @property
    def metadata(self) -> Sequence[Tuple[str, str]]:
        return [("client-id", self._client_id)]

    @property
    def is_closed(self) -> bool:
        return self._terminal_error is not None

    @classmethod
    async def from_host_address(
        cls, host_address: str, extra_grpc_config: ChannelArgumentType = DEFAULT_GRPC_CONFIG
    ) -> Self:
        logger.info("Connecting to %s", host_address)
        #  Always use DEFAULT_GRPC_CONFIG and override it with provided grpc_config
        merged_options = [
            (k, v) for k, v in {**dict(HostConnection.DEFAULT_GRPC_CONFIG), **dict(extra_grpc_config)}.items()
        ]

        channel = grpc.aio.insecure_channel(
            host_address,
            options=merged_options,
        )
        stub: AgentRpcAsyncStub = agent_worker_pb2_grpc.AgentRpcStub(channel)  # type: ignore
        instance = cls(channel, stub)

        try:
            await instance._connect()
        except BaseException:
            await instance.close()
            raise
        return instance

    async def close(self) -> None:
        """Close the stream and join its reader, including partially opened connections."""
        if self._close_task is None:
            self._close_task = asyncio.create_task(self._close())
        await await_cleanup(self._close_task)

    async def _close(self) -> None:
        self._finish(ConnectionError("Host connection is closed."))
        if self._stream is not None:
            self._stream.cancel()
        try:
            await self._channel.close()
        finally:
            if self._connection_task is not None:
                self._connection_task.cancel()
                await asyncio.gather(self._connection_task, return_exceptions=True)

    def _finish(self, error: ConnectionError) -> None:
        if self._terminal_error is None:
            self._terminal_error = error
            self._send_queue.put_nowait(None)
            self._recv_queue.put_nowait(None)

    async def _connect(self) -> None:
        self._stream = self._stub.OpenChannel(  # type: ignore
            QueueAsyncIterable(self._send_queue), metadata=self.metadata
        )
        await self._stream.wait_for_connection()
        self._connection_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        assert self._stream is not None
        try:
            while True:
                message = cast(agent_worker_pb2.Message, await self._stream.read())  # type: ignore
                if message == grpc.aio.EOF:  # type: ignore
                    break
                self._recv_queue.put_nowait(message)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._finish(ConnectionError(f"Host connection disconnected: {error}"))
        finally:
            self._finish(ConnectionError("Host connection is closed."))
            self._stream.cancel()

    async def send(self, message: agent_worker_pb2.Message) -> None:
        if self._terminal_error is not None:
            raise self._terminal_error
        logger.info(f"Send message to host: {message}")
        self._send_queue.put_nowait(message)

    async def recv(self) -> agent_worker_pb2.Message:
        message = await self._recv_queue.get()
        if message is None:
            # Preserve the terminal notification for concurrent and future waiters.
            self._recv_queue.put_nowait(None)
            raise self._terminal_error or ConnectionError("Host connection is closed.")
        return message


# TODO: Lots of types need to have protobuf equivalents:
# Core:
#   - FunctionCall, CodeResult, possibly CodeBlock
#   - All the types in https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/models/_types.py
#
# Agentchat:
#   - All the types in https://github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/messages.py to protobufs.
#
# Ext --
#   CodeExecutor:
#       - CommandLineCodeResult


class GrpcWorkerAgentRuntime(AgentRuntime):
    """An agent runtime for running remote or cross-language agents.

    Agent messaging uses protobufs from `agent_worker.proto`_ and ``CloudEvent`` from `cloudevent.proto`_.

    Cross-language agents will additionally require all agents use shared protobuf schemas for any message types that are sent between agents.

    .. _agent_worker.proto: https://github.com/microsoft/autogen/blob/main/protos/agent_worker.proto

    .. _cloudevent.proto: https://github.com/microsoft/autogen/blob/main/protos/cloudevent.proto

    """

    # TODO: Needs to handle agent close() call
    def __init__(
        self,
        host_address: str,
        tracer_provider: TracerProvider | None = None,
        extra_grpc_config: ChannelArgumentType | None = None,
        payload_serialization_format: str = JSON_DATA_CONTENT_TYPE,
    ) -> None:
        self._host_address = host_address
        self._trace_helper = TraceHelper(tracer_provider, MessageRuntimeTracingConfig("Worker Runtime"))
        self._per_type_subscribers: DefaultDict[tuple[str, str], Set[AgentId]] = defaultdict(set)
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._known_namespaces: set[str] = set()
        self._read_task: None | Task[None] = None
        self._running = False
        self._lifecycle_lock = asyncio.Lock()
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0
        self._host_connection: HostConnection | None = None
        self._background_tasks: Set[Task[Any]] = set()
        self._subscription_manager = SubscriptionManager()
        self._serialization_registry = SerializationRegistry()
        self._extra_grpc_config = extra_grpc_config or []
        self._agent_instance_types: Dict[str, Type[Agent]] = {}

        if payload_serialization_format not in {JSON_DATA_CONTENT_TYPE, PROTOBUF_DATA_CONTENT_TYPE}:
            raise ValueError(f"Unsupported payload serialization format: {payload_serialization_format}")

        self._payload_serialization_format = payload_serialization_format

    async def start(self) -> None:
        """Start the runtime, restoring registrations after an explicit restart."""
        async with self._lifecycle_lock:
            if self._running:
                raise ValueError("Runtime is already running.")
            connection = await HostConnection.from_host_address(
                self._host_address, extra_grpc_config=self._extra_grpc_config
            )
            self._host_connection = connection
            try:
                for agent_type in self._agent_factories:
                    await self._register_agent_type(agent_type)
                for subscription in self._subscription_manager.subscriptions:
                    await connection.stub.AddSubscription(
                        agent_worker_pb2.AddSubscriptionRequest(subscription=subscription_to_proto(subscription)),
                        metadata=connection.metadata,
                    )
            except BaseException:
                await connection.close()
                self._host_connection = None
                raise
            self._running = True
            self._read_task = asyncio.create_task(self._run_read_loop())

    def _raise_on_exception(self, task: Task[Any]) -> None:
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            raise exception

    async def _run_read_loop(self) -> None:
        logger.info("Starting read loop")
        assert self._host_connection is not None
        # TODO: catch exceptions and reconnect
        while self._running:
            try:
                message = await self._host_connection.recv()
                oneofcase = agent_worker_pb2.Message.WhichOneof(message, "message")
                match oneofcase:
                    case "request":
                        task = asyncio.create_task(self._process_request(message.request))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._raise_on_exception)
                        task.add_done_callback(self._background_tasks.discard)
                    case "response":
                        # Settle replies in wire order before a following EOF
                        # can fail outstanding calls. This path never awaits I/O.
                        await self._process_response(message.response)
                    case "cloudEvent":
                        task = asyncio.create_task(self._process_event(message.cloudEvent))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._raise_on_exception)
                        task.add_done_callback(self._background_tasks.discard)
                    case None:
                        logger.warning("No message")
            except ConnectionError as error:
                self._fail_pending_requests(error)
                # stop() may cancel this reader while handlers are already
                # finalizing. Give that cleanup its own owner to avoid sending
                # a second cancellation into their asynchronous finalizers.
                await await_cleanup(asyncio.create_task(self._cancel_background_tasks()))
                return
            except Exception as e:
                logger.error("Error in read loop", exc_info=e)

    async def _cancel_background_tasks(self) -> None:
        tasks = list(self._background_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self) -> None:
        """Stop immediately, cancel owned handlers and finish outstanding callers."""
        async with self._lifecycle_lock:
            if not self._running:
                raise RuntimeError("Runtime is not running.")
            await await_cleanup(asyncio.create_task(self._shutdown()))

    def _fail_pending_requests(self, error: Exception) -> None:
        pending, self._pending_requests = self._pending_requests, {}
        for future in pending.values():
            if not future.done():
                future.set_exception(error)

    async def _shutdown(self) -> None:
        self._running = False
        self._fail_pending_requests(ConnectionError("Runtime stopped; host connection is closed."))
        # Stop dispatch before taking a snapshot of the tasks it owns.
        if self._read_task is not None:
            self._read_task.cancel()
            await asyncio.gather(self._read_task, return_exceptions=True)
            self._read_task = None
        tasks = list(self._background_tasks)
        for task in tasks:
            task.cancel()
        try:
            if self._host_connection is not None:
                await self._host_connection.close()
        finally:
            await asyncio.gather(*tasks, return_exceptions=True)
            self._background_tasks.clear()
            self._host_connection = None

    async def stop_when_signal(self, signals: Sequence[signal.Signals] = (signal.SIGTERM, signal.SIGINT)) -> None:
        """Stop the runtime when a signal is received."""
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def signal_handler() -> None:
            logger.info("Received exit signal, shutting down gracefully...")
            shutdown_event.set()

        for sig in signals:
            loop.add_signal_handler(sig, signal_handler)

        # Wait for the signal to trigger the shutdown event.
        await shutdown_event.wait()

        # Stop the runtime.
        await self.stop()

    @property
    def _known_agent_names(self) -> Set[str]:
        return set(self._agent_factories.keys())

    async def _send_message(
        self,
        runtime_message: agent_worker_pb2.Message,
        send_type: Literal["send", "publish"],
        recipient: AgentId | TopicId,
        telemetry_metadata: Mapping[str, str],
    ) -> None:
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        with self._trace_helper.trace_block(send_type, recipient, parent=telemetry_metadata):
            await self._host_connection.send(runtime_message)

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> Any:
        # TODO: use message_id
        if not self._running:
            raise ValueError("Runtime must be running when sending message.")
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        data_type = self._serialization_registry.type_name(message)
        with self._trace_helper.trace_block(
            "create", recipient, parent=None, extraAttributes={"message_type": data_type}
        ):
            serialized_message = self._serialization_registry.serialize(
                message, type_name=data_type, data_content_type=JSON_DATA_CONTENT_TYPE
            )
            future = asyncio.get_running_loop().create_future()
            request_id = await self._get_new_request_id()
            self._pending_requests[request_id] = future
            if cancellation_token is not None:
                cancellation_token.link_future(future)
            telemetry_metadata = get_telemetry_grpc_metadata()
            runtime_message = agent_worker_pb2.Message(
                request=agent_worker_pb2.RpcRequest(
                    request_id=request_id,
                    target=agent_worker_pb2.AgentId(type=recipient.type, key=recipient.key),
                    source=agent_worker_pb2.AgentId(type=sender.type, key=sender.key) if sender is not None else None,
                    metadata=telemetry_metadata,
                    payload=agent_worker_pb2.Payload(
                        data_type=data_type,
                        data=serialized_message,
                        data_content_type=JSON_DATA_CONTENT_TYPE,
                    ),
                )
            )

            try:
                if not future.cancelled():
                    await self._send_message(runtime_message, "send", recipient, telemetry_metadata)
                return await future
            finally:
                self._pending_requests.pop(request_id, None)
                if not future.done():
                    future.cancel()

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> None:
        if not self._running:
            raise ValueError("Runtime must be running when publishing message.")
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        if message_id is None:
            message_id = str(uuid.uuid4())

        message_type = self._serialization_registry.type_name(message)
        with self._trace_helper.trace_block(
            "create", topic_id, parent=None, extraAttributes={"message_type": message_type}
        ):
            serialized_message = self._serialization_registry.serialize(
                message, type_name=message_type, data_content_type=self._payload_serialization_format
            )

            sender_id = sender or AgentId("unknown", "unknown")
            attributes = {
                _constants.DATA_CONTENT_TYPE_ATTR: cloudevent_pb2.CloudEvent.CloudEventAttributeValue(
                    ce_string=self._payload_serialization_format
                ),
                _constants.DATA_SCHEMA_ATTR: cloudevent_pb2.CloudEvent.CloudEventAttributeValue(ce_string=message_type),
                _constants.AGENT_SENDER_TYPE_ATTR: cloudevent_pb2.CloudEvent.CloudEventAttributeValue(
                    ce_string=sender_id.type
                ),
                _constants.AGENT_SENDER_KEY_ATTR: cloudevent_pb2.CloudEvent.CloudEventAttributeValue(
                    ce_string=sender_id.key
                ),
                _constants.MESSAGE_KIND_ATTR: cloudevent_pb2.CloudEvent.CloudEventAttributeValue(
                    ce_string=_constants.MESSAGE_KIND_VALUE_PUBLISH
                ),
            }

            # If sending JSON we fill text_data with the serialized message
            # If sending Protobuf we fill proto_data with the serialized message
            # TODO: add an encoding field for serializer

            if self._payload_serialization_format == JSON_DATA_CONTENT_TYPE:
                runtime_message = agent_worker_pb2.Message(
                    cloudEvent=cloudevent_pb2.CloudEvent(
                        id=message_id,
                        spec_version="1.0",
                        type=topic_id.type,
                        source=topic_id.source,
                        attributes=attributes,
                        # TODO: use text, or proto fields appropriately
                        binary_data=serialized_message,
                    )
                )
            else:
                # We need to unpack the serialized proto back into an Any
                # TODO: find a way to prevent the roundtrip serialization
                any_proto = any_pb2.Any()
                any_proto.ParseFromString(serialized_message)
                runtime_message = agent_worker_pb2.Message(
                    cloudEvent=cloudevent_pb2.CloudEvent(
                        id=message_id,
                        spec_version="1.0",
                        type=topic_id.type,
                        source=topic_id.source,
                        attributes=attributes,
                        proto_data=any_proto,
                    )
                )

            telemetry_metadata = get_telemetry_grpc_metadata()
            task = asyncio.create_task(self._send_message(runtime_message, "publish", topic_id, telemetry_metadata))
            self._background_tasks.add(task)
            task.add_done_callback(self._raise_on_exception)
            task.add_done_callback(self._background_tasks.discard)

    async def save_state(self) -> Mapping[str, Any]:
        raise NotImplementedError("Saving state is not yet implemented.")

    async def load_state(self, state: Mapping[str, Any]) -> None:
        raise NotImplementedError("Loading state is not yet implemented.")

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        raise NotImplementedError("Agent metadata is not yet implemented.")

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        raise NotImplementedError("Agent save_state is not yet implemented.")

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        raise NotImplementedError("Agent load_state is not yet implemented.")

    async def _get_new_request_id(self) -> str:
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _process_request(self, request: agent_worker_pb2.RpcRequest) -> None:
        assert self._host_connection is not None
        recipient = AgentId(request.target.type, request.target.key)
        sender: AgentId | None = None
        if request.HasField("source"):
            sender = AgentId(request.source.type, request.source.key)
            logging.info(f"Processing request from {sender} to {recipient}")
        else:
            logging.info(f"Processing request from unknown source to {recipient}")

        # Every request stage must produce a terminal response. Decode, factory,
        # and result-encoding failures are just as terminal as handler failures.
        try:
            message = self._serialization_registry.deserialize(
                request.payload.data,
                type_name=request.payload.data_type,
                data_content_type=request.payload.data_content_type,
            )
            rec_agent = await self._get_agent(recipient)
            message_context = MessageContext(
                sender=sender,
                topic_id=None,
                is_rpc=True,
                cancellation_token=CancellationToken(),
                message_id=request.request_id,
            )
            with MessageHandlerContext.populate_context(rec_agent.id):
                with self._trace_helper.trace_block(
                    "process",
                    rec_agent.id,
                    parent=request.metadata,
                    attributes={"request_id": request.request_id},
                    extraAttributes={"message_type": request.payload.data_type},
                ):
                    result = await rec_agent.on_message(message, ctx=message_context)
            result_type = self._serialization_registry.type_name(result)
            serialized_result = self._serialization_registry.serialize(
                result, type_name=result_type, data_content_type=JSON_DATA_CONTENT_TYPE
            )
        except (Exception, asyncio.CancelledError) as e:
            if isinstance(e, asyncio.CancelledError) and (
                not self._running or self._host_connection.is_closed
            ):
                raise
            response_message = agent_worker_pb2.Message(
                response=agent_worker_pb2.RpcResponse(
                    request_id=request.request_id,
                    error=str(e) or type(e).__name__,
                    metadata=get_telemetry_grpc_metadata(),
                ),
            )
            # Send the error response.
            await self._host_connection.send(response_message)
            return

        # Create the response message.
        response_message = agent_worker_pb2.Message(
            response=agent_worker_pb2.RpcResponse(
                request_id=request.request_id,
                payload=agent_worker_pb2.Payload(
                    data_type=result_type,
                    data=serialized_result,
                    data_content_type=JSON_DATA_CONTENT_TYPE,
                ),
                metadata=get_telemetry_grpc_metadata(),
            )
        )

        # Send the response.
        await self._host_connection.send(response_message)

    async def _process_response(self, response: agent_worker_pb2.RpcResponse) -> None:
        future = self._pending_requests.pop(response.request_id, None)
        if future is None or future.done():
            return
        with self._trace_helper.trace_block(
            "ack",
            None,
            parent=response.metadata,
            attributes={"request_id": response.request_id},
            extraAttributes={"message_type": response.payload.data_type},
        ):
            if len(response.error) > 0:
                future.set_exception(Exception(response.error))
            else:
                try:
                    result = self._serialization_registry.deserialize(
                        response.payload.data,
                        type_name=response.payload.data_type,
                        data_content_type=response.payload.data_content_type,
                    )
                except Exception as error:
                    future.set_exception(error)
                else:
                    future.set_result(result)

    async def _process_event(self, event: cloudevent_pb2.CloudEvent) -> None:
        event_attributes = event.attributes
        sender: AgentId | None = None
        if (
            _constants.AGENT_SENDER_TYPE_ATTR in event_attributes
            and _constants.AGENT_SENDER_KEY_ATTR in event_attributes
        ):
            sender = AgentId(
                event_attributes[_constants.AGENT_SENDER_TYPE_ATTR].ce_string,
                event_attributes[_constants.AGENT_SENDER_KEY_ATTR].ce_string,
            )
        topic_id = TopicId(event.type, event.source)
        # Get the recipients for the topic.
        recipients = await self._subscription_manager.get_subscribed_recipients(topic_id)

        message_content_type = event_attributes[_constants.DATA_CONTENT_TYPE_ATTR].ce_string
        message_type = event_attributes[_constants.DATA_SCHEMA_ATTR].ce_string

        if message_content_type == JSON_DATA_CONTENT_TYPE:
            message = self._serialization_registry.deserialize(
                event.binary_data, type_name=message_type, data_content_type=message_content_type
            )
        elif message_content_type == PROTOBUF_DATA_CONTENT_TYPE:
            # TODO: find a way to prevent the roundtrip serialization
            proto_binary_data = event.proto_data.SerializeToString()
            message = self._serialization_registry.deserialize(
                proto_binary_data, type_name=message_type, data_content_type=message_content_type
            )
        else:
            raise ValueError(f"Unsupported message content type: {message_content_type}")

        # TODO: dont read these values in the runtime
        topic_type_suffix = topic_id.type.split(":", maxsplit=1)[1] if ":" in topic_id.type else ""
        is_rpc = topic_type_suffix == _constants.MESSAGE_KIND_VALUE_RPC_REQUEST
        is_marked_rpc_type = (
            _constants.MESSAGE_KIND_ATTR in event_attributes
            and event_attributes[_constants.MESSAGE_KIND_ATTR].ce_string == _constants.MESSAGE_KIND_VALUE_RPC_REQUEST
        )
        if is_rpc and not is_marked_rpc_type:
            warnings.warn("Received RPC request with topic type suffix but not marked as RPC request.", stacklevel=2)

        # Send the message to each recipient.
        responses: List[Awaitable[Any]] = []
        for agent_id in recipients:
            if agent_id == sender:
                continue
            message_context = MessageContext(
                sender=sender,
                topic_id=topic_id,
                is_rpc=is_rpc,
                cancellation_token=CancellationToken(),
                message_id=event.id,
            )
            agent = await self._get_agent(agent_id)
            with MessageHandlerContext.populate_context(agent.id):

                def stringify_attributes(
                    attributes: Mapping[str, cloudevent_pb2.CloudEvent.CloudEventAttributeValue],
                ) -> Mapping[str, str]:
                    result: Dict[str, str] = {}
                    for key, value in attributes.items():
                        item = None
                        match value.WhichOneof("attr"):
                            case "ce_boolean":
                                item = str(value.ce_boolean)
                            case "ce_integer":
                                item = str(value.ce_integer)
                            case "ce_string":
                                item = value.ce_string
                            case "ce_bytes":
                                item = str(value.ce_bytes)
                            case "ce_uri":
                                item = value.ce_uri
                            case "ce_uri_ref":
                                item = value.ce_uri_ref
                            case "ce_timestamp":
                                item = str(value.ce_timestamp)
                            case _:
                                raise ValueError("Unknown attribute kind")
                        result[key] = item

                    return result

                async def send_message(agent: Agent, message_context: MessageContext) -> Any:
                    with self._trace_helper.trace_block(
                        "process",
                        agent.id,
                        parent=stringify_attributes(event.attributes),
                        extraAttributes={"message_type": message_type},
                    ):
                        await agent.on_message(message, ctx=message_context)

                future = send_message(agent, message_context)
            responses.append(future)
        # Wait for all responses.
        try:
            await asyncio.gather(*responses)
        except BaseException as e:
            logger.error("Error handling event", exc_info=e)

    async def _register_agent_type(self, agent_type: str) -> None:
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        message = agent_worker_pb2.RegisterAgentTypeRequest(type=agent_type)
        _response: agent_worker_pb2.RegisterAgentTypeResponse = await self._host_connection.stub.RegisterAgent(
            message, metadata=self._host_connection.metadata
        )

    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        expected_class: type[T] | None = None,
    ) -> AgentType:
        if isinstance(type, str):
            type = AgentType(type)

        if type.type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")

        async def factory_wrapper() -> T:
            maybe_agent_instance = agent_factory()
            if inspect.isawaitable(maybe_agent_instance):
                agent_instance = await maybe_agent_instance
            else:
                agent_instance = maybe_agent_instance

            if expected_class is not None and type_func_alias(agent_instance) != expected_class:
                raise ValueError("Factory registered using the wrong type.")

            return agent_instance

        self._agent_factories[type.type] = factory_wrapper
        # Send the registration request message to the host.
        await self._register_agent_type(type.type)

        return type

    async def register_agent_instance(
        self,
        agent_instance: Agent,
        agent_id: AgentId,
    ) -> AgentId:
        def agent_factory() -> Agent:
            raise RuntimeError(
                "Agent factory was invoked for an agent instance that was not registered. This is likely due to the agent type being incorrectly subscribed to a topic. If this exception occurs when publishing a message to the DefaultTopicId, then it is likely that `skip_class_subscriptions` needs to be turned off when registering the agent."
            )

        if agent_id in self._instantiated_agents:
            raise ValueError(f"Agent with id {agent_id} already exists.")

        if agent_id.type not in self._agent_factories:
            self._agent_factories[agent_id.type] = agent_factory
            await self._register_agent_type(agent_id.type)
            self._agent_instance_types[agent_id.type] = type_func_alias(agent_instance)
        else:
            if self._agent_factories[agent_id.type].__code__ != agent_factory.__code__:
                raise ValueError("Agent factories and agent instances cannot be registered to the same type.")
            if self._agent_instance_types[agent_id.type] != type_func_alias(agent_instance):
                raise ValueError("Agent instances must be the same object type.")

        await agent_instance.bind_id_and_runtime(id=agent_id, runtime=self)
        self._instantiated_agents[agent_id] = agent_instance
        return agent_id

    async def _invoke_agent_factory(
        self,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        agent_id: AgentId,
    ) -> T:
        with AgentInstantiationContext.populate_context((self, agent_id)):
            if len(inspect.signature(agent_factory).parameters) == 0:
                factory_one = cast(Callable[[], T], agent_factory)
                agent = factory_one()
            elif len(inspect.signature(agent_factory).parameters) == 2:
                warnings.warn(
                    "Agent factories that take two arguments are deprecated. Use AgentInstantiationContext instead. Two arg factories will be removed in a future version.",
                    stacklevel=2,
                )
                factory_two = cast(Callable[[AgentRuntime, AgentId], T], agent_factory)
                agent = factory_two(self, agent_id)
            else:
                raise ValueError("Agent factory must take 0 or 2 arguments.")

            if inspect.isawaitable(agent):
                agent = cast(T, await agent)

        return agent

    async def _get_agent(self, agent_id: AgentId) -> Agent:
        if agent_id in self._instantiated_agents:
            return self._instantiated_agents[agent_id]

        if agent_id.type not in self._agent_factories:
            raise ValueError(f"Agent with name {agent_id.type} not found.")

        agent_factory = self._agent_factories[agent_id.type]
        agent = await self._invoke_agent_factory(agent_factory, agent_id)
        self._instantiated_agents[agent_id] = agent
        return agent

    # TODO: uncomment out the following type ignore when this is fixed in mypy: https://github.com/python/mypy/issues/3737
    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        if id.type not in self._agent_factories:
            raise LookupError(f"Agent with name {id.type} not found.")

        # TODO: check if remote
        agent_instance = await self._get_agent(id)

        if not isinstance(agent_instance, type):
            raise TypeError(f"Agent with name {id.type} is not of type {type.__name__}")

        return agent_instance

    async def add_subscription(self, subscription: Subscription) -> None:
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")

        message = agent_worker_pb2.AddSubscriptionRequest(subscription=subscription_to_proto(subscription))
        _response: agent_worker_pb2.AddSubscriptionResponse = await self._host_connection.stub.AddSubscription(
            message, metadata=self._host_connection.metadata
        )

        # Add to local subscription manager.
        await self._subscription_manager.add_subscription(subscription)

    async def remove_subscription(self, id: str) -> None:
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")

        message = agent_worker_pb2.RemoveSubscriptionRequest(id=id)
        _response: agent_worker_pb2.RemoveSubscriptionResponse = await self._host_connection.stub.RemoveSubscription(
            message, metadata=self._host_connection.metadata
        )

        await self._subscription_manager.remove_subscription(id)

    async def get(
        self, id_or_type: AgentId | AgentType | str, /, key: str = "default", *, lazy: bool = True
    ) -> AgentId:
        return await get_impl(
            id_or_type=id_or_type,
            key=key,
            lazy=lazy,
            instance_getter=self._get_agent,
        )

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        self._serialization_registry.add_serializer(serializer)
