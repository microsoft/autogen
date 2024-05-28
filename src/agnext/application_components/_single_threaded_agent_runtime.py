import asyncio
from asyncio import Future
from dataclasses import dataclass
from typing import Any, Awaitable, Dict, List, Mapping, Set

from ..core import Agent, AgentRuntime, CancellationToken
from ..core.exceptions import MessageDroppedException
from ..core.intervention import DropMessage, InterventionHandler


@dataclass(kw_only=True)
class PublishMessageEnvelope:
    """A message envelope for publishing messages to all agents that can handle
    the message of the type T."""

    message: Any
    cancellation_token: CancellationToken
    sender: Agent | None


@dataclass(kw_only=True)
class SendMessageEnvelope:
    """A message envelope for sending a message to a specific agent that can handle
    the message of the type T."""

    message: Any
    sender: Agent | None
    recipient: Agent
    future: Future[Any]
    cancellation_token: CancellationToken


@dataclass(kw_only=True)
class ResponseMessageEnvelope:
    """A message envelope for sending a response to a message."""

    message: Any
    future: Future[Any]
    sender: Agent
    recipient: Agent | None


class SingleThreadedAgentRuntime(AgentRuntime):
    def __init__(self, *, before_send: InterventionHandler | None = None) -> None:
        self._message_queue: List[PublishMessageEnvelope | SendMessageEnvelope | ResponseMessageEnvelope] = []
        self._per_type_subscribers: Dict[type, List[Agent]] = {}
        self._agents: Set[Agent] = set()
        self._before_send = before_send

    def add_agent(self, agent: Agent) -> None:
        agent_names = {agent.name for agent in self._agents}
        if agent.name in agent_names:
            raise ValueError(f"Agent with name {agent.name} already exists. Agent names must be unique.")

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
            )
        )

        return future

    def publish_message(
        self,
        message: Any,
        *,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[None]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        self._message_queue.append(
            PublishMessageEnvelope(
                message=message,
                cancellation_token=cancellation_token,
                sender=sender,
            )
        )

        future = asyncio.get_event_loop().create_future()
        future.set_result(None)
        return future

    def save_state(self) -> Mapping[str, Any]:
        state: Dict[str, Dict[str, Any]] = {}
        for agent in self._agents:
            state[agent.name] = dict(agent.save_state())
        return state

    def load_state(self, state: Mapping[str, Any]) -> None:
        for agent in self._agents:
            agent.load_state(state[agent.name])

    async def _process_send(self, message_envelope: SendMessageEnvelope) -> None:
        recipient = message_envelope.recipient
        assert recipient in self._agents

        try:
            response = await recipient.on_message(
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

    async def _process_publish(self, message_envelope: PublishMessageEnvelope) -> None:
        responses: List[Awaitable[Any]] = []
        for agent in self._per_type_subscribers.get(type(message_envelope.message), []):  # type: ignore
            future = agent.on_message(
                message_envelope.message,
                cancellation_token=message_envelope.cancellation_token,
            )
            responses.append(future)

        try:
            _all_responses = await asyncio.gather(*responses)
        except BaseException:
            # TODO log error
            return

        # TODO if responses are given for a publish

    async def _process_response(self, message_envelope: ResponseMessageEnvelope) -> None:
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
            case PublishMessageEnvelope(
                message=message,
                sender=sender,
            ):
                if self._before_send is not None:
                    temp_message = await self._before_send.on_publish(message, sender=sender)
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        # TODO log message dropped
                        return

                    message_envelope.message = temp_message

                asyncio.create_task(self._process_publish(message_envelope))
            case ResponseMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
                if self._before_send is not None:
                    temp_message = await self._before_send.on_response(message, sender=sender, recipient=recipient)
                    if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                        future.set_exception(MessageDroppedException())
                        return

                    message_envelope.message = temp_message

                asyncio.create_task(self._process_response(message_envelope))

        # Yield control to the message loop to allow other tasks to run
        await asyncio.sleep(0)
