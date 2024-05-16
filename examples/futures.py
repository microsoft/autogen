import asyncio
from dataclasses import dataclass

from agnext.core.agent import Agent
from agnext.core.agent_runtime import AgentRuntime
from agnext.core.message import Message
from agnext.single_threaded_agent_runtime import SingleThreadedAgentRuntime
from agnext.type_routed_agent import TypeRoutedAgent, event_handler


@dataclass
class MessageType(Message):
    message: str
    sender: str


class Inner(TypeRoutedAgent[MessageType]):
    def __init__(self, name: str, router: AgentRuntime[MessageType]) -> None:
        super().__init__(name, router)

    @event_handler(MessageType)
    async def on_new_event(self, event: MessageType) -> MessageType:
        return MessageType(message=f"Inner: {event.message}", sender=self.name)


class Outer(TypeRoutedAgent[MessageType]):
    def __init__(self, name: str, router: AgentRuntime[MessageType], inner: Agent[MessageType]) -> None:
        super().__init__(name, router)
        self._inner = inner

    @event_handler(MessageType)
    async def on_new_event(self, event: MessageType) -> MessageType:
        inner_response = self._send_message(event, self._inner)
        inner_message = await inner_response
        return MessageType(message=f"Outer: {inner_message.message}", sender=self.name)


async def main() -> None:
    router = SingleThreadedAgentRuntime[MessageType]()

    inner = Inner("inner", router)
    outer = Outer("outer", router, inner)
    response = router.send_message(MessageType(message="Hello", sender="external"), outer)

    while not response.done():
        await router.process_next()

    print(await response)


if __name__ == "__main__":
    asyncio.run(main())
