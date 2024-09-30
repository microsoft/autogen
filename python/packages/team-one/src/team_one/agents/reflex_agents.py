from autogen_core.base import MessageContext, TopicId
from autogen_core.components import RoutedAgent, default_subscription, message_handler
from autogen_core.components.models import UserMessage

from ..messages import BroadcastMessage, RequestReplyMessage


@default_subscription
class ReflexAgent(RoutedAgent):
    def __init__(self, description: str) -> None:
        super().__init__(description)

    @message_handler
    async def handle_incoming_message(self, message: BroadcastMessage, ctx: MessageContext) -> None:
        """Handle an incoming message."""
        pass

    @message_handler
    async def handle_request_reply_message(self, message: RequestReplyMessage, ctx: MessageContext) -> None:
        name = self.metadata["type"]

        response_message = UserMessage(
            content=f"Hello, world from {name}!",
            source=name,
        )
        topic_id = TopicId("default", self.id.key)

        await self.publish_message(BroadcastMessage(content=response_message), topic_id=topic_id)
