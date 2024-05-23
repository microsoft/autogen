import random

from ..agents.base import BaseChatAgent
from ..messages import ChatMessage


class RandomResponseAgent(BaseChatAgent):
    async def on_chat_message(self, message: ChatMessage) -> ChatMessage:
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
