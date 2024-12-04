import asyncio
import logging
from dataclasses import dataclass
from typing import Any, NoReturn

from autogen_core import (
    DefaultSubscription,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    message_handler,
    try_get_known_serializers_for_type,
)
from autogen_core.application import WorkerAgentRuntime


@dataclass
class AskToGreet:
    content: str


@dataclass
class Greeting:
    content: str


@dataclass
class ReturnedGreeting:
    content: str


@dataclass
class Feedback:
    content: str


@dataclass
class ReturnedFeedback:
    content: str


class ReceiveAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Receive Agent")

    @message_handler
    async def on_greet(self, message: Greeting, ctx: MessageContext) -> None:
        await self.publish_message(ReturnedGreeting(f"Returned greeting: {message.content}"), topic_id=DefaultTopicId())

    @message_handler
    async def on_feedback(self, message: Feedback, ctx: MessageContext) -> None:
        await self.publish_message(ReturnedFeedback(f"Returned feedback: {message.content}"), topic_id=DefaultTopicId())

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> NoReturn:  # type: ignore
        print(f"Unhandled message: {message}")


class GreeterAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Greeter Agent")

    @message_handler
    async def on_ask(self, message: AskToGreet, ctx: MessageContext) -> None:
        await self.publish_message(Greeting(f"Hello, {message.content}!"), topic_id=DefaultTopicId())

    @message_handler
    async def on_returned_greet(self, message: ReturnedGreeting, ctx: MessageContext) -> None:
        await self.publish_message(Feedback(f"Feedback: {message.content}"), topic_id=DefaultTopicId())

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> NoReturn:  # type: ignore
        print(f"Unhandled message: {message}")


async def main() -> None:
    runtime = WorkerAgentRuntime(host_address="localhost:50051")
    runtime.start()
    for t in [AskToGreet, Greeting, ReturnedGreeting, Feedback, ReturnedFeedback]:
        runtime.add_message_serializer(try_get_known_serializers_for_type(t))

    await ReceiveAgent.register(runtime, "receiver", ReceiveAgent)
    await runtime.add_subscription(DefaultSubscription(agent_type="receiver"))
    await GreeterAgent.register(runtime, "greeter", GreeterAgent)
    await runtime.add_subscription(DefaultSubscription(agent_type="greeter"))

    await runtime.publish_message(AskToGreet("Hello World!"), topic_id=DefaultTopicId())

    await runtime.stop_when_signal()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("autogen_core")
    logger.setLevel(logging.DEBUG)
    asyncio.run(main())
