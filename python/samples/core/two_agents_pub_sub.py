"""
This example shows how to use publish-subscribe to implement a simple
interaction between two agents that use a chat completion model to respond to messages.

1. The main function sends a message to Jack to start the conversation.
2. The Jack agent receives the message, generates a response using a chat completion model,
and publishes the response.
3. The Cathy agent receives the message, generates a response using a chat completion model,
and publishes the response.
4. The conversation continues until a message with termination word is received by any agent.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from agnext.core import CancellationToken

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.utils import get_chat_completion_client_from_envs


@dataclass
class Message:
    source: str
    content: str


class ChatCompletionAgent(TypeRoutedAgent):
    """An agent that uses a chat completion model to respond to messages.
    It keeps a memory of the conversation and uses it to generate responses.
    It publishes a termination message when the termination word is mentioned."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        termination_word: str,
    ) -> None:
        super().__init__(description)
        self._system_messages = system_messages
        self._model_client = model_client
        self._memory: List[Message] = []
        self._termination_word = termination_word

    @message_handler
    async def handle_message(self, message: Message, cancellation_token: CancellationToken) -> None:
        self._memory.append(message)
        if self._termination_word in message.content:
            return
        llm_messages: List[LLMMessage] = []
        for m in self._memory[-10:]:
            if m.source == self.metadata["name"]:
                llm_messages.append(AssistantMessage(content=m.content, source=self.metadata["name"]))
            else:
                llm_messages.append(UserMessage(content=m.content, source=m.source))
        response = await self._model_client.create(self._system_messages + llm_messages)
        assert isinstance(response.content, str)
        await self.publish_message(Message(content=response.content, source=self.metadata["name"]))


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Register the agents.
    jack = await runtime.register_and_get(
        "Jack",
        lambda: ChatCompletionAgent(
            description="Jack a comedian",
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            system_messages=[
                SystemMessage("You are a comedian likes to make jokes. " "When you are done talking, say 'TERMINATE'.")
            ],
            termination_word="TERMINATE",
        ),
    )
    await runtime.register_and_get(
        "Cathy",
        lambda: ChatCompletionAgent(
            description="Cathy a poet",
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            system_messages=[
                SystemMessage("You are a poet likes to write poems. " "When you are done talking, say 'TERMINATE'.")
            ],
            termination_word="TERMINATE",
        ),
    )

    run_context = runtime.start()

    # Send a message to Jack to start the conversation.
    message = Message(content="Can you tell me something fun about SF?", source="User")
    await runtime.send_message(message, jack)

    # Process messages.
    await run_context.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
