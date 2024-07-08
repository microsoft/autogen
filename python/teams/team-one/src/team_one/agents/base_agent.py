from typing import List, Tuple, Union

from agnext.components import Image, TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    LLMMessage,
    UserMessage,
)
from agnext.core import CancellationToken

from team_one.messages import BroadcastMessage, RequestReplyMessage

# Convenience type
UserContent = Union[str, List[Union[str, Image]]]


class BaseAgent(TypeRoutedAgent):
    """An agent that handles the RequestReply and Broadcast messages"""

    def __init__(
        self,
        description: str,
    ) -> None:
        super().__init__(description)
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_broadcast(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming broadcast message."""
        assert isinstance(message.content, UserMessage)
        self._chat_history.append(message.content)

    @message_handler
    async def handle_request_reply(self, message: RequestReplyMessage, cancellation_token: CancellationToken) -> None:
        """Respond to a reply request."""
        request_halt, response = await self._generate_reply(cancellation_token)

        # Convert the response to an acceptable format for the assistant
        if isinstance(response, str):
            assistant_message = AssistantMessage(content=response, source=self.metadata["name"])
        elif isinstance(response, List):
            converted: List[str] = list()
            for item in response:
                if isinstance(item, str):
                    converted.append(item.rstrip())
                elif isinstance(item, Image):
                    converted.append("<image>")
                else:
                    raise AssertionError("Unexpected response type.")
            assistant_message = AssistantMessage(content="\n".join(converted), source=self.metadata["name"])
        else:
            raise AssertionError("Unexpected response type.")
        self._chat_history.append(assistant_message)

        user_message = UserMessage(content=response, source=self.metadata["name"])
        await self.publish_message(BroadcastMessage(content=user_message, request_halt=request_halt))

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Returns (request_halt, response_message)"""
        raise NotImplementedError()
