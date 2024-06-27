from agnext.components import TypeRoutedAgent, message_handler
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
        name = self.metadata["name"]
        await self.publish_message(
            BroadcastMessage(content=f"Hello, world from {name}!"), cancellation_token=cancellation_token
        )
