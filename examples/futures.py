import asyncio
from dataclasses import dataclass

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentProxy, AgentRuntime, CancellationToken


@dataclass
class MessageType:
    body: str
    sender: str


class Inner(TypeRoutedAgent):  # type: ignore
    def __init__(self, name: str, runtime: AgentRuntime) -> None:  # type: ignore
        super().__init__(name, "The inner agent", runtime)

    @message_handler()  # type: ignore
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:  # type: ignore
        return MessageType(body=f"Inner: {message.body}", sender=self.metadata["name"])


class Outer(TypeRoutedAgent):  # type: ignore
    def __init__(self, name: str, runtime: AgentRuntime, inner: AgentProxy) -> None:  # type: ignore
        super().__init__(name, "The outter agent", runtime)
        self._inner = inner

    @message_handler()  # type: ignore
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:  # type: ignore
        inner_response = self._send_message(message, self._inner.id)
        inner_message = await inner_response
        assert isinstance(inner_message, MessageType)
        return MessageType(body=f"Outer: {inner_message.body}", sender=self.metadata["name"])


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    inner = Inner("inner", runtime)
    outer = Outer("outer", runtime, AgentProxy(inner, runtime))
    response = runtime.send_message(MessageType(body="Hello", sender="external"), outer)

    while not response.done():
        await runtime.process_next()

    print(await response)


if __name__ == "__main__":
    asyncio.run(main())
