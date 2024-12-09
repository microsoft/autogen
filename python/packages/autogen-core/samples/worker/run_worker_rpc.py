import asyncio
import logging
from dataclasses import dataclass

from autogen_core import (
    AgentId,
    DefaultSubscription,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    message_handler,
)
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime


@dataclass
class AskToGreet:
    content: str


@dataclass
class Greeting:
    content: str


@dataclass
class Feedback:
    content: str


class ReceiveAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Receive Agent")

    @message_handler
    async def on_greet(self, message: Greeting, ctx: MessageContext) -> Greeting:
        return Greeting(content=f"Received: {message.content}")

    @message_handler
    async def on_feedback(self, message: Feedback, ctx: MessageContext) -> None:
        print(f"Feedback received: {message.content}")


class GreeterAgent(RoutedAgent):
    def __init__(self, receive_agent_type: str) -> None:
        super().__init__("Greeter Agent")
        self._receive_agent_id = AgentId(receive_agent_type, self.id.key)

    @message_handler
    async def on_ask(self, message: AskToGreet, ctx: MessageContext) -> None:
        response = await self.send_message(Greeting(f"Hello, {message.content}!"), recipient=self._receive_agent_id)
        await self.publish_message(Feedback(f"Feedback: {response.content}"), topic_id=DefaultTopicId())


async def main() -> None:
    runtime = GrpcWorkerAgentRuntime(host_address="localhost:50051")
    runtime.start()

    await ReceiveAgent.register(
        runtime,
        "receiver",
        lambda: ReceiveAgent(),
    )
    await runtime.add_subscription(DefaultSubscription(agent_type="receiver"))
    await GreeterAgent.register(
        runtime,
        "greeter",
        lambda: GreeterAgent("receiver"),
    )
    await runtime.add_subscription(DefaultSubscription(agent_type="greeter"))
    await runtime.publish_message(AskToGreet("Hello World!"), topic_id=DefaultTopicId())

    await runtime.stop_when_signal()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("autogen_core")
    logger.setLevel(logging.DEBUG)
    asyncio.run(main())
