import asyncio
import inspect
import json
import logging
import signal
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
    Type,
    TypeVar,
    cast,
)

import grpc
from grpc.aio import StreamStreamCall
from opentelemetry.trace import NoOpTracerProvider, TracerProvider
from typing_extensions import Self, deprecated

from autogen_core.base import JSON_DATA_CONTENT_TYPE
from autogen_core.base._serialization import MessageSerializer, SerializationRegistry

from ..base import (
    Agent,
    AgentId,
    AgentInstantiationContext,
    AgentMetadata,
    AgentRuntime,
    AgentType,
    CancellationToken,
    MessageContext,
    MessageHandlerContext,
    Subscription,
    SubscriptionInstantiationContext,
    TopicId,
)
from ..components import TypeSubscription
from ._helpers import SubscriptionManager, get_impl
from .protos import agent_worker_pb2, agent_worker_pb2_grpc
from .telemetry import MessageRuntimeTracingConfig, TraceHelper, get_telemetry_grpc_metadata

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
        return await self._queue.get()

    def __aiter__(self) -> AsyncIterator[Any]:
        return self


class HostConnection:
    DEFAULT_GRPC_CONFIG: ClassVar[Mapping[str, Any]] = {
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

    def __init__(self, channel: grpc.aio.Channel) -> None:  # type: ignore
        self._channel = channel
        self._send_queue = asyncio.Queue[agent_worker_pb2.Message]()
        self._recv_queue = asyncio.Queue[agent_worker_pb2.Message]()
        self._connection_task: Task[None] | None = None

    @classmethod
    def from_host_address(cls, host_address: str, grpc_config: Mapping[str, Any] = DEFAULT_GRPC_CONFIG) -> Self:
        logger.info("Connecting to %s", host_address)
        channel = grpc.aio.insecure_channel(host_address, options=[("grpc.service_config", json.dumps(grpc_config))])
        instance = cls(channel)
        instance._connection_task = asyncio.create_task(
            instance._connect(channel, instance._send_queue, instance._recv_queue)
        )
        return instance

    async def close(self) -> None:
        if self._connection_task is None:
            raise RuntimeError("Connection is not open.")
        await self._channel.close()
        if self._connection_task is not None:
            await self._connection_task

    @staticmethod
    async def _connect(  # type: ignore
        channel: grpc.aio.Channel,
        send_queue: asyncio.Queue[agent_worker_pb2.Message],
        receive_queue: asyncio.Queue[agent_worker_pb2.Message],
    ) -> None:
        stub: AgentRpcAsyncStub = agent_worker_pb2_grpc.AgentRpcStub(channel)  # type: ignore

        # TODO: where do exceptions from reading the iterable go? How do we recover from those?
        recv_stream: StreamStreamCall[agent_worker_pb2.Message, agent_worker_pb2.Message] = stub.OpenChannel(  # type: ignore
            QueueAsyncIterable(send_queue)
        )  # type: ignore

        while True:
            logger.info("Waiting for message from host")
            message = await recv_stream.read()  # type: ignore
            if message == grpc.aio.EOF:  # type: ignore
                logger.info("EOF")
                break
            message = cast(agent_worker_pb2.Message, message)
            logger.info(f"Received a message from host: {message}")
            await receive_queue.put(message)
            logger.info("Put message in receive queue")

    async def send(self, message: agent_worker_pb2.Message) -> None:
        logger.info(f"Send message to host: {message}")
        await self._send_queue.put(message)
        logger.info("Put message in send queue")

    async def recv(self) -> agent_worker_pb2.Message:
        logger.info("Getting message from queue")
        return await self._recv_queue.get()


class WorkerAgentRuntime(AgentRuntime):
    def __init__(self, host_address: str, tracer_provider: TracerProvider | None = None) -> None:
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
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0
        self._host_connection: HostConnection | None = None
        self._background_tasks: Set[Task[Any]] = set()
        self._subscription_manager = SubscriptionManager()
        self._serialization_registry = SerializationRegistry()

    def start(self) -> None:
        """Start the runtime in a background task."""
        if self._running:
            raise ValueError("Runtime is already running.")
        logger.info(f"Connecting to host: {self._host_address}")
        self._host_connection = HostConnection.from_host_address(self._host_address)
        logger.info("Connection established")
        if self._read_task is None:
            self._read_task = asyncio.create_task(self._run_read_loop())
        self._running = True

    def _raise_on_exception(self, task: Task[Any]) -> None:
        exception = task.exception()
        if exception is not None:
            raise exception

    async def _run_read_loop(self) -> None:
        logger.info("Starting read loop")
        # TODO: catch exceptions and reconnect
        while self._running:
            try:
                message = await self._host_connection.recv()  # type: ignore
                oneofcase = agent_worker_pb2.Message.WhichOneof(message, "message")
                match oneofcase:
                    case "registerAgentType" | "addSubscription":
                        logger.warning(f"Cant handle {oneofcase}, skipping.")
                    case "request":
                        request: agent_worker_pb2.RpcRequest = message.request
                        task = asyncio.create_task(self._process_request(request))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._raise_on_exception)
                        task.add_done_callback(self._background_tasks.discard)
                    case "response":
                        response: agent_worker_pb2.RpcResponse = message.response
                        task = asyncio.create_task(self._process_response(response))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._raise_on_exception)
                        task.add_done_callback(self._background_tasks.discard)
                    case "event":
                        event: agent_worker_pb2.Event = message.event
                        task = asyncio.create_task(self._process_event(event))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._raise_on_exception)
                        task.add_done_callback(self._background_tasks.discard)
                    case None:
                        logger.warning("No message")
            except Exception as e:
                logger.error("Error in read loop", exc_info=e)

    async def stop(self) -> None:
        """Stop the runtime immediately."""
        if not self._running:
            raise RuntimeError("Runtime is not running.")
        self._running = False
        # Wait for all background tasks to finish.
        final_tasks_results = await asyncio.gather(*self._background_tasks, return_exceptions=True)
        for task_result in final_tasks_results:
            if isinstance(task_result, Exception):
                logger.error("Error in background task", exc_info=task_result)
        # Close the host connection.
        if self._host_connection is not None:
            try:
                await self._host_connection.close()
            except asyncio.CancelledError:
                pass
        # Cancel the read task.
        if self._read_task is not None:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

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
    ) -> Any:
        if not self._running:
            raise ValueError("Runtime must be running when sending message.")
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        data_type = self._serialization_registry.type_name(message)
        with self._trace_helper.trace_block(
            "create", recipient, parent=None, extraAttributes={"message_type": data_type, "message_size": len(message)}
        ):
            # create a new future for the result
            future = asyncio.get_event_loop().create_future()
            async with self._pending_requests_lock:
                self._next_request_id += 1
                request_id = self._next_request_id
            request_id_str = str(request_id)
            self._pending_requests[request_id_str] = future
            serialized_message = self._serialization_registry.serialize(
                message, type_name=data_type, data_content_type=JSON_DATA_CONTENT_TYPE
            )
            telemetry_metadata = get_telemetry_grpc_metadata()
            runtime_message = agent_worker_pb2.Message(
                request=agent_worker_pb2.RpcRequest(
                    request_id=request_id_str,
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

            # TODO: Find a way to handle timeouts/errors
            task = asyncio.create_task(self._send_message(runtime_message, "send", recipient, telemetry_metadata))
            self._background_tasks.add(task)
            task.add_done_callback(self._raise_on_exception)
            task.add_done_callback(self._background_tasks.discard)
            return await future

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        if not self._running:
            raise ValueError("Runtime must be running when publishing message.")
        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        message_type = self._serialization_registry.type_name(message)
        with self._trace_helper.trace_block(
            "create", topic_id, parent=None, extraAttributes={"message_type": message_type}
        ):
            serialized_message = self._serialization_registry.serialize(
                message, type_name=message_type, data_content_type=JSON_DATA_CONTENT_TYPE
            )
            telemetry_metadata = get_telemetry_grpc_metadata()
            runtime_message = agent_worker_pb2.Message(
                event=agent_worker_pb2.Event(
                    topic_type=topic_id.type,
                    topic_source=topic_id.source,
                    source=agent_worker_pb2.AgentId(type=sender.type, key=sender.key) if sender is not None else None,
                    metadata=telemetry_metadata,
                    payload=agent_worker_pb2.Payload(
                        data_type=message_type,
                        data=serialized_message,
                        data_content_type=JSON_DATA_CONTENT_TYPE,
                    ),
                )
            )

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

    async def _process_request(self, request: agent_worker_pb2.RpcRequest) -> None:
        assert self._host_connection is not None
        recipient = AgentId(request.target.type, request.target.key)
        sender: AgentId | None = None
        if request.HasField("source"):
            sender = AgentId(request.source.type, request.source.key)
            logging.info(f"Processing request from {sender} to {recipient}")
        else:
            logging.info(f"Processing request from unknown source to {recipient}")

        # Deserialize the message.
        message = self._serialization_registry.deserialize(
            request.payload.data,
            type_name=request.payload.data_type,
            data_content_type=request.payload.data_content_type,
        )

        # Get the receiving agent and prepare the message context.
        rec_agent = await self._get_agent(recipient)
        message_context = MessageContext(
            sender=sender,
            topic_id=None,
            is_rpc=True,
            cancellation_token=CancellationToken(),
        )

        # Call the receiving agent.
        try:
            with MessageHandlerContext.populate_context(rec_agent.id):
                with self._trace_helper.trace_block(
                    "process",
                    rec_agent.id,
                    parent=request.metadata,
                    attributes={"request_id": request.request_id},
                    extraAttributes={"message_type": request.payload.data_type},
                ):
                    result = await rec_agent.on_message(message, ctx=message_context)
        except BaseException as e:
            response_message = agent_worker_pb2.Message(
                response=agent_worker_pb2.RpcResponse(
                    request_id=request.request_id,
                    error=str(e),
                    metadata=get_telemetry_grpc_metadata(),
                ),
            )
            # Send the error response.
            await self._host_connection.send(response_message)
            return

        # Serialize the result.
        result_type = self._serialization_registry.type_name(result)
        serialized_result = self._serialization_registry.serialize(
            result, type_name=result_type, data_content_type=JSON_DATA_CONTENT_TYPE
        )

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
        with self._trace_helper.trace_block(
            "ack",
            None,
            parent=response.metadata,
            attributes={"request_id": response.request_id},
            extraAttributes={"message_type": response.payload.data_type},
        ):
            # Deserialize the result.
            result = self._serialization_registry.deserialize(
                response.payload.data,
                type_name=response.payload.data_type,
                data_content_type=response.payload.data_content_type,
            )
            # Get the future and set the result.
            future = self._pending_requests.pop(response.request_id)
            if len(response.error) > 0:
                future.set_exception(Exception(response.error))
            else:
                future.set_result(result)

    async def _process_event(self, event: agent_worker_pb2.Event) -> None:
        message = self._serialization_registry.deserialize(
            event.payload.data, type_name=event.payload.data_type, data_content_type=event.payload.data_content_type
        )
        sender: AgentId | None = None
        if event.HasField("source"):
            sender = AgentId(event.source.type, event.source.key)
        topic_id = TopicId(event.topic_type, event.topic_source)
        # Get the recipients for the topic.
        recipients = await self._subscription_manager.get_subscribed_recipients(topic_id)
        # Send the message to each recipient.
        responses: List[Awaitable[Any]] = []
        for agent_id in recipients:
            if agent_id == sender:
                continue
            message_context = MessageContext(
                sender=sender,
                topic_id=topic_id,
                is_rpc=False,
                cancellation_token=CancellationToken(),
            )
            agent = await self._get_agent(agent_id)
            with MessageHandlerContext.populate_context(agent.id):

                async def send_message(agent: Agent, message_context: MessageContext) -> Any:
                    with self._trace_helper.trace_block(
                        "process",
                        agent.id,
                        parent=event.metadata,
                        extraAttributes={"message_type": event.payload.data_type},
                    ):
                        await agent.on_message(message, ctx=message_context)

                future = send_message(agent, message_context)
            responses.append(future)
        # Wait for all responses.
        try:
            await asyncio.gather(*responses)
        except BaseException as e:
            logger.error("Error handling event", exc_info=e)

    @deprecated(
        "Use your agent's `register` method directly instead of this method. See documentation for latest usage."
    )
    async def register(
        self,
        type: str,
        agent_factory: Callable[[], T | Awaitable[T]],
        subscriptions: Callable[[], list[Subscription] | Awaitable[list[Subscription]]]
        | list[Subscription]
        | None = None,
    ) -> AgentType:
        if type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")
        self._agent_factories[type] = agent_factory

        if self._host_connection is None:
            raise RuntimeError("Host connection is not set.")
        message = agent_worker_pb2.Message(registerAgentType=agent_worker_pb2.RegisterAgentType(type=type))
        await self._host_connection.send(message)

        if subscriptions is not None:
            if callable(subscriptions):
                with SubscriptionInstantiationContext.populate_context(AgentType(type)):
                    subscriptions_list_result = subscriptions()
                    if inspect.isawaitable(subscriptions_list_result):
                        subscriptions_list = await subscriptions_list_result
                    else:
                        subscriptions_list = subscriptions_list_result
            else:
                subscriptions_list = subscriptions

            for subscription in subscriptions_list:
                await self.add_subscription(subscription)

        return AgentType(type)

    async def register_factory(
        self,
        *,
        type: AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        expected_class: type[T],
    ) -> AgentType:
        async def factory_wrapper() -> T:
            maybe_agent_instance = agent_factory()
            if inspect.isawaitable(maybe_agent_instance):
                agent_instance = await maybe_agent_instance
            else:
                agent_instance = maybe_agent_instance

            if type_func_alias(agent_instance) != expected_class:
                raise ValueError("Factory registered using the wrong type.")

            return agent_instance

        self._agent_factories[type.type] = factory_wrapper

        return type

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
                return cast(T, await agent)

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
        if not isinstance(subscription, TypeSubscription):
            raise ValueError("Only TypeSubscription is supported.")
        # Add to local subscription manager.
        await self._subscription_manager.add_subscription(subscription)
        # Send the subscription to the host.
        message = agent_worker_pb2.Message(
            addSubscription=agent_worker_pb2.AddSubscription(
                subscription=agent_worker_pb2.Subscription(
                    typeSubscription=agent_worker_pb2.TypeSubscription(
                        topic_type=subscription.topic_type, agent_type=subscription.agent_type
                    )
                )
            )
        )
        await self._host_connection.send(message)

    async def remove_subscription(self, id: str) -> None:
        raise NotImplementedError("Subscriptions cannot be removed while using distributed runtime currently.")

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
