import asyncio
from asyncio import Future
from dataclasses import dataclass
from typing import Dict, Generic, List, Set, Type, TypeVar

from ..core.agent import Agent
from ..core.agent_runtime import AgentRuntime
from ..core.message import Message

T = TypeVar("T", bound=Message)


@dataclass
class BroadcastMessage(Generic[T]):
    message: T
    future: Future[List[T]]


@dataclass
class SendMessage(Generic[T]):
    message: T
    destination: Agent[T]
    future: Future[T]


@dataclass
class ResponseMessage(Generic[T]): ...


class SingleThreadedAgentRuntime(AgentRuntime[T]):
    def __init__(self) -> None:
        self._event_queue: List[BroadcastMessage[T] | SendMessage[T]] = []
        self._per_type_subscribers: Dict[Type[T], List[Agent[T]]] = {}
        self._agents: Set[Agent[T]] = set()

    def add_agent(self, agent: Agent[T]) -> None:
        for event_type in agent.subscriptions:
            if event_type not in self._per_type_subscribers:
                self._per_type_subscribers[event_type] = []
            self._per_type_subscribers[event_type].append(agent)
        self._agents.add(agent)

    # Returns the response of the message
    def send_message(self, message: T, destination: Agent[T]) -> Future[T]:
        loop = asyncio.get_event_loop()
        future: Future[T] = loop.create_future()

        self._event_queue.append(SendMessage(message, destination, future))

        return future

    # Returns the response of all handling agents
    def broadcast_message(self, message: T) -> Future[List[T]]:
        future: Future[List[T]] = asyncio.get_event_loop().create_future()
        self._event_queue.append(BroadcastMessage(message, future))
        return future

    async def _process_send(self, message: SendMessage[T]) -> None:
        recipient = message.destination
        if recipient not in self._agents:
            message.future.set_exception(Exception("Recipient not found"))
            return

        response = await recipient.on_event(message.message)
        message.future.set_result(response)

    async def _process_broadcast(self, message: BroadcastMessage[T]) -> None:
        responses: List[T] = []
        for agent in self._per_type_subscribers.get(type(message.message), []):
            response = await agent.on_event(message.message)
            responses.append(response)
        message.future.set_result(responses)

    async def process_next(self) -> None:
        if len(self._event_queue) == 0:
            # Yield control to the event loop to allow other tasks to run
            await asyncio.sleep(0)
            return

        event = self._event_queue.pop(0)

        match event:
            case SendMessage(message, destination, future):
                asyncio.create_task(self._process_send(SendMessage(message, destination, future)))
            case BroadcastMessage(message, future):
                asyncio.create_task(self._process_broadcast(BroadcastMessage(message, future)))

        # Yield control to the event loop to allow other tasks to run
        await asyncio.sleep(0)
