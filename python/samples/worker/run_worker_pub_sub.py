import asyncio
import logging
from dataclasses import dataclass
from typing import Any, NoReturn

from agnext.application import WorkerAgentRuntime
from agnext.components import DefaultTopicId, RoutedAgent, message_handler
from agnext.components._type_subscription import TypeSubscription
from agnext.core import MESSAGE_TYPE_REGISTRY, MessageContext, TopicId


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
    runtime = WorkerAgentRuntime()
    MESSAGE_TYPE_REGISTRY.add_type(Greeting)
    MESSAGE_TYPE_REGISTRY.add_type(AskToGreet)
    MESSAGE_TYPE_REGISTRY.add_type(Feedback)
    MESSAGE_TYPE_REGISTRY.add_type(ReturnedGreeting)
    MESSAGE_TYPE_REGISTRY.add_type(ReturnedFeedback)
    await runtime.start(host_connection_string="localhost:50051")

    await runtime.register("receiver", lambda: ReceiveAgent())
    await runtime.add_subscription(TypeSubscription("default", "receiver"))
    await runtime.register("greeter", lambda: GreeterAgent())
    await runtime.add_subscription(TypeSubscription("default", "greeter"))

    await runtime.publish_message(AskToGreet("Hello World!"), topic_id=TopicId("default", "default"))

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
