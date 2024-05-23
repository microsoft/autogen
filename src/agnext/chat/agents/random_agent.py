import random

from agnext.agent_components.type_routed_agent import message_handler
from agnext.core.cancellation_token import CancellationToken

from ..agents.base import BaseChatAgent
from ..messages import ChatMessage


class RandomResponseAgent(BaseChatAgent):
    # TODO: use require_response
    @message_handler(ChatMessage)
    async def on_chat_message_with_cancellation(
        self, message: ChatMessage, require_response: bool, cancellation_token: CancellationToken
    ) -> ChatMessage | None:
        print(f"{self.name} received message from {message.sender}: {message.body}")
        if message.save_message_only:
            return ChatMessage(body="OK", sender=self.name)
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
        return ChatMessage(body=response_body, sender=self.name)
