import asyncio
import inspect
import json
import logging
import threading
from asyncio import Future, Task
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
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
    Mapping,
    ParamSpec,
    Set,
    TypeVar,
    cast,
)

import grpc
from grpc.aio import StreamStreamCall
from typing_extensions import Self

from agnext.core import MESSAGE_TYPE_REGISTRY, agent_instantiation_context

from ..core import (
    Agent,
    AgentId,
    AgentMetadata,
    AgentProxy,
    AgentRuntime,
    CancellationToken,
)
from .protos import AgentId as AgentIdProto
from .protos import (
    AgentRpcStub,
    Event,
    Message,
    RegisterAgentType,
    RpcRequest,
    RpcResponse,
)

if TYPE_CHECKING:
    from .protos import AgentRpcAsyncStub

logger = logging.getLogger("agnext")
event_logger = logging.getLogger("agnext.events")


@dataclass(kw_only=True)
class PublishMessageEnvelope:
    """A message envelope for publishing messages to all agents that can handle
    the message of the type T."""

    message: Any
    cancellation_token: CancellationToken
    sender: AgentId | None
    namespace: str


@dataclass(kw_only=True)
class SendMessageEnvelope:
    """A message envelope for sending a message to a specific agent that can handle
    the message of the type T."""

    message: Any
    sender: AgentId | None
    recipient: AgentId
    future: Future[Any]
    cancellation_token: CancellationToken


@dataclass(kw_only=True)
class ResponseMessageEnvelope:
    """A message envelope for sending a response to a message."""

    message: Any
    future: Future[Any]
    sender: AgentId
    recipient: AgentId | None


P = ParamSpec("P")
T = TypeVar("T", bound=Agent)


class QueueAsyncIterable(AsyncIterator[Any], AsyncIterable[Any]):
    def __init__(self, queue: asyncio.Queue[Any]) -> None:
        self._queue = queue

    async def __anext__(self) -> Any:
        return await self._queue.get()

    def __aiter__(self) -> AsyncIterator[Any]:
        return self


class RuntimeConnection:
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
        self._send_queue = asyncio.Queue[Message]()
        self._recv_queue = asyncio.Queue[Message]()
        self._connection_task: Task[None] | None = None

    @classmethod
    async def from_connection_string(
        cls, connection_string: str, grpc_config: Mapping[str, Any] = DEFAULT_GRPC_CONFIG
    ) -> Self:
        logger.info("Connecting to %s", connection_string)
        channel = grpc.aio.insecure_channel(
            connection_string, options=[("grpc.service_config", json.dumps(grpc_config))]
        )
        # logger.info("awaiting channel_ready")
        # await channel.channel_ready()
        # logger.info("channel_ready")
        instance = cls(channel)
        instance._connection_task = asyncio.create_task(
            instance._connect(channel, instance._send_queue, instance._recv_queue)
        )
        return instance

    async def close(self) -> None:
        await self._channel.close()
        if self._connection_task is not None:
            await self._connection_task

    @staticmethod
    async def _connect(  # type: ignore
        channel: grpc.aio.Channel, send_queue: asyncio.Queue[Message], receive_queue: asyncio.Queue[Message]
    ) -> None:
        stub: AgentRpcAsyncStub = AgentRpcStub(channel)  # type: ignore

        # TODO: where do exceptions from reading the iterable go? How do we recover from those?
        recv_stream: StreamStreamCall[Message, Message] = stub.OpenChannel(QueueAsyncIterable(send_queue))  # type: ignore

        while True:
            try:
                logger.info("Waiting for message")
                message = await recv_stream.read()  # type: ignore
                if message == grpc.aio.EOF:  # type: ignore
                    logger.info("EOF")
                    break
                message = cast(Message, message)
                logger.info("Received message: %s", message)
                await receive_queue.put(message)
                logger.info("Put message in queue")
            except Exception as e:
                print("=========================================================================")
                print(e)
                print("=========================================================================")
                del recv_stream
                recv_stream = stub.OpenChannel(QueueAsyncIterable(send_queue))  # type: ignore

    async def send(self, message: Message) -> None:
        await self._send_queue.put(message)

    async def recv(self) -> Message:
        logger.info("Getting message from queue")
        return await self._recv_queue.get()
        logger.info("Got message from queue")


class WorkerAgentRuntime(AgentRuntime):
    def __init__(self) -> None:
        self._message_queue: List[PublishMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope] = []
        # (namespace, type) -> List[AgentId]
        self._per_type_subscribers: DefaultDict[tuple[str, str], Set[AgentId]] = defaultdict(set)
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        # If empty, then all namespaces are valid for that agent type
        self._valid_namespaces: Dict[str, Sequence[str]] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._known_namespaces: set[str] = set()
        self._read_task: None | Task[None] = None
        self._running = False
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = threading.Lock()
        self._next_request_id = 0
        self._runtime_connection: RuntimeConnection | None = None

    async def setup_channel(self, connection_string: str) -> None:
        logger.info(f"connecting to: {connection_string}")
        self._runtime_connection = await RuntimeConnection.from_connection_string(connection_string)
        logger.info("connection")
        if self._read_task is None:
            self._read_task = asyncio.create_task(self.run_read_loop())
        self._running = True

    async def send_register_agent_type(self, agent_type: str) -> None:
        assert self._runtime_connection is not None
        message = Message(registerAgentType=RegisterAgentType(type=agent_type))
        await self._runtime_connection.send(message)
        logger.info("Sent registerAgentType message for %s", agent_type)

    async def run_read_loop(self) -> None:
        logger.info("Starting read loop")
        # TODO: catch exceptions and reconnect
        while self._running:
            try:
                message = await self._runtime_connection.recv()  # type: ignore
                logger.info("Got message: %s", message)
                oneofcase = Message.WhichOneof(message, "message")
                match oneofcase:
                    case "registerAgentType":
                        logger.warn("Cant handle registerAgentType")
                    case "request":
                        # request: RpcRequest = message.request
                        # source = AgentId(request.source.name, request.source.namespace)
                        # target = AgentId(request.target.name, request.target.namespace)

                        raise NotImplementedError("Sending messages is not yet implemented.")
                    case "response":
                        response: RpcResponse = message.response
                        future = self._pending_requests.pop(response.request_id)
                        if len(response.error) > 0:
                            future.set_exception(Exception(response.error))
                            break
                        future.set_result(response.result)
                    case "event":
                        event: Event = message.event
                        message = MESSAGE_TYPE_REGISTRY.deserialize(event.data, type_name=event.type)
                        # namespace = event.namespace
                        namespace = "default"

                        logger.info("Got event: %s", message)
                        for agent_id in self._per_type_subscribers[
                            (namespace, MESSAGE_TYPE_REGISTRY.type_name(message))
                        ]:
                            logger.info("Sending message to %s", agent_id)
                            agent = await self._get_agent(agent_id)
                            try:
                                await agent.on_message(message, CancellationToken())
                                logger.info("%s handled event %s", agent_id, message)
                            except Exception as e:
                                event_logger.error("Error handling message", exc_info=e)

                        logger.warn("Cant handle event")
                    case None:
                        logger.warn("No message")
            except Exception as e:
                logger.error("Error in read loop", exc_info=e)

    async def close_channel(self) -> None:
        self._running = False
        if self._runtime_connection is not None:
            await self._runtime_connection.close()
        if self._read_task is not None:
            await self._read_task

    @property
    def _known_agent_names(self) -> Set[str]:
        return set(self._agent_factories.keys())

    # Returns the response of the message
    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Any:
        assert self._runtime_connection is not None
        # create a new future for the result
        future = asyncio.get_event_loop().create_future()
        with self._pending_requests_lock:
            self._next_request_id += 1
            request_id = self._next_request_id
            request_id_str = str(request_id)
            self._pending_requests[request_id_str] = future
            sender = cast(AgentId, sender)
            runtime_message = Message(
                request=RpcRequest(
                    request_id=request_id_str,
                    target=AgentIdProto(name=recipient.name, namespace=recipient.namespace),
                    source=AgentIdProto(name=sender.name, namespace=sender.namespace),
                    data=message,
                )
            )
            # TODO: Find a way to handle timeouts/errors
            asyncio.create_task(self._runtime_connection.send(runtime_message))
        return await future

    async def publish_message(
        self,
        message: Any,
        *,
        namespace: str | None = None,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        assert self._runtime_connection is not None
        sender_namespace = sender.namespace if sender is not None else None
        explicit_namespace = namespace
        if explicit_namespace is not None and sender_namespace is not None and explicit_namespace != sender_namespace:
            raise ValueError(
                f"Explicit namespace {explicit_namespace} does not match sender namespace {sender_namespace}"
            )

        assert explicit_namespace is not None or sender_namespace is not None
        actual_namespace = cast(str, explicit_namespace or sender_namespace)
        await self._process_seen_namespace(actual_namespace)
        message_type = MESSAGE_TYPE_REGISTRY.type_name(message)
        serialized_message = MESSAGE_TYPE_REGISTRY.serialize(message, type_name=message_type)
        message = Message(event=Event(namespace=actual_namespace, type=message_type, data=serialized_message))

        async def write_message() -> None:
            assert self._runtime_connection is not None
            await self._runtime_connection.send(message)

        await asyncio.create_task(write_message())

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

    async def register(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
    ) -> None:
        if name in self._agent_factories:
            raise ValueError(f"Agent with name {name} already exists.")
        self._agent_factories[name] = agent_factory

        # For all already prepared namespaces we need to prepare this agent
        for namespace in self._known_namespaces:
            await self._get_agent(AgentId(name=name, namespace=namespace))

        await self.send_register_agent_type(name)

    async def _invoke_agent_factory(
        self,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        agent_id: AgentId,
    ) -> T:
        with agent_instantiation_context((self, agent_id)):
            if len(inspect.signature(agent_factory).parameters) == 0:
                factory_one = cast(Callable[[], T], agent_factory)
                agent = factory_one()
            elif len(inspect.signature(agent_factory).parameters) == 2:
                factory_two = cast(Callable[[AgentRuntime, AgentId], T], agent_factory)
                agent = factory_two(self, agent_id)
            else:
                raise ValueError("Agent factory must take 0 or 2 arguments.")

            if inspect.isawaitable(agent):
                return cast(T, await agent)

        return agent

    async def _get_agent(self, agent_id: AgentId) -> Agent:
        await self._process_seen_namespace(agent_id.namespace)
        if agent_id in self._instantiated_agents:
            return self._instantiated_agents[agent_id]

        if agent_id.name not in self._agent_factories:
            raise ValueError(f"Agent with name {agent_id.name} not found.")

        agent_factory = self._agent_factories[agent_id.name]

        agent = await self._invoke_agent_factory(agent_factory, agent_id)

        for message_type in agent.metadata["subscriptions"]:
            self._per_type_subscribers[(agent_id.namespace, message_type)].add(agent_id)

        self._instantiated_agents[agent_id] = agent
        return agent

    async def get(self, name: str, *, namespace: str = "default") -> AgentId:
        return (await self._get_agent(AgentId(name=name, namespace=namespace))).id

    async def get_proxy(self, name: str, *, namespace: str = "default") -> AgentProxy:
        id = await self.get(name, namespace=namespace)
        return AgentProxy(id, self)

    # Hydrate the agent instances in a namespace. The primary reason for this is
    # to ensure message type subscriptions are set up.
    async def _process_seen_namespace(self, namespace: str) -> None:
        if namespace in self._known_namespaces:
            return

        self._known_namespaces.add(namespace)
        for name in self._known_agent_names:
            await self._get_agent(AgentId(name=name, namespace=namespace))
