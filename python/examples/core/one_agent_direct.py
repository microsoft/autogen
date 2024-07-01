"""
This example shows how to use direct messaging to implement
a simple chat completion agent.
The agent receives a message from the main function, sends it to the
chat completion model, and returns the response to the main function.
"""

import asyncio
import os
import sys
from dataclasses import dataclass

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from agnext.core import CancellationToken

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.utils import get_chat_completion_client_from_envs


@dataclass
class Message:
    content: str


class ChatCompletionAgent(TypeRoutedAgent):
    def __init__(self, description: str, model_client: ChatCompletionClient) -> None:
        super().__init__(description)
        self._system_messages = [SystemMessage("You are a helpful AI assistant.")]
        self._model_client = model_client

    @message_handler
    async def handle_user_message(self, message: Message, cancellation_token: CancellationToken) -> Message:
        user_message = UserMessage(content=message.content, source="User")
        response = await self._model_client.create(self._system_messages + [user_message])
        assert isinstance(response.content, str)
        return Message(content=response.content)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    agent = runtime.register_and_get(
        "chat_agent",
        lambda: ChatCompletionAgent("Chat agent", get_chat_completion_client_from_envs(model="gpt-3.5-turbo")),
    )

    run_context = runtime.start()

    # Send a message to the agent.
    message = Message(content="Can you tell me something fun about SF?")
    result = await runtime.send_message(message, agent)

    # Get the response from the agent.
    response = await result
    assert isinstance(response, Message)
    print(response.content)

    await run_context.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
