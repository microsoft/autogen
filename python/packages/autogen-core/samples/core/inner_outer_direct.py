"""
This example shows how to use direct messaging to implement
a simple interaction between an inner and an outer agent.
1. The outer agent receives a message, sends a message to the inner agent.
2. The inner agent receives the message, processes it, and sends a response to the outer agent.
3. The outer agent receives the response and processes it, and returns the final response.
"""

import asyncio
import logging
from dataclasses import dataclass

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext, MessageContext
from autogen_core.components import RoutedAgent, message_handler


@dataclass
class MessageType:
    body: str
    sender: str


class Inner(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("The inner agent")

    @message_handler()
    async def on_new_message(self, message: MessageType, ctx: MessageContext) -> MessageType:
        return MessageType(body=f"Inner: {message.body}", sender=self.metadata["type"])


class Outer(RoutedAgent):
    def __init__(self, inner: AgentId) -> None:
        super().__init__("The outer agent")
        self._inner = inner

    @message_handler()
    async def on_new_message(self, message: MessageType, ctx: MessageContext) -> MessageType:
        inner_response = self.send_message(message, self._inner)
        inner_message = await inner_response
        assert isinstance(inner_message, MessageType)
        return MessageType(body=f"Outer: {inner_message.body}", sender=self.metadata["type"])


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register("inner", Inner)
    await runtime.register("outer", lambda: Outer(AgentId("inner", AgentInstantiationContext.current_agent_id().key)))
    outer = AgentId("outer", "default")

    runtime.start()

    response = await runtime.send_message(MessageType(body="Hello", sender="external"), outer)
    print(response)
    await runtime.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
