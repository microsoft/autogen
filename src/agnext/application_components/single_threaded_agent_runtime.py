import asyncio
from asyncio import Future
from dataclasses import dataclass
from typing import Any, Awaitable, Dict, List, Sequence, Set, cast

from agnext.core.cancellation_token import CancellationToken
from agnext.core.exceptions import MessageDroppedException
from agnext.core.intervention import DropMessage, InterventionHandler

from ..core.agent import Agent
from ..core.agent_runtime import AgentRuntime


@dataclass(kw_only=True)
class BroadcastMessageEnvelope:
    """A message envelope for broadcasting messages to all agents that can handle
    the message of the type T."""

    message: Any
    future: Future[Sequence[Any] | None]
    cancellation_token: CancellationToken
    sender: Agent | None
    require_response: bool


@dataclass(kw_only=True)
class SendMessageEnvelope:
    """A message envelope for sending a message to a specific agent that can handle
    the message of the type T."""

    message: Any
    sender: Agent | None
    recipient: Agent
    future: Future[Any | None]
    cancellation_token: CancellationToken
    require_response: bool


@dataclass(kw_only=True)
class ResponseMessageEnvelope:
    """A message envelope for sending a response to a message."""

    message: Any
    future: Future[Any]
    sender: Agent
    recipient: Agent | None


@dataclass(kw_only=True)
class BroadcastResponseMessageEnvelope:
    """A message envelope for sending a response to a message."""

    message: Sequence[Any]
    future: Future[Sequence[Any]]
    recipient: Agent | None


class SingleThreadedAgentRuntime(AgentRuntime):
    def __init__(self, *, before_send: InterventionHandler | None = None) -> None:
        self._message_queue: List[
            BroadcastMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope | BroadcastResponseMessageEnvelope
        ] = []
        self._per_type_subscribers: Dict[type, List[Agent]] = {}
        self._agents: Set[Agent] = set()
        self._before_send = before_send

    def add_agent(self, agent: Agent) -> None:
        for message_type in agent.subscriptions:
            if message_type not in self._per_type_subscribers:
                self._per_type_subscribers[message_type] = []
            self._per_type_subscribers[message_type].append(agent)
        self._agents.add(agent)

    # Returns the response of the message
    def send_message(
        self,
        message: Any,
        recipient: Agent,
        *,
        require_response: bool = True,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any | None]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future = asyncio.get_event_loop().create_future()
        if recipient not in self._agents:
            future.set_exception(Exception("Recipient not found"))

        self._message_queue.append(
            SendMessageEnvelope(
                message=message,
                recipient=recipient,
                future=future,
                cancellation_token=cancellation_token,
                sender=sender,
                require_response=require_response,
            )
        )

        return future

    # send message, require_response=False -> returns after delivery, gives None
    # send message, require_response=True -> returns after handling, gives Response
    def broadcast_message(
        self,
        message: Any,
        *,
        require_response: bool = True,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Sequence[Any] | None]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future = asyncio.get_event_loop().create_future()
        self._message_queue.append(
            BroadcastMessageEnvelope(
                message=message,
                future=future,
                cancellation_token=cancellation_token,
                sender=sender,
                require_response=require_response,
            )
        )

        return future

    async def _process_send(self, message_envelope: SendMessageEnvelope) -> None:
        recipient = message_envelope.recipient
        assert recipient in self._agents

        try:
            response = await recipient.on_message(
                message_envelope.message,
                require_response=message_envelope.require_response,
                cancellation_token=message_envelope.cancellation_token,
            )
        except BaseException as e:
            message_envelope.future.set_exception(e)
            return

        if not message_envelope.require_response and response is not None:
            raise Exception("Recipient returned a response for a message that did not request a response")

        if message_envelope.require_response and response is None:
            raise Exception("Recipient did not return a response for a message that requested a response")

        if message_envelope.require_response:
            self._message_queue.append(
                ResponseMessageEnvelope(
                    message=response,
                    future=message_envelope.future,
                    sender=message_envelope.recipient,
                    recipient=message_envelope.sender,
                )
            )
        else:
            message_envelope.future.set_result(None)

    async def _process_broadcast(self, message_envelope: BroadcastMessageEnvelope) -> None:
        responses: List[Awaitable[Any]] = []
        for agent in self._per_type_subscribers.get(type(message_envelope.message), []):  # type: ignore
            future = agent.on_message(
                message_envelope.message,
                require_response=message_envelope.require_response,
                cancellation_token=message_envelope.cancellation_token,
            )
            responses.append(future)

        try:
            all_responses = await asyncio.gather(*responses)
        except BaseException as e:
            message_envelope.future.set_exception(e)
            return

        if message_envelope.require_response:
            self._message_queue.append(
                BroadcastResponseMessageEnvelope(
                    message=all_responses,
                    future=cast(Future[Sequence[Any]], message_envelope.future),
                    recipient=message_envelope.sender,
                )
            )
        else:
            message_envelope.future.set_result(None)

    async def _process_response(self, message_envelope: ResponseMessageEnvelope) -> None:
        message_envelope.future.set_result(message_envelope.message)

    async def _process_broadcast_response(self, message_envelope: BroadcastResponseMessageEnvelope) -> None:
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

                    message_envelope.message = temp_message

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

                    message_envelope.message = temp_message

                asyncio.create_task(self._process_broadcast(message_envelope))
            case ResponseMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._before_send is not None:
                    temp_message = await self._before_send.on_response(message, sender=sender, recipient=recipient)
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = temp_message

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
