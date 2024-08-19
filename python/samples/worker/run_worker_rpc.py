import asyncio
import logging
from dataclasses import dataclass

from agnext.application import WorkerAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import MESSAGE_TYPE_REGISTRY, AgentId, MessageContext


@dataclass
class AskToGreet:
    content: str


@dataclass
class Greeting:
    content: str


@dataclass
class Feedback:
    content: str


class ReceiveAgent(TypeRoutedAgent):
    def __init__(self) -> None:
        super().__init__("Receive Agent")

    @message_handler
    async def on_greet(self, message: Greeting, ctx: MessageContext) -> Greeting:
        return Greeting(content=f"Received: {message.content}")

    @message_handler
    async def on_feedback(self, message: Feedback, ctx: MessageContext) -> None:
        print(f"Feedback received: {message.content}")


class GreeterAgent(TypeRoutedAgent):
    def __init__(self, receive_agent_id: AgentId) -> None:
        super().__init__("Greeter Agent")
        self._receive_agent_id = receive_agent_id

    @message_handler
    async def on_ask(self, message: AskToGreet, ctx: MessageContext) -> None:
        response = await self.send_message(Greeting(f"Hello, {message.content}!"), recipient=self._receive_agent_id)
        await self.publish_message(Feedback(f"Feedback: {response.content}"))


async def main() -> None:
    runtime = WorkerAgentRuntime()
    MESSAGE_TYPE_REGISTRY.add_type(Greeting)
    MESSAGE_TYPE_REGISTRY.add_type(AskToGreet)
    MESSAGE_TYPE_REGISTRY.add_type(Feedback)
    await runtime.start(host_connection_string="localhost:50051")

    await runtime.register("reciever", lambda: ReceiveAgent())
    reciever = await runtime.get("reciever")
    await runtime.register("greeter", lambda: GreeterAgent(reciever))

    await runtime.publish_message(AskToGreet("Hello World!"), namespace="default")

    # Just to keep the runtime running
    try:
        await asyncio.sleep(1000000)
    except KeyboardInterrupt:
        pass
    await runtime.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("agnext")
    logger.setLevel(logging.DEBUG)
    asyncio.run(main())
