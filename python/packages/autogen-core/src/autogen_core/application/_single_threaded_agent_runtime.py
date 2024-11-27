from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import uuid
import warnings
from asyncio import CancelledError, Future, Task
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Mapping, ParamSpec, Set, Type, TypeVar, cast

from opentelemetry.trace import TracerProvider
from typing_extensions import deprecated

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
from ..base.exceptions import MessageDroppedException
from ..base.intervention import DropMessage, InterventionHandler
from ._helpers import SubscriptionManager, get_impl
from .telemetry import EnvelopeMetadata, MessageRuntimeTracingConfig, TraceHelper, get_telemetry_envelope_metadata

logger = logging.getLogger("autogen_core")
event_logger = logging.getLogger("autogen_core.events")

# We use a type parameter in some functions which shadows the built-in `type` function.
# This is a workaround to avoid shadowing the built-in `type` function.
type_func_alias = type


@dataclass(kw_only=True)
class PublishMessageEnvelope:
    """A message envelope for publishing messages to all agents that can handle
    the message of the type T."""

    message: Any
    cancellation_token: CancellationToken
    sender: AgentId | None
    topic_id: TopicId
    metadata: EnvelopeMetadata | None = None
    message_id: str


@dataclass(kw_only=True)
class SendMessageEnvelope:
    """A message envelope for sending a message to a specific agent that can handle
    the message of the type T."""

    message: Any
    sender: AgentId | None
    recipient: AgentId
    future: Future[Any]
    cancellation_token: CancellationToken
    metadata: EnvelopeMetadata | None = None


@dataclass(kw_only=True)
class ResponseMessageEnvelope:
    """A message envelope for sending a response to a message."""

    message: Any
    future: Future[Any]
    sender: AgentId
    recipient: AgentId | None
    metadata: EnvelopeMetadata | None = None


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
        self._end_condition: Callable[[], bool] = self._stop_when_cancelled
        self._run_task = asyncio.create_task(self._run())
        self._lock = asyncio.Lock()

    async def _run(self) -> None:
        while True:
            async with self._lock:
                if self._end_condition():
                    return

                await self._runtime.process_next()

    async def stop(self) -> None:
        async with self._lock:
            self._run_state = RunContext.RunState.CANCELLED
            self._end_condition = self._stop_when_cancelled
        await self._run_task

    async def stop_when_idle(self) -> None:
        async with self._lock:
            self._run_state = RunContext.RunState.UNTIL_IDLE
            self._end_condition = self._stop_when_idle
        await self._run_task

    async def stop_when(self, condition: Callable[[], bool]) -> None:
        async with self._lock:
            self._end_condition = condition
        await self._run_task

    def _stop_when_cancelled(self) -> bool:
        return self._run_state == RunContext.RunState.CANCELLED

    def _stop_when_idle(self) -> bool:
        return self._run_state == RunContext.RunState.UNTIL_IDLE and self._runtime.idle


def _warn_if_none(value: Any, handler_name: str) -> None:
    """
    Utility function to check if the intervention handler returned None and issue a warning.

    Args:
        value: The return value to check
        handler_name: Name of the intervention handler method for the warning message
    """
    if value is None:
        warnings.warn(
            f"Intervention handler {handler_name} returned None. This might be unintentional. "
            "Consider returning the original message or DropMessage explicitly.",
            RuntimeWarning,
            stacklevel=2,
        )


class SingleThreadedAgentRuntime(AgentRuntime):
    def __init__(
        self,
        *,
        intervention_handlers: List[InterventionHandler] | None = None,
        tracer_provider: TracerProvider | None = None,
    ) -> None:
        self._tracer_helper = TraceHelper(tracer_provider, MessageRuntimeTracingConfig("SingleThreadedAgentRuntime"))
        self._message_queue: List[PublishMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope] = []
        # (namespace, type) -> List[AgentId]
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._intervention_handlers = intervention_handlers
        self._outstanding_tasks = Counter()
        self._background_tasks: Set[Task[Any]] = set()
        self._subscription_manager = SubscriptionManager()
        self._run_context: RunContext | None = None
        self._serialization_registry = SerializationRegistry()

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

        with self._tracer_helper.trace_block(
            "create",
            recipient,
            parent=None,
            extraAttributes={"message_type": type(message).__name__},
        ):
            future = asyncio.get_event_loop().create_future()
            if recipient.type not in self._known_agent_names:
                future.set_exception(Exception("Recipient not found"))

            content = message.__dict__ if hasattr(message, "__dict__") else message
            logger.info(f"Sending message of type {type(message).__name__} to {recipient.type}: {content}")

            self._message_queue.append(
                SendMessageEnvelope(
                    message=message,
                    recipient=recipient,
                    future=future,
                    cancellation_token=cancellation_token,
                    sender=sender,
                    metadata=get_telemetry_envelope_metadata(),
                )
            )

            cancellation_token.link_future(future)

            return await future

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> None:
        with self._tracer_helper.trace_block(
            "create",
            topic_id,
            parent=None,
            extraAttributes={"message_type": type(message).__name__},
        ):
            if cancellation_token is None:
                cancellation_token = CancellationToken()
            content = message.__dict__ if hasattr(message, "__dict__") else message
            logger.info(f"Publishing message of type {type(message).__name__} to all subscribers: {content}")

            if message_id is None:
                message_id = str(uuid.uuid4())

            # event_logger.info(
            #     MessageEvent(
            #         payload=message,
            #         sender=sender,
            #         receiver=None,
            #         kind=MessageKind.PUBLISH,
            #         delivery_stage=DeliveryStage.SEND,
            #     )
            # )

            self._message_queue.append(
                PublishMessageEnvelope(
                    message=message,
                    cancellation_token=cancellation_token,
                    sender=sender,
                    topic_id=topic_id,
                    metadata=get_telemetry_envelope_metadata(),
                    message_id=message_id,
                )
            )

    async def save_state(self) -> Mapping[str, Any]:
        state: Dict[str, Dict[str, Any]] = {}
        for agent_id in self._instantiated_agents:
            state[str(agent_id)] = dict(await (await self._get_agent(agent_id)).save_state())
        return state

    async def load_state(self, state: Mapping[str, Any]) -> None:
        for agent_id_str in state:
            agent_id = AgentId.from_str(agent_id_str)
            if agent_id.type in self._known_agent_names:
                await (await self._get_agent(agent_id)).load_state(state[str(agent_id)])

    async def _process_send(self, message_envelope: SendMessageEnvelope) -> None:
        with self._tracer_helper.trace_block("send", message_envelope.recipient, parent=message_envelope.metadata):
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
                message_context = MessageContext(
                    sender=message_envelope.sender,
                    topic_id=None,
                    is_rpc=True,
                    cancellation_token=message_envelope.cancellation_token,
                    # Will be fixed when send API removed
                    message_id="NOT_DEFINED_TODO_FIX",
                )
                with MessageHandlerContext.populate_context(recipient_agent.id):
                    response = await recipient_agent.on_message(
                        message_envelope.message,
                        ctx=message_context,
                    )
            except CancelledError as e:
                if not message_envelope.future.cancelled():
                    message_envelope.future.set_exception(e)
                self._outstanding_tasks.decrement()
                return
            except BaseException as e:
                message_envelope.future.set_exception(e)
                self._outstanding_tasks.decrement()
                return

            self._message_queue.append(
                ResponseMessageEnvelope(
                    message=response,
                    future=message_envelope.future,
                    sender=message_envelope.recipient,
                    recipient=message_envelope.sender,
                    metadata=get_telemetry_envelope_metadata(),
                )
            )
            self._outstanding_tasks.decrement()

    async def _process_publish(self, message_envelope: PublishMessageEnvelope) -> None:
        with self._tracer_helper.trace_block("publish", message_envelope.topic_id, parent=message_envelope.metadata):
            try:
                responses: List[Awaitable[Any]] = []
                recipients = await self._subscription_manager.get_subscribed_recipients(message_envelope.topic_id)
                for agent_id in recipients:
                    # Avoid sending the message back to the sender
                    if message_envelope.sender is not None and agent_id == message_envelope.sender:
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
                    message_context = MessageContext(
                        sender=message_envelope.sender,
                        topic_id=message_envelope.topic_id,
                        is_rpc=False,
                        cancellation_token=message_envelope.cancellation_token,
                        message_id=message_envelope.message_id,
                    )
                    agent = await self._get_agent(agent_id)

                    async def _on_message(agent: Agent, message_context: MessageContext) -> Any:
                        with self._tracer_helper.trace_block("process", agent.id, parent=None):
                            with MessageHandlerContext.populate_context(agent.id):
                                return await agent.on_message(
                                    message_envelope.message,
                                    ctx=message_context,
                                )

                    future = _on_message(agent, message_context)
                    responses.append(future)

                await asyncio.gather(*responses)
            except BaseException as e:
                # Ignore cancelled errors from logs
                if isinstance(e, CancelledError):
                    return
                logger.error("Error processing publish message", exc_info=True)
            finally:
                self._outstanding_tasks.decrement()
            # TODO if responses are given for a publish

    async def _process_response(self, message_envelope: ResponseMessageEnvelope) -> None:
        with self._tracer_helper.trace_block("ack", message_envelope.recipient, parent=message_envelope.metadata):
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
            if not message_envelope.future.cancelled():
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
                if self._intervention_handlers is not None:
                    for handler in self._intervention_handlers:
                        with self._tracer_helper.trace_block(
                            "intercept", handler.__class__.__name__, parent=message_envelope.metadata
                        ):
                            try:
                                temp_message = await handler.on_send(message, sender=sender, recipient=recipient)
                                _warn_if_none(temp_message, "on_send")
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
                if self._intervention_handlers is not None:
                    for handler in self._intervention_handlers:
                        with self._tracer_helper.trace_block(
                            "intercept", handler.__class__.__name__, parent=message_envelope.metadata
                        ):
                            try:
                                temp_message = await handler.on_publish(message, sender=sender)
                                _warn_if_none(temp_message, "on_publish")
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
                if self._intervention_handlers is not None:
                    for handler in self._intervention_handlers:
                        try:
                            temp_message = await handler.on_response(message, sender=sender, recipient=recipient)
                            _warn_if_none(temp_message, "on_response")
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

    def start(self) -> None:
        """Start the runtime message processing loop."""
        if self._run_context is not None:
            raise RuntimeError("Runtime is already started")
        self._run_context = RunContext(self)

    async def stop(self) -> None:
        """Stop the runtime message processing loop."""
        if self._run_context is None:
            raise RuntimeError("Runtime is not started")
        await self._run_context.stop()
        self._run_context = None

    async def stop_when_idle(self) -> None:
        """Stop the runtime message processing loop when there is
        no outstanding message being processed or queued."""
        if self._run_context is None:
            raise RuntimeError("Runtime is not started")
        await self._run_context.stop_when_idle()
        self._run_context = None

    async def stop_when(self, condition: Callable[[], bool]) -> None:
        """Stop the runtime message processing loop when the condition is met."""
        if self._run_context is None:
            raise RuntimeError("Runtime is not started")
        await self._run_context.stop_when(condition)
        self._run_context = None

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        return (await self._get_agent(agent)).metadata

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        return await (await self._get_agent(agent)).save_state()

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        await (await self._get_agent(agent)).load_state(state)

    @deprecated(
        "Use your agent's `register` method directly instead of this method. See documentation for latest usage."
    )
    async def register(
        self,
        type: str,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        subscriptions: Callable[[], list[Subscription] | Awaitable[list[Subscription]]]
        | list[Subscription]
        | None = None,
    ) -> AgentType:
        if type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")

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

        self._agent_factories[type] = agent_factory
        return AgentType(type)

    async def register_factory(
        self,
        *,
        type: AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        expected_class: type[T],
    ) -> AgentType:
        if type.type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")

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
            raise LookupError(f"Agent with name {agent_id.type} not found.")

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
            raise TypeError(
                f"Agent with name {id.type} is not of type {type.__name__}. It is of type {type_func_alias(agent_instance).__name__}"
            )

        return agent_instance

    async def add_subscription(self, subscription: Subscription) -> None:
        await self._subscription_manager.add_subscription(subscription)

    async def remove_subscription(self, id: str) -> None:
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
