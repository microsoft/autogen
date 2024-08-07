from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import UserMessage
from agnext.core import CancellationToken

from ..messages import BroadcastMessage, RequestReplyMessage


class ReflexAgent(TypeRoutedAgent):
    def __init__(self, description: str) -> None:
        super().__init__(description)

    @message_handler
    async def handle_incoming_message(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming message."""
        pass

    @message_handler
    async def handle_request_reply_message(
        self, message: RequestReplyMessage, cancellation_token: CancellationToken
    ) -> None:
        name = self.metadata["type"]

        response_message = UserMessage(
            content=f"Hello, world from {name}!",
            source=name,
        )

        await self.publish_message(BroadcastMessage(response_message), cancellation_token=cancellation_token)
