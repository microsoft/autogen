import asyncio

from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import UserMessage
from agnext.core import CancellationToken

from team_one.messages import BroadcastMessage, RequestReplyMessage


class UserProxy(TypeRoutedAgent):
    """An agent that allows the user to play the role of an agent in the conversation."""

    DEFAULT_DESCRIPTION = "A human user."

    def __init__(
        self,
        description: str = DEFAULT_DESCRIPTION,
    ) -> None:
        super().__init__(description)

    @message_handler
    async def handle_broadcast(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming broadcast message."""
        pass

    @message_handler
    async def handle_request_reply(self, message: RequestReplyMessage, cancellation_token: CancellationToken) -> None:
        """Respond to a reply request."""

        # Make an inference to the model.
        response = await self.ainput("User input ('exit' to quit): ")

        response = response.strip()

        await self.publish_message(
            BroadcastMessage(
                content=UserMessage(content=response, source=self.metadata["name"]), request_halt=(response == "exit")
            )
        )

    async def ainput(self, prompt: str) -> str:
        return await asyncio.to_thread(input, f"{prompt} ")
