from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import warnings
from asyncio import CancelledError, Future, Task
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, DefaultDict, Dict, List, Mapping, ParamSpec, Set, Type, TypeVar, cast

from ..core import (
    MESSAGE_TYPE_REGISTRY,
    Agent,
    AgentId,
    AgentInstantiationContext,
    AgentMetadata,
    AgentProxy,
    AgentRuntime,
    CancellationToken,
)
from ..core.exceptions import MessageDroppedException
from ..core.intervention import DropMessage, InterventionHandler

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


class Counter:
    def __init__(self) -> None:
        self._count: int = 0
        self.threadLock = threading.Lock()

    def increment(self) -> None:
        self.threadLock.acquire()
        self._count += 1
        self.threadLock.release()

    def get(self) -> int:
        return self._count

    def decrement(self) -> None:
        self.threadLock.acquire()
        self._count -= 1
        self.threadLock.release()


class RunContext:
    class RunState(Enum):
        RUNNING = 0
        CANCELLED = 1
        UNTIL_IDLE = 2

    def __init__(self, runtime: SingleThreadedAgentRuntime) -> None:
        self._runtime = runtime
        self._run_state = RunContext.RunState.RUNNING
        self._run_task = asyncio.create_task(self._run())
        self._lock = asyncio.Lock()

    async def _run(self) -> None:
        while True:
            async with self._lock:
                if self._run_state == RunContext.RunState.CANCELLED:
                    return
                elif self._run_state == RunContext.RunState.UNTIL_IDLE:
                    if self._runtime.idle:
                        return

                await self._runtime.process_next()

    async def stop(self) -> None:
        async with self._lock:
            self._run_state = RunContext.RunState.CANCELLED
        await self._run_task

    async def stop_when_idle(self) -> None:
        async with self._lock:
            self._run_state = RunContext.RunState.UNTIL_IDLE
        await self._run_task


class SingleThreadedAgentRuntime(AgentRuntime):
    def __init__(self, *, intervention_handler: InterventionHandler | None = None) -> None:
        self._message_queue: List[PublishMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope] = []
        # (namespace, type) -> List[AgentId]
        self._per_type_subscribers: DefaultDict[tuple[str, str], Set[AgentId]] = defaultdict(set)
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._intervention_handler = intervention_handler
        self._known_namespaces: set[str] = set()
        self._outstanding_tasks = Counter()
        self._background_tasks: Set[Task[Any]] = set()

    @property
    def unprocessed_messages(
        self,
    ) -> Sequence[PublishMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope]:
        return self._message_queue

    @property
    def outstanding_tasks(self) -> int:
        return self._outstanding_tasks.get()

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
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        # event_logger.info(
        #     MessageEvent(
        #         payload=message,
        #         sender=sender,
        #         receiver=recipient,
        #         kind=MessageKind.DIRECT,
        #         delivery_stage=DeliveryStage.SEND,
        #     )
        # )

        future = asyncio.get_event_loop().create_future()
        if recipient.type not in self._known_agent_names:
            future.set_exception(Exception("Recipient not found"))

        if sender is not None and sender.key != recipient.key:
            raise ValueError("Sender and recipient must be in the same namespace to communicate.")

        await self._process_seen_namespace(recipient.key)

        content = message.__dict__ if hasattr(message, "__dict__") else message
        logger.info(f"Sending message of type {type(message).__name__} to {recipient.type}: {content}")

        self._message_queue.append(
            SendMessageEnvelope(
                message=message,
                recipient=recipient,
                future=future,
                cancellation_token=cancellation_token,
                sender=sender,
            )
        )

        cancellation_token.link_future(future)

        return await future

    async def publish_message(
        self,
        message: Any,
        *,
        namespace: str | None = None,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        content = message.__dict__ if hasattr(message, "__dict__") else message
        logger.info(f"Publishing message of type {type(message).__name__} to all subscribers: {content}")

        # event_logger.info(
        #     MessageEvent(
        #         payload=message,
        #         sender=sender,
        #         receiver=None,
        #         kind=MessageKind.PUBLISH,
        #         delivery_stage=DeliveryStage.SEND,
        #     )
        # )

        if sender is None and namespace is None:
            raise ValueError("Namespace must be provided if sender is not provided.")

        sender_namespace = sender.key if sender is not None else None
        explicit_namespace = namespace
        if explicit_namespace is not None and sender_namespace is not None and explicit_namespace != sender_namespace:
            raise ValueError(
                f"Explicit namespace {explicit_namespace} does not match sender namespace {sender_namespace}"
            )

        assert explicit_namespace is not None or sender_namespace is not None
        namespace = cast(str, explicit_namespace or sender_namespace)
        await self._process_seen_namespace(namespace)

        self._message_queue.append(
            PublishMessageEnvelope(
                message=message,
                cancellation_token=cancellation_token,
                sender=sender,
                namespace=namespace,
            )
        )

    async def save_state(self) -> Mapping[str, Any]:
        state: Dict[str, Dict[str, Any]] = {}
        for agent_id in self._instantiated_agents:
            state[str(agent_id)] = dict((await self._get_agent(agent_id)).save_state())
        return state

    async def load_state(self, state: Mapping[str, Any]) -> None:
        for agent_id_str in state:
            agent_id = AgentId.from_str(agent_id_str)
            if agent_id.type in self._known_agent_names:
                (await self._get_agent(agent_id)).load_state(state[str(agent_id)])

    async def _process_send(self, message_envelope: SendMessageEnvelope) -> None:
        recipient = message_envelope.recipient
        # todo: check if recipient is in the known namespaces
        # assert recipient in self._agents

        try:
            # TODO use id
            sender_name = message_envelope.sender.type if message_envelope.sender is not None else "Unknown"
            logger.info(
                f"Calling message handler for {recipient} with message type {type(message_envelope.message).__name__} sent by {sender_name}"
            )
            # event_logger.info(
            #     MessageEvent(
            #         payload=message_envelope.message,
            #         sender=message_envelope.sender,
            #         receiver=recipient,
            #         kind=MessageKind.DIRECT,
            #         delivery_stage=DeliveryStage.DELIVER,
            #     )
            # )
            recipient_agent = await self._get_agent(recipient)
            response = await recipient_agent.on_message(
                message_envelope.message,
                cancellation_token=message_envelope.cancellation_token,
            )
        except BaseException as e:
            message_envelope.future.set_exception(e)
            return

        self._message_queue.append(
            ResponseMessageEnvelope(
                message=response,
                future=message_envelope.future,
                sender=message_envelope.recipient,
                recipient=message_envelope.sender,
            )
        )
        self._outstanding_tasks.decrement()

    async def _process_publish(self, message_envelope: PublishMessageEnvelope) -> None:
        responses: List[Awaitable[Any]] = []
        target_namespace = message_envelope.namespace
        for agent_id in self._per_type_subscribers[
            (target_namespace, MESSAGE_TYPE_REGISTRY.type_name(message_envelope.message))
        ]:
            if message_envelope.sender is not None and agent_id.type == message_envelope.sender.type:
                continue

            sender_agent = (
                await self._get_agent(message_envelope.sender) if message_envelope.sender is not None else None
            )
            sender_name = str(sender_agent.id) if sender_agent is not None else "Unknown"
            logger.info(
                f"Calling message handler for {agent_id.type} with message type {type(message_envelope.message).__name__} published by {sender_name}"
            )
            # event_logger.info(
            #     MessageEvent(
            #         payload=message_envelope.message,
            #         sender=message_envelope.sender,
            #         receiver=agent,
            #         kind=MessageKind.PUBLISH,
            #         delivery_stage=DeliveryStage.DELIVER,
            #     )
            # )

            agent = await self._get_agent(agent_id)
            future = agent.on_message(
                message_envelope.message,
                cancellation_token=message_envelope.cancellation_token,
            )
            responses.append(future)

        try:
            _all_responses = await asyncio.gather(*responses)
        except BaseException as e:
            # Ignore cancelled errors from logs
            if isinstance(e, CancelledError):
                return
            logger.error("Error processing publish message", exc_info=True)
        finally:
            self._outstanding_tasks.decrement()
        # TODO if responses are given for a publish

    async def _process_response(self, message_envelope: ResponseMessageEnvelope) -> None:
        content = (
            message_envelope.message.__dict__
            if hasattr(message_envelope.message, "__dict__")
            else message_envelope.message
        )
        logger.info(
            f"Resolving response with message type {type(message_envelope.message).__name__} for recipient {message_envelope.recipient} from {message_envelope.sender.type}: {content}"
        )
        # event_logger.info(
        #     MessageEvent(
        #         payload=message_envelope.message,
        #         sender=message_envelope.sender,
        #         receiver=message_envelope.recipient,
        #         kind=MessageKind.RESPOND,
        #         delivery_stage=DeliveryStage.DELIVER,
        #     )
        # )
        self._outstanding_tasks.decrement()
        message_envelope.future.set_result(message_envelope.message)

    async def process_next(self) -> None:
        """Process the next message in the queue."""

        if len(self._message_queue) == 0:
            # Yield control to the event loop to allow other tasks to run
            await asyncio.sleep(0)
            return

        message_envelope = self._message_queue.pop(0)

        match message_envelope:
            case SendMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._intervention_handler is not None:
                    try:
                        temp_message = await self._intervention_handler.on_send(
                            message, sender=sender, recipient=recipient
                        )
                    except BaseException as e:
                        future.set_exception(e)
                        return
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = temp_message
                self._outstanding_tasks.increment()
                task = asyncio.create_task(self._process_send(message_envelope))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            case PublishMessageEnvelope(
                message=message,
                sender=sender,
            ):
                if self._intervention_handler is not None:
                    try:
                        temp_message = await self._intervention_handler.on_publish(message, sender=sender)
                    except BaseException as e:
                        # TODO: we should raise the intervention exception to the publisher.
                        logger.error(f"Exception raised in in intervention handler: {e}", exc_info=True)
                        return
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        # TODO log message dropped
                        return

                    message_envelope.message = temp_message
                self._outstanding_tasks.increment()
                task = asyncio.create_task(self._process_publish(message_envelope))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            case ResponseMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._intervention_handler is not None:
                    try:
                        temp_message = await self._intervention_handler.on_response(
                            message, sender=sender, recipient=recipient
                        )
                    except BaseException as e:
                        # TODO: should we raise the exception to sender of the response instead?
                        future.set_exception(e)
                        return
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = temp_message
                self._outstanding_tasks.increment()
                task = asyncio.create_task(self._process_response(message_envelope))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        # Yield control to the message loop to allow other tasks to run
        await asyncio.sleep(0)

    @property
    def idle(self) -> bool:
        return len(self._message_queue) == 0 and self._outstanding_tasks.get() == 0

    def start(self) -> RunContext:
        return RunContext(self)

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        return (await self._get_agent(agent)).metadata

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        return (await self._get_agent(agent)).save_state()

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        (await self._get_agent(agent)).load_state(state)

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
            await self._get_agent(AgentId(type=name, key=namespace))

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
        await self._process_seen_namespace(agent_id.key)
        if agent_id in self._instantiated_agents:
            return self._instantiated_agents[agent_id]

        if agent_id.type not in self._agent_factories:
            raise LookupError(f"Agent with name {agent_id.type} not found.")

        agent_factory = self._agent_factories[agent_id.type]

        agent = await self._invoke_agent_factory(agent_factory, agent_id)
        for message_type in agent.metadata["subscriptions"]:
            self._per_type_subscribers[(agent_id.key, message_type)].add(agent_id)
        self._instantiated_agents[agent_id] = agent
        return agent

    async def get(self, name: str, *, namespace: str = "default") -> AgentId:
        return (await self._get_agent(AgentId(type=name, key=namespace))).id

    async def get_proxy(self, name: str, *, namespace: str = "default") -> AgentProxy:
        id = await self.get(name, namespace=namespace)
        return AgentProxy(id, self)

    # TODO: uncomment out the following type ignore when this is fixed in mypy: https://github.com/python/mypy/issues/3737
    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        if id.type not in self._agent_factories:
            raise LookupError(f"Agent with name {id.type} not found.")

        # TODO: check if remote
        agent_instance = await self._get_agent(id)

        if not isinstance(agent_instance, type):
            raise TypeError(f"Agent with name {id.type} is not of type {type.__name__}")

        return agent_instance

    # Hydrate the agent instances in a namespace. The primary reason for this is
    # to ensure message type subscriptions are set up.
    async def _process_seen_namespace(self, namespace: str) -> None:
        if namespace in self._known_namespaces:
            return

        self._known_namespaces.add(namespace)
        for name in self._known_agent_names:
            await self._get_agent(AgentId(type=name, key=namespace))
