import asyncio
from asyncio import Future
from dataclasses import dataclass
from typing import Awaitable, Dict, Generic, List, Set, Type, TypeVar, cast

from agnext.core.cancellation_token import CancellationToken
from agnext.core.exceptions import MessageDroppedException
from agnext.core.intervention import DropMessage, InterventionHandler

from ..core.agent import Agent
from ..core.agent_runtime import AgentRuntime

T = TypeVar("T")


@dataclass(kw_only=True)
class BroadcastMessageEnvelope(Generic[T]):
    """A message envelope for broadcasting messages to all agents that can handle
    the message of the type T."""

    message: T
    future: Future[List[T]]
    cancellation_token: CancellationToken
    sender: Agent[T] | None


@dataclass(kw_only=True)
class SendMessageEnvelope(Generic[T]):
    """A message envelope for sending a message to a specific agent that can handle
    the message of the type T."""

    message: T
    sender: Agent[T] | None
    recipient: Agent[T]
    future: Future[T]
    cancellation_token: CancellationToken


@dataclass(kw_only=True)
class ResponseMessageEnvelope(Generic[T]):
    """A message envelope for sending a response to a message."""

    message: T
    future: Future[T]
    sender: Agent[T]
    recipient: Agent[T] | None


@dataclass(kw_only=True)
class BroadcastResponseMessageEnvelope(Generic[T]):
    """A message envelope for sending a response to a message."""

    message: List[T]
    future: Future[List[T]]
    recipient: Agent[T] | None


class SingleThreadedAgentRuntime(AgentRuntime[T]):
    def __init__(self, *, before_send: InterventionHandler[T] | None = None) -> None:
        self._message_queue: List[
            BroadcastMessageEnvelope[T]
            | SendMessageEnvelope[T]
            | ResponseMessageEnvelope[T]
            | BroadcastResponseMessageEnvelope[T]
        ] = []
        self._per_type_subscribers: Dict[Type[T], List[Agent[T]]] = {}
        self._agents: Set[Agent[T]] = set()
        self._before_send = before_send

    def add_agent(self, agent: Agent[T]) -> None:
        for message_type in agent.subscriptions:
            if message_type not in self._per_type_subscribers:
                self._per_type_subscribers[message_type] = []
            self._per_type_subscribers[message_type].append(agent)
        self._agents.add(agent)

    # Returns the response of the message
    def send_message(
        self,
        message: T,
        recipient: Agent[T],
        *,
        sender: Agent[T] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[T]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        loop = asyncio.get_event_loop()
        future: Future[T] = loop.create_future()

        self._message_queue.append(
            SendMessageEnvelope(
                message=message,
                recipient=recipient,
                future=future,
                cancellation_token=cancellation_token,
                sender=sender,
            )
        )

        return future

    # Returns the response of all handling agents
    def broadcast_message(
        self, message: T, *, sender: Agent[T] | None = None, cancellation_token: CancellationToken | None = None
    ) -> Future[List[T]]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future: Future[List[T]] = asyncio.get_event_loop().create_future()
        self._message_queue.append(
            BroadcastMessageEnvelope(
                message=message, future=future, cancellation_token=cancellation_token, sender=sender
            )
        )
        return future

    async def _process_send(self, message_envelope: SendMessageEnvelope[T]) -> None:
        recipient = message_envelope.recipient
        if recipient not in self._agents:
            message_envelope.future.set_exception(Exception("Recipient not found"))
            return

        try:
            response = await recipient.on_message(
                message_envelope.message, cancellation_token=message_envelope.cancellation_token
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

    async def _process_broadcast(self, message_envelope: BroadcastMessageEnvelope[T]) -> None:
        responses: List[Awaitable[T]] = []
        for agent in self._per_type_subscribers.get(type(message_envelope.message), []):
            future = agent.on_message(message_envelope.message, cancellation_token=message_envelope.cancellation_token)
            responses.append(future)

        try:
            all_responses = await asyncio.gather(*responses)
        except BaseException as e:
            message_envelope.future.set_exception(e)
            return

        self._message_queue.append(
            BroadcastResponseMessageEnvelope(
                message=all_responses, future=message_envelope.future, recipient=message_envelope.sender
            )
        )

    async def _process_response(self, message_envelope: ResponseMessageEnvelope[T]) -> None:
        message_envelope.future.set_result(message_envelope.message)

    async def _process_broadcast_response(self, message_envelope: BroadcastResponseMessageEnvelope[T]) -> None:
        message_envelope.future.set_result(message_envelope.message)

    async def process_next(self) -> None:
        if len(self._message_queue) == 0:
            # Yield control to the event loop to allow other tasks to run
            await asyncio.sleep(0)
            return

        message_envelope = self._message_queue.pop(0)

        match message_envelope:
            case SendMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._before_send is not None:
                    temp_message = await self._before_send.on_send(message, sender=sender, recipient=recipient)
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = cast(T, temp_message)

                asyncio.create_task(self._process_send(message_envelope))
            case BroadcastMessageEnvelope(
                message=message,
                sender=sender,
                future=future,
            ):
                if self._before_send is not None:
                    temp_message = await self._before_send.on_broadcast(message, sender=sender)
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = cast(T, temp_message)

                asyncio.create_task(self._process_broadcast(message_envelope))
            case ResponseMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._before_send is not None:
                    temp_message = await self._before_send.on_response(message, sender=sender, recipient=recipient)
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = cast(T, temp_message)

                asyncio.create_task(self._process_response(message_envelope))

            case BroadcastResponseMessageEnvelope(message=message, recipient=recipient, future=future):
                if self._before_send is not None:
                    temp_message_list = await self._before_send.on_broadcast_response(message, recipient=recipient)
                    if temp_message_list is DropMessage or isinstance(temp_message_list, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = list(temp_message_list)  # type: ignore

                asyncio.create_task(self._process_broadcast_response(message_envelope))

        # Yield control to the message loop to allow other tasks to run
        await asyncio.sleep(0)
