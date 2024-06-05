import asyncio
from dataclasses import dataclass

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.core import Agent, AgentRuntime, CancellationToken


@dataclass
class MessageType:
    body: str
    sender: str


class Inner(TypeRoutedAgent):
    def __init__(self, name: str, router: AgentRuntime) -> None:
        super().__init__(name, router)

    @message_handler()
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        return MessageType(body=f"Inner: {message.body}", sender=self.name)


class Outer(TypeRoutedAgent):
    def __init__(self, name: str, router: AgentRuntime, inner: Agent) -> None:
        super().__init__(name, router)
        self._inner = inner

    @message_handler()
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        inner_response = self._send_message(message, self._inner)
        inner_message = await inner_response
        assert isinstance(inner_message, MessageType)
        return MessageType(body=f"Outer: {inner_message.body}", sender=self.name)


async def main() -> None:
    router = SingleThreadedAgentRuntime()
    inner = Inner("inner", router)
    outer = Outer("outer", router, inner)
    response = router.send_message(MessageType(body="Hello", sender="external"), outer)

    while not response.done():
        await router.process_next()

    print(await response)


if __name__ == "__main__":
    asyncio.run(main())
