import argparse
import asyncio
import logging
from dataclasses import dataclass

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentId, CancellationToken


@dataclass
class MessageType:
    body: str
    sender: str


class Inner(TypeRoutedAgent):  # type: ignore
    def __init__(self) -> None:  # type: ignore
        super().__init__("The inner agent")

    @message_handler()  # type: ignore
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:  # type: ignore
        return MessageType(body=f"Inner: {message.body}", sender=self.metadata["name"])


class Outer(TypeRoutedAgent):  # type: ignore
    def __init__(self, inner: AgentId) -> None:  # type: ignore
        super().__init__("The outer agent")
        self._inner = inner

    @message_handler()  # type: ignore
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:  # type: ignore
        inner_response = self._send_message(message, self._inner)
        inner_message = await inner_response
        assert isinstance(inner_message, MessageType)
        return MessageType(body=f"Outer: {inner_message.body}", sender=self.metadata["name"])


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    inner = runtime.register_and_get("inner", Inner)
    outer = runtime.register_and_get("outer", lambda: Outer(inner))
    response = runtime.send_message(MessageType(body="Hello", sender="external"), outer)

    while not response.done():
        await runtime.process_next()

    print(await response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inner-Outter agent example.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)
        handler = logging.FileHandler("inner_outter.log")
        logging.getLogger("agnext").addHandler(handler)
    asyncio.run(main())
