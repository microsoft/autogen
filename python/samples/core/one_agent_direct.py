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
from agnext.core import AgentId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agnext.core import MessageContext
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
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        user_message = UserMessage(content=message.content, source="User")
        response = await self._model_client.create(self._system_messages + [user_message])
        assert isinstance(response.content, str)
        return Message(content=response.content)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register(
        "chat_agent",
        lambda: ChatCompletionAgent("Chat agent", get_chat_completion_client_from_envs(model="gpt-4o-mini")),
    )
    agent = AgentId("chat_agent", "default")

    runtime.start()

    # Send a message to the agent and get the response.
    message = Message(content="Hello, what are some fun things to do in Seattle?")
    response = await runtime.send_message(message, agent)
    assert isinstance(response, Message)
    print(response.content)

    await runtime.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
