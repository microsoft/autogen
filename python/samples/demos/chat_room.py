import argparse
import asyncio
import json
import logging
import os
import sys

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext, AgentProxy, AgentRuntime
from autogen_core.components import DefaultSubscription, DefaultTopicId, RoutedAgent, message_handler
from autogen_core.components.memory import ChatMemory
from autogen_core.components.models import ChatCompletionClient, SystemMessage

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autogen_core.base import MessageContext
from common.memory import BufferedChatMemory
from common.types import Message, TextMessage
from common.utils import convert_messages_to_llm_messages, get_chat_completion_client_from_envs
from utils import TextualChatApp, TextualUserAgent


# Define a custom agent that can handle chat room messages.
class ChatRoomAgent(RoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        background_story: str,
        memory: ChatMemory[Message],
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description)
        system_prompt = f"""Your name is {name}.
Your background story is:
{background_story}

Now you are in a chat room with other users.
You can send messages to the chat room by typing your message below.
You do not need to respond to every message.
Use the following JSON format to provide your thought on the latest message and choose whether to respond:
{{
    "thought": "Your thought on the message",
    "respond": <true/false>,
    "response": "Your response to the message or None if you choose not to respond."
}}
"""
        self._system_messages = [SystemMessage(system_prompt)]
        self._memory = memory
        self._client = model_client

    @message_handler()
    async def on_chat_room_message(self, message: TextMessage, ctx: MessageContext) -> None:
        # Save the message to memory as structured JSON.
        from_message = TextMessage(
            content=json.dumps({"sender": message.source, "content": message.content}), source=message.source
        )
        await self._memory.add_message(from_message)

        # Get a response from the model.
        raw_response = await self._client.create(
            self._system_messages
            + convert_messages_to_llm_messages(await self._memory.get_messages(), self_name=self.metadata["type"]),
            json_output=True,
        )
        assert isinstance(raw_response.content, str)

        # Save the response to memory.
        await self._memory.add_message(TextMessage(source=self.metadata["type"], content=raw_response.content))

        # Parse the response.
        data = json.loads(raw_response.content)
        respond = data.get("respond")
        response = data.get("response")

        # Publish the response if needed.
        if respond is True or str(respond).lower().strip() == "true":
            await self.publish_message(
                TextMessage(source=self.metadata["type"], content=str(response)), topic_id=DefaultTopicId()
            )


class ChatRoomUserAgent(TextualUserAgent):
    """An agent that is used to receive messages from the runtime."""

    @message_handler
    async def on_chat_room_message(self, message: TextMessage, ctx: MessageContext) -> None:
        await self._app.post_runtime_message(message)


# Define a chat room with participants -- the runtime is the chat room.
async def chat_room(runtime: AgentRuntime, app: TextualChatApp) -> None:
    await runtime.register(
        "User",
        lambda: ChatRoomUserAgent(
            description="The user in the chat room.",
            app=app,
        ),
        lambda: [DefaultSubscription()],
    )
    await runtime.register(
        "Alice",
        lambda: ChatRoomAgent(
            name=AgentInstantiationContext.current_agent_id().type,
            description="Alice in the chat room.",
            background_story="Alice is a software engineer who loves to code.",
            memory=BufferedChatMemory(buffer_size=10),
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
        ),
        lambda: [DefaultSubscription()],
    )
    alice = AgentProxy(AgentId("Alice", "default"), runtime)
    await runtime.register(
        "Bob",
        lambda: ChatRoomAgent(
            name=AgentInstantiationContext.current_agent_id().type,
            description="Bob in the chat room.",
            background_story="Bob is a data scientist who loves to analyze data.",
            memory=BufferedChatMemory(buffer_size=10),
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
        ),
        lambda: [DefaultSubscription()],
    )
    bob = AgentProxy(AgentId("Bob", "default"), runtime)
    await runtime.register(
        "Charlie",
        lambda: ChatRoomAgent(
            name=AgentInstantiationContext.current_agent_id().type,
            description="Charlie in the chat room.",
            background_story="Charlie is a designer who loves to create art.",
            memory=BufferedChatMemory(buffer_size=10),
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
        ),
        lambda: [DefaultSubscription()],
    )
    charlie = AgentProxy(AgentId("Charlie", "default"), runtime)
    app.welcoming_notice = f"""Welcome to the chat room demo with the following participants:
1. 👧 {alice.id.type}: {(await alice.metadata)['description']}
2. 👱🏼‍♂️ {bob.id.type}: {(await bob.metadata)['description']}
3. 👨🏾‍🦳 {charlie.id.type}: {(await charlie.metadata)['description']}

Each participant decides on its own whether to respond to the latest message.

You can greet the chat room by typing your first message below.
"""


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    app = TextualChatApp(runtime, user_name="You")
    await chat_room(runtime, app)
    runtime.start()
    await app.run_async()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat room demo with self-driving AI agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("chat_room.log")
        logging.getLogger("autogen_core").addHandler(handler)
    asyncio.run(main())
