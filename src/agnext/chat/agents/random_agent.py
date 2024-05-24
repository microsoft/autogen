import random

from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.chat.types import RespondNow, TextMessage
from agnext.core.cancellation_token import CancellationToken

from ..agents.base import BaseChatAgent


class RandomResponseAgent(BaseChatAgent, TypeRoutedAgent):
    # TODO: use require_response
    @message_handler(RespondNow)
    async def on_chat_message_with_cancellation(
        self, message: RespondNow, require_response: bool, cancellation_token: CancellationToken
    ) -> TextMessage:
        # Generate a random response.
        response_body = random.choice(
            [
                "Hello!",
                "Hi!",
                "Hey!",
                "How are you?",
                "What's up?",
                "Good day!",
                "Good morning!",
                "Good evening!",
                "Good afternoon!",
                "Good night!",
                "Good bye!",
                "Bye!",
                "See you later!",
                "See you soon!",
                "See you!",
            ]
        )
        return TextMessage(content=response_body, source=self.name)
