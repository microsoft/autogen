import asyncio
import inspect
import json
import logging
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
    Mapping,
    ParamSpec,
    Set,
    Type,
    TypeVar,
    cast,
)

import grpc
from grpc.aio import StreamStreamCall
from typing_extensions import Self

from ..core import (
    MESSAGE_TYPE_REGISTRY,
    Agent,
    AgentId,
    AgentInstantiationContext,
    AgentMetadata,
    AgentRuntime,
    AgentType,
    CancellationToken,
    MessageContext,
    Subscription,
    TopicId,
)
from ._helpers import get_impl
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

P = ParamSpec("P")
T = TypeVar("T", bound=Agent)


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


class WorkerAgentRuntime(AgentRuntime):
    def __init__(self) -> None:
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
        self._subscriptions: List[Subscription] = []
        self._seen_topics: Set[TopicId] = set()
        self._subscribed_recipients: DefaultDict[TopicId, List[AgentId]] = defaultdict(list)

    async def start(self, host_connection_string: str) -> None:
        if self._running:
            raise ValueError("Runtime is already running.")
        logger.info(f"Connecting to host: {host_connection_string}")
        self._host_connection = await HostConnection.from_connection_string(host_connection_string)
        logger.info("connection")
        if self._read_task is None:
            self._read_task = asyncio.create_task(self._run_read_loop())
        self._running = True

    async def _run_read_loop(self) -> None:
        logger.info("Starting read loop")
        # TODO: catch exceptions and reconnect
        while self._running:
            try:
                message = await self._host_connection.recv()  # type: ignore
                logger.info("Got message: %s", message)
                oneofcase = Message.WhichOneof(message, "message")
                match oneofcase:
                    case "registerAgentType":
                        logger.warn("Cant handle registerAgentType, skipping.")
                    case "request":
                        request: RpcRequest = message.request
                        task = asyncio.create_task(self._process_request(request))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    case "response":
                        response: RpcResponse = message.response
                        task = asyncio.create_task(self._process_response(response))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    case "event":
                        event: Event = message.event
                        task = asyncio.create_task(self._process_event(event))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    case None:
                        logger.warn("No message")
            except Exception as e:
                logger.error("Error in read loop", exc_info=e)

    async def stop(self) -> None:
        self._running = False
        if self._host_connection is not None:
            await self._host_connection.close()
        if self._read_task is not None:
            await self._read_task

    @property
    def _known_agent_names(self) -> Set[str]:
        return set(self._agent_factories.keys())

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
        assert self._host_connection is not None
        # create a new future for the result
        future = asyncio.get_event_loop().create_future()
        async with self._pending_requests_lock:
            self._next_request_id += 1
            request_id = self._next_request_id
        request_id_str = str(request_id)
        self._pending_requests[request_id_str] = future
        sender = cast(AgentId, sender)
        method = MESSAGE_TYPE_REGISTRY.type_name(message)
        serialized_message = MESSAGE_TYPE_REGISTRY.serialize(message, type_name=method)
        runtime_message = Message(
            request=RpcRequest(
                request_id=request_id_str,
                target=AgentIdProto(name=recipient.type, namespace=recipient.key),
                source=AgentIdProto(name=sender.type, namespace=sender.key),
                method=method,
                data=serialized_message,
            )
        )
        # TODO: Find a way to handle timeouts/errors
        task = asyncio.create_task(self._host_connection.send(runtime_message))
        self._background_tasks.add(task)
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
        assert self._host_connection is not None
        message_type = MESSAGE_TYPE_REGISTRY.type_name(message)
        serialized_message = MESSAGE_TYPE_REGISTRY.serialize(message, type_name=message_type)
        message = Message(
            event=Event(
                topic_type=topic_id.type, topic_source=topic_id.source, data_type=message_type, data=serialized_message
            )
        )

        async def write_message() -> None:
            assert self._host_connection is not None
            await self._host_connection.send(message)

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

    async def _process_request(self, request: RpcRequest) -> None:
        assert self._host_connection is not None
        target = AgentId(request.target.name, request.target.namespace)
        source = AgentId(request.source.name, request.source.namespace)

        try:
            logging.info(f"Processing request from {source} to {target}")
            target_agent = await self._get_agent(target)
            message_context = MessageContext(
                sender=source,
                topic_id=None,
                is_rpc=True,
                cancellation_token=CancellationToken(),
            )
            message = MESSAGE_TYPE_REGISTRY.deserialize(request.data, type_name=request.method)
            response = await target_agent.on_message(message, ctx=message_context)
            serialized_response = MESSAGE_TYPE_REGISTRY.serialize(response, type_name=request.method)
            response_message = Message(
                response=RpcResponse(
                    request_id=request.request_id,
                    result=serialized_response,
                )
            )
        except BaseException as e:
            response_message = Message(
                response=RpcResponse(
                    request_id=request.request_id,
                    error=str(e),
                )
            )

        # Send the response.
        await self._host_connection.send(response_message)

    async def _process_response(self, response: RpcResponse) -> None:
        # TODO: deserialize the response and set the future result
        future = self._pending_requests.pop(response.request_id)
        if len(response.error) > 0:
            future.set_exception(Exception(response.error))
        else:
            future.set_result(response.result)

    async def _process_event(self, event: Event) -> None:
        ...
        # message = MESSAGE_TYPE_REGISTRY.deserialize(event.data, type_name=event.data_type)

        # for agent_id in self._per_type_subscribers[
        #                     (namespace, MESSAGE_TYPE_REGISTRY.type_name(message))
        #                 ]:

        #                     agent = await self._get_agent(agent_id)
        #                     message_context = MessageContext(
        #                         # TODO: should sender be in the proto even for published events?
        #                         sender=None,
        #                         # TODO: topic_id
        #                         topic_id=None,
        #                         is_rpc=False,
        #                         cancellation_token=CancellationToken(),
        #                     )
        #                     try:
        #                         await agent.on_message(message, ctx=message_context)
        #                         logger.info("%s handled event %s", agent_id, message)
        #                     except Exception as e:
        #                         event_logger.error("Error handling message", exc_info=e)

    async def register(
        self,
        type: str,
        agent_factory: Callable[[], T | Awaitable[T]],
    ) -> AgentType:
        if type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")
        self._agent_factories[type] = agent_factory

        assert self._host_connection is not None
        message = Message(registerAgentType=RegisterAgentType(type=type))
        await self._host_connection.send(message)
        logger.info("Sent registerAgentType message for %s", type)
        return AgentType(type)

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
        raise NotImplementedError("try_get_underlying_agent_instance is not yet implemented.")

    async def add_subscription(self, subscription: Subscription) -> None:
        raise NotImplementedError("Subscriptions are not yet implemented.")

    async def remove_subscription(self, id: str) -> None:
        raise NotImplementedError("Subscriptions are not yet implemented.")

    async def get(
        self, id_or_type: AgentId | AgentType | str, /, key: str = "default", *, lazy: bool = True
    ) -> AgentId:
        return await get_impl(
            id_or_type=id_or_type,
            key=key,
            lazy=lazy,
            instance_getter=self._get_agent,
        )
