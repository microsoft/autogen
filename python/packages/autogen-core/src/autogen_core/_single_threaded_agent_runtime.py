from __future__ import annotations

import asyncio
import inspect
import json
import logging
import sys
import uuid
import warnings
from asyncio import CancelledError, Future, Queue, Task
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Mapping, ParamSpec, Set, Type, TypeVar, cast

from opentelemetry.trace import TracerProvider

from .logging import (
    AgentConstructionExceptionEvent,
    DeliveryStage,
    MessageDroppedEvent,
    MessageEvent,
    MessageHandlerExceptionEvent,
    MessageKind,
)

if sys.version_info >= (3, 13):
    from asyncio import Queue, QueueShutDown
else:
    from ._queue import Queue, QueueShutDown  # type: ignore


from ._agent import Agent
from ._agent_id import AgentId
from ._agent_instantiation import AgentInstantiationContext
from ._agent_metadata import AgentMetadata
from ._agent_runtime import AgentRuntime
from ._agent_type import AgentType
from ._cancellation_token import CancellationToken
from ._intervention import DropMessage, InterventionHandler
from ._message_context import MessageContext
from ._message_handler_context import MessageHandlerContext
from ._runtime_impl_helpers import SubscriptionManager, get_impl
from ._serialization import JSON_DATA_CONTENT_TYPE, MessageSerializer, SerializationRegistry
from ._subscription import Subscription
from ._telemetry import EnvelopeMetadata, MessageRuntimeTracingConfig, TraceHelper, get_telemetry_envelope_metadata
from ._topic import TopicId
from .exceptions import MessageDroppedException

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
    message_id: str


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


class RunContext:
    def __init__(self, runtime: SingleThreadedAgentRuntime) -> None:
        self._runtime = runtime
        self._run_task = asyncio.create_task(self._run())
        self._stopped = asyncio.Event()

    async def _run(self) -> None:
        while True:
            if self._stopped.is_set():
                return

            await self._runtime._process_next()  # type: ignore

    async def stop(self) -> None:
        self._stopped.set()
        self._runtime._message_queue.shutdown(immediate=True)  # type: ignore
        await self._run_task

    async def stop_when_idle(self) -> None:
        await self._runtime._message_queue.join()  # type: ignore
        self._stopped.set()
        self._runtime._message_queue.shutdown(immediate=True)  # type: ignore
        await self._run_task

    async def stop_when(self, condition: Callable[[], bool], check_period: float = 1.0) -> None:
        async def check_condition() -> None:
            while not condition():
                await asyncio.sleep(check_period)
            await self.stop()

        await asyncio.create_task(check_condition())


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
    """A single-threaded agent runtime that processes all messages using a single asyncio queue.
    Messages are delivered in the order they are received, and the runtime processes
    each message in a separate asyncio task concurrently.

    .. note::

        This runtime is suitable for development and standalone applications.
        It is not suitable for high-throughput or high-concurrency scenarios.

    Args:
        intervention_handlers (List[InterventionHandler], optional): A list of intervention
            handlers that can intercept messages before they are sent or published. Defaults to None.
        tracer_provider (TracerProvider, optional): The tracer provider to use for tracing. Defaults to None.
            Additionally, you can set `AUTOGEN_DISABLE_RUNTIME_TRACING` to `true` to disable the agent runtime telemetry if you don't have access to the runtime constructor. For example, if you are using `ComponentConfig`.
        ignore_unhandled_exceptions (bool, optional): Whether to ignore unhandled exceptions in that occur in agent event handlers. Any background exceptions will be raised on the next call to `process_next` or from an awaited `stop`, `stop_when_idle` or `stop_when`. Note, this does not apply to RPC handlers. Defaults to True.

    Examples:

        A simple example of creating a runtime, registering an agent, sending a message and stopping the runtime:

        .. code-block:: python

            import asyncio
            from dataclasses import dataclass

            from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler


            @dataclass
            class MyMessage:
                content: str


            class MyAgent(RoutedAgent):
                @message_handler
                async def handle_my_message(self, message: MyMessage, ctx: MessageContext) -> None:
                    print(f"Received message: {message.content}")


            async def main() -> None:
                # Create a runtime and register the agent
                runtime = SingleThreadedAgentRuntime()
                await MyAgent.register(runtime, "my_agent", lambda: MyAgent("My agent"))

                # Start the runtime, send a message and stop the runtime
                runtime.start()
                await runtime.send_message(MyMessage("Hello, world!"), recipient=AgentId("my_agent", "default"))
                await runtime.stop()


            asyncio.run(main())

        An example of creating a runtime, registering an agent, publishing a message and stopping the runtime:

        .. code-block:: python

            import asyncio
            from dataclasses import dataclass

            from autogen_core import (
                DefaultTopicId,
                MessageContext,
                RoutedAgent,
                SingleThreadedAgentRuntime,
                default_subscription,
                message_handler,
            )


            @dataclass
            class MyMessage:
                content: str


            # The agent is subscribed to the default topic.
            @default_subscription
            class MyAgent(RoutedAgent):
                @message_handler
                async def handle_my_message(self, message: MyMessage, ctx: MessageContext) -> None:
                    print(f"Received message: {message.content}")


            async def main() -> None:
                # Create a runtime and register the agent
                runtime = SingleThreadedAgentRuntime()
                await MyAgent.register(runtime, "my_agent", lambda: MyAgent("My agent"))

                # Start the runtime.
                runtime.start()
                # Publish a message to the default topic that the agent is subscribed to.
                await runtime.publish_message(MyMessage("Hello, world!"), DefaultTopicId())
                # Wait for the message to be processed and then stop the runtime.
                await runtime.stop_when_idle()


            asyncio.run(main())

    """

    def __init__(
        self,
        *,
        intervention_handlers: List[InterventionHandler] | None = None,
        tracer_provider: TracerProvider | None = None,
        ignore_unhandled_exceptions: bool = True,
    ) -> None:
        self._tracer_helper = TraceHelper(tracer_provider, MessageRuntimeTracingConfig("SingleThreadedAgentRuntime"))
        self._message_queue: Queue[PublishMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope] = Queue()
        # (namespace, type) -> List[AgentId]
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._intervention_handlers = intervention_handlers
        self._background_tasks: Set[Task[Any]] = set()
        self._subscription_manager = SubscriptionManager()
        self._run_context: RunContext | None = None
        self._serialization_registry = SerializationRegistry()
        self._ignore_unhandled_handler_exceptions = ignore_unhandled_exceptions
        self._background_exception: BaseException | None = None
        self._agent_instance_types: Dict[str, Type[Agent]] = {}

    @property
    def unprocessed_messages_count(
        self,
    ) -> int:
        return self._message_queue.qsize()

    @property
    def _known_agent_names(self) -> Set[str]:
        return set(self._agent_factories.keys())

    async def _create_otel_attributes(
        self,
        sender_agent_id: AgentId | None = None,
        recipient_agent_id: AgentId | None = None,
        message_context: MessageContext | None = None,
        message: Any = None,
    ) -> Mapping[str, str]:
        """Create OpenTelemetry attributes for the given agent and message.

        Args:
            sender_agent (Agent, optional): The sender agent instance.
            recipient_agent (Agent, optional): The recipient agent instance.
            message (Any): The message instance.

        Returns:
            Attributes: A dictionary of OpenTelemetry attributes.
        """
        if not sender_agent_id and not recipient_agent_id and not message:
            return {}
        attributes: Dict[str, str] = {}
        if sender_agent_id:
            sender_agent = await self._get_agent(sender_agent_id)
            attributes["sender_agent_type"] = sender_agent.id.type
            attributes["sender_agent_class"] = sender_agent.__class__.__name__
        if recipient_agent_id:
            recipient_agent = await self._get_agent(recipient_agent_id)
            attributes["recipient_agent_type"] = recipient_agent.id.type
            attributes["recipient_agent_class"] = recipient_agent.__class__.__name__

        if message_context:
            serialized_message_context = {
                "sender": str(message_context.sender),
                "topic_id": str(message_context.topic_id),
                "is_rpc": message_context.is_rpc,
                "message_id": message_context.message_id,
            }
            attributes["message_context"] = json.dumps(serialized_message_context)

        if message:
            try:
                serialized_message = self._try_serialize(message)
            except Exception as e:
                serialized_message = str(e)
        else:
            serialized_message = "No Message"
        attributes["message"] = serialized_message

        return attributes

    # Returns the response of the message
    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> Any:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        if message_id is None:
            message_id = str(uuid.uuid4())

        event_logger.info(
            MessageEvent(
                payload=self._try_serialize(message),
                sender=sender,
                receiver=recipient,
                kind=MessageKind.DIRECT,
                delivery_stage=DeliveryStage.SEND,
            )
        )

        with self._tracer_helper.trace_block(
            "create",
            recipient,
            parent=None,
            extraAttributes={"message_type": type(message).__name__},
        ):
            future = asyncio.get_event_loop().create_future()
            if recipient.type not in self._known_agent_names:
                future.set_exception(Exception("Recipient not found"))
                return await future

            content = message.__dict__ if hasattr(message, "__dict__") else message
            logger.info(f"Sending message of type {type(message).__name__} to {recipient.type}: {content}")

            await self._message_queue.put(
                SendMessageEnvelope(
                    message=message,
                    recipient=recipient,
                    future=future,
                    cancellation_token=cancellation_token,
                    sender=sender,
                    metadata=get_telemetry_envelope_metadata(),
                    message_id=message_id,
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

            event_logger.info(
                MessageEvent(
                    payload=self._try_serialize(message),
                    sender=sender,
                    receiver=topic_id,
                    kind=MessageKind.PUBLISH,
                    delivery_stage=DeliveryStage.SEND,
                )
            )

            await self._message_queue.put(
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
        """Save the state of all instantiated agents.

        This method calls the :meth:`~autogen_core.BaseAgent.save_state` method on each agent and returns a dictionary
        mapping agent IDs to their state.

        .. note::
            This method does not currently save the subscription state. We will add this in the future.

        Returns:
            A dictionary mapping agent IDs to their state.

        """
        state: Dict[str, Dict[str, Any]] = {}
        for agent_id in self._instantiated_agents:
            state[str(agent_id)] = dict(await (await self._get_agent(agent_id)).save_state())
        return state

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the state of all instantiated agents.

        This method calls the :meth:`~autogen_core.BaseAgent.load_state` method on each agent with the state
        provided in the dictionary. The keys of the dictionary are the agent IDs, and the values are the state
        dictionaries returned by the :meth:`~autogen_core.BaseAgent.save_state` method.

        .. note::

            This method does not currently load the subscription state. We will add this in the future.

        """
        for agent_id_str in state:
            agent_id = AgentId.from_str(agent_id_str)
            if agent_id.type in self._known_agent_names:
                await (await self._get_agent(agent_id)).load_state(state[str(agent_id)])

    async def _process_send(self, message_envelope: SendMessageEnvelope) -> None:
        with self._tracer_helper.trace_block("send", message_envelope.recipient, parent=message_envelope.metadata):
            recipient = message_envelope.recipient

            if recipient.type not in self._known_agent_names:
                raise LookupError(f"Agent type '{recipient.type}' does not exist.")

            try:
                sender_id = str(message_envelope.sender) if message_envelope.sender is not None else "Unknown"
                logger.info(
                    f"Calling message handler for {recipient} with message type {type(message_envelope.message).__name__} sent by {sender_id}"
                )
                event_logger.info(
                    MessageEvent(
                        payload=self._try_serialize(message_envelope.message),
                        sender=message_envelope.sender,
                        receiver=recipient,
                        kind=MessageKind.DIRECT,
                        delivery_stage=DeliveryStage.DELIVER,
                    )
                )
                recipient_agent = await self._get_agent(recipient)

                message_context = MessageContext(
                    sender=message_envelope.sender,
                    topic_id=None,
                    is_rpc=True,
                    cancellation_token=message_envelope.cancellation_token,
                    message_id=message_envelope.message_id,
                )
                with self._tracer_helper.trace_block(
                    "process",
                    recipient_agent.id,
                    parent=message_envelope.metadata,
                    attributes=await self._create_otel_attributes(
                        sender_agent_id=message_envelope.sender,
                        recipient_agent_id=recipient,
                        message_context=message_context,
                        message=message_envelope.message,
                    ),
                ):
                    with MessageHandlerContext.populate_context(recipient_agent.id):
                        response = await recipient_agent.on_message(
                            message_envelope.message,
                            ctx=message_context,
                        )
            except CancelledError as e:
                if not message_envelope.future.cancelled():
                    message_envelope.future.set_exception(e)
                self._message_queue.task_done()
                event_logger.info(
                    MessageHandlerExceptionEvent(
                        payload=self._try_serialize(message_envelope.message),
                        handling_agent=recipient,
                        exception=e,
                    )
                )
                return
            except BaseException as e:
                message_envelope.future.set_exception(e)
                self._message_queue.task_done()
                event_logger.info(
                    MessageHandlerExceptionEvent(
                        payload=self._try_serialize(message_envelope.message),
                        handling_agent=recipient,
                        exception=e,
                    )
                )
                return

            event_logger.info(
                MessageEvent(
                    payload=self._try_serialize(response),
                    sender=message_envelope.recipient,
                    receiver=message_envelope.sender,
                    kind=MessageKind.RESPOND,
                    delivery_stage=DeliveryStage.SEND,
                )
            )

            await self._message_queue.put(
                ResponseMessageEnvelope(
                    message=response,
                    future=message_envelope.future,
                    sender=message_envelope.recipient,
                    recipient=message_envelope.sender,
                    metadata=get_telemetry_envelope_metadata(),
                )
            )
            self._message_queue.task_done()

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
                    event_logger.info(
                        MessageEvent(
                            payload=self._try_serialize(message_envelope.message),
                            sender=message_envelope.sender,
                            receiver=None,
                            kind=MessageKind.PUBLISH,
                            delivery_stage=DeliveryStage.DELIVER,
                        )
                    )
                    message_context = MessageContext(
                        sender=message_envelope.sender,
                        topic_id=message_envelope.topic_id,
                        is_rpc=False,
                        cancellation_token=message_envelope.cancellation_token,
                        message_id=message_envelope.message_id,
                    )
                    agent = await self._get_agent(agent_id)

                    async def _on_message(agent: Agent, message_context: MessageContext) -> Any:
                        with self._tracer_helper.trace_block(
                            "process",
                            agent.id,
                            parent=message_envelope.metadata,
                            attributes=await self._create_otel_attributes(
                                sender_agent_id=message_envelope.sender,
                                recipient_agent_id=agent.id,
                                message_context=message_context,
                                message=message_envelope.message,
                            ),
                        ):
                            with MessageHandlerContext.populate_context(agent.id):
                                try:
                                    return await agent.on_message(
                                        message_envelope.message,
                                        ctx=message_context,
                                    )
                                except BaseException as e:
                                    logger.error(f"Error processing publish message for {agent.id}", exc_info=True)
                                    event_logger.info(
                                        MessageHandlerExceptionEvent(
                                            payload=self._try_serialize(message_envelope.message),
                                            handling_agent=agent.id,
                                            exception=e,
                                        )
                                    )
                                    raise e

                    future = _on_message(agent, message_context)
                    responses.append(future)

                await asyncio.gather(*responses)
            except BaseException as e:
                if not self._ignore_unhandled_handler_exceptions:
                    self._background_exception = e
            finally:
                self._message_queue.task_done()
            # TODO if responses are given for a publish

    async def _process_response(self, message_envelope: ResponseMessageEnvelope) -> None:
        with self._tracer_helper.trace_block(
            "ack",
            message_envelope.recipient,
            parent=message_envelope.metadata,
            attributes=await self._create_otel_attributes(
                sender_agent_id=message_envelope.sender,
                recipient_agent_id=message_envelope.recipient,
                message=message_envelope.message,
            ),
        ):
            content = (
                message_envelope.message.__dict__
                if hasattr(message_envelope.message, "__dict__")
                else message_envelope.message
            )
            logger.info(
                f"Resolving response with message type {type(message_envelope.message).__name__} for recipient {message_envelope.recipient} from {message_envelope.sender.type}: {content}"
            )
            event_logger.info(
                MessageEvent(
                    payload=self._try_serialize(message_envelope.message),
                    sender=message_envelope.sender,
                    receiver=message_envelope.recipient,
                    kind=MessageKind.RESPOND,
                    delivery_stage=DeliveryStage.DELIVER,
                )
            )
            if not message_envelope.future.cancelled():
                message_envelope.future.set_result(message_envelope.message)
            self._message_queue.task_done()

    async def process_next(self) -> None:
        """Process the next message in the queue.

        If there is an unhandled exception in the background task, it will be raised here. `process_next` cannot be called again after an unhandled exception is raised.
        """
        await self._process_next()

    async def _process_next(self) -> None:
        """Process the next message in the queue."""

        if self._background_exception is not None:
            e = self._background_exception
            self._background_exception = None
            self._message_queue.shutdown(immediate=True)  # type: ignore
            raise e

        try:
            message_envelope = await self._message_queue.get()
        except QueueShutDown:
            if self._background_exception is not None:
                e = self._background_exception
                self._background_exception = None
                raise e from None
            return

        match message_envelope:
            case SendMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._intervention_handlers is not None:
                    for handler in self._intervention_handlers:
                        with self._tracer_helper.trace_block(
                            "intercept", handler.__class__.__name__, parent=message_envelope.metadata
                        ):
                            try:
                                message_context = MessageContext(
                                    sender=sender,
                                    topic_id=None,
                                    is_rpc=True,
                                    cancellation_token=message_envelope.cancellation_token,
                                    message_id=message_envelope.message_id,
                                )
                                temp_message = await handler.on_send(
                                    message, message_context=message_context, recipient=recipient
                                )
                                _warn_if_none(temp_message, "on_send")
                            except BaseException as e:
                                future.set_exception(e)
                                return
                            if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                                event_logger.info(
                                    MessageDroppedEvent(
                                        payload=self._try_serialize(message),
                                        sender=sender,
                                        receiver=recipient,
                                        kind=MessageKind.DIRECT,
                                    )
                                )
                                future.set_exception(MessageDroppedException())
                                return

                        message_envelope.message = temp_message
                task = asyncio.create_task(self._process_send(message_envelope))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            case PublishMessageEnvelope(
                message=message,
                sender=sender,
                topic_id=topic_id,
            ):
                if self._intervention_handlers is not None:
                    for handler in self._intervention_handlers:
                        with self._tracer_helper.trace_block(
                            "intercept", handler.__class__.__name__, parent=message_envelope.metadata
                        ):
                            try:
                                message_context = MessageContext(
                                    sender=sender,
                                    topic_id=topic_id,
                                    is_rpc=False,
                                    cancellation_token=message_envelope.cancellation_token,
                                    message_id=message_envelope.message_id,
                                )
                                temp_message = await handler.on_publish(message, message_context=message_context)
                                _warn_if_none(temp_message, "on_publish")
                            except BaseException as e:
                                # TODO: we should raise the intervention exception to the publisher.
                                logger.error(f"Exception raised in in intervention handler: {e}", exc_info=True)
                                return
                            if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                                event_logger.info(
                                    MessageDroppedEvent(
                                        payload=self._try_serialize(message),
                                        sender=sender,
                                        receiver=topic_id,
                                        kind=MessageKind.PUBLISH,
                                    )
                                )
                                return

                        message_envelope.message = temp_message

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
                            event_logger.info(
                                MessageDroppedEvent(
                                    payload=self._try_serialize(message),
                                    sender=sender,
                                    receiver=recipient,
                                    kind=MessageKind.RESPOND,
                                )
                            )
                            future.set_exception(MessageDroppedException())
                            return
                        message_envelope.message = temp_message
                task = asyncio.create_task(self._process_response(message_envelope))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        # Yield control to the message loop to allow other tasks to run
        await asyncio.sleep(0)

    def start(self) -> None:
        """Start the runtime message processing loop. This runs in a background task.

        Example:

        .. code-block:: python

            import asyncio
            from autogen_core import SingleThreadedAgentRuntime


            async def main() -> None:
                runtime = SingleThreadedAgentRuntime()
                runtime.start()

                # ... do other things ...

                await runtime.stop()


            asyncio.run(main())

        """
        if self._run_context is not None:
            raise RuntimeError("Runtime is already started")
        self._run_context = RunContext(self)

    async def close(self) -> None:
        """Calls :meth:`stop` if applicable and the :meth:`Agent.close` method on all instantiated agents"""
        # stop the runtime if it hasn't been stopped yet
        if self._run_context is not None:
            await self.stop()
        # close all the agents that have been instantiated
        for agent_id in self._instantiated_agents:
            agent = await self._get_agent(agent_id)
            await agent.close()

    async def stop(self) -> None:
        """Immediately stop the runtime message processing loop. The currently processing message will be completed, but all others following it will be discarded."""
        if self._run_context is None:
            raise RuntimeError("Runtime is not started")

        try:
            await self._run_context.stop()
        finally:
            self._run_context = None
            self._message_queue = Queue()

    async def stop_when_idle(self) -> None:
        """Stop the runtime message processing loop when there is
        no outstanding message being processed or queued. This is the most common way to stop the runtime."""
        if self._run_context is None:
            raise RuntimeError("Runtime is not started")

        try:
            await self._run_context.stop_when_idle()
        finally:
            self._run_context = None
            self._message_queue = Queue()

    async def stop_when(self, condition: Callable[[], bool]) -> None:
        """Stop the runtime message processing loop when the condition is met.

        .. caution::

            This method is not recommended to be used, and is here for legacy
            reasons. It will spawn a busy loop to continually check the
            condition. It is much more efficient to call `stop_when_idle` or
            `stop` instead. If you need to stop the runtime based on a
            condition, consider using a background task and asyncio.Event to
            signal when the condition is met and the background task should call
            stop.

        """
        if self._run_context is None:
            raise RuntimeError("Runtime is not started")
        await self._run_context.stop_when(condition)

        self._run_context = None
        self._message_queue = Queue()

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        return (await self._get_agent(agent)).metadata

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        return await (await self._get_agent(agent)).save_state()

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        await (await self._get_agent(agent)).load_state(state)

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
            try:
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

            except BaseException as e:
                event_logger.info(
                    AgentConstructionExceptionEvent(
                        agent_id=agent_id,
                        exception=e,
                    )
                )
                logger.error(f"Error constructing agent {agent_id}", exc_info=True)
                raise

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

    def _try_serialize(self, message: Any) -> str:
        try:
            type_name = self._serialization_registry.type_name(message)
            return self._serialization_registry.serialize(
                message, type_name=type_name, data_content_type=JSON_DATA_CONTENT_TYPE
            ).decode("utf-8")
        except ValueError:
            return "Message could not be serialized"
