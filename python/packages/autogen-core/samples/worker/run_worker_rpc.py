import asyncio
import logging
from dataclasses import dataclass
from typing import Any, NoReturn

from autogen_core.application import WorkerAgentRuntime
from autogen_core.base import (
    AgentId,
    AgentInstantiationContext,
    MessageContext,
)
from autogen_core.components import DefaultSubscription, DefaultTopicId, RoutedAgent, message_handler


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

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> NoReturn:  # type: ignore
        print(f"Unhandled message: {message}")


class GreeterAgent(RoutedAgent):
    def __init__(self, receive_agent_id: AgentId) -> None:
        super().__init__("Greeter Agent")
        self._receive_agent_id = receive_agent_id

    @message_handler
    async def on_ask(self, message: AskToGreet, ctx: MessageContext) -> None:
        response = await self.send_message(Greeting(f"Hello, {message.content}!"), recipient=self._receive_agent_id)
        await self.publish_message(Feedback(f"Feedback: {response.content}"), topic_id=DefaultTopicId())

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> NoReturn:  # type: ignore
        print(f"Unhandled message: {message}")


async def main() -> None:
    runtime = WorkerAgentRuntime(host_address="localhost:50051")
    runtime.start()

    await runtime.register("receiver", lambda: ReceiveAgent(), lambda: [DefaultSubscription()])
    await runtime.register(
        "greeter",
        lambda: GreeterAgent(AgentId("receiver", AgentInstantiationContext.current_agent_id().key)),
        lambda: [DefaultSubscription()],
    )
    await runtime.publish_message(AskToGreet("Hello World!"), topic_id=DefaultTopicId())

    await runtime.stop_when_signal()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("autogen_core")
    logger.setLevel(logging.DEBUG)
    asyncio.run(main())
