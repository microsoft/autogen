import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.memory import BufferedChatMemory, ChatMemory
from agnext.chat.types import TextMessage
from agnext.chat.utils import convert_messages_to_llm_messages
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import ChatCompletionClient, OpenAI, SystemMessage
from agnext.core import AgentRuntime, CancellationToken
from utils import TextualChatApp, TextualUserAgent, start_runtime


# Define a custom agent that can handle chat room messages.
class ChatRoomAgent(TypeRoutedAgent):  # type: ignore
    def __init__(  # type: ignore
        self,
        name: str,
        description: str,
        background_story: str,
        memory: ChatMemory,  # type: ignore
        model_client: ChatCompletionClient,  # type: ignore
    ) -> None:  # type: ignore
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

    @message_handler()  # type: ignore
    async def on_chat_room_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        # Save the message to memory as structured JSON.
        from_message = TextMessage(
            content=json.dumps({"sender": message.source, "content": message.content}), source=message.source
        )
        await self._memory.add_message(from_message)

        # Get a response from the model.
        raw_response = await self._client.create(
            self._system_messages
            + convert_messages_to_llm_messages(await self._memory.get_messages(), self_name=self.metadata["name"]),
            json_output=True,
        )
        assert isinstance(raw_response.content, str)

        # Save the response to memory.
        await self._memory.add_message(TextMessage(source=self.metadata["name"], content=raw_response.content))

        # Parse the response.
        data = json.loads(raw_response.content)
        respond = data.get("respond")
        response = data.get("response")

        # Publish the response if needed.
        if respond is True or str(respond).lower().strip() == "true":
            await self._publish_message(TextMessage(source=self.metadata["name"], content=str(response)))


class ChatRoomUserAgent(TextualUserAgent):  # type: ignore
    """An agent that is used to receive messages from the runtime."""

    @message_handler  # type: ignore
    async def on_chat_room_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        await self._app.post_runtime_message(message)


# Define a chat room with participants -- the runtime is the chat room.
def chat_room(runtime: AgentRuntime, app: TextualChatApp) -> None:  # type: ignore
    runtime.register(
        "User",
        lambda: ChatRoomUserAgent(
            description="The user in the chat room.",
            app=app,
        ),
    )
    alice = runtime.register_and_get_proxy(
        "Alice",
        lambda rt, id: ChatRoomAgent(
            name=id.name,
            description="Alice in the chat room.",
            background_story="Alice is a software engineer who loves to code.",
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAI(model="gpt-4-turbo"),  # type: ignore
        ),
    )
    bob = runtime.register_and_get_proxy(
        "Bob",
        lambda rt, id: ChatRoomAgent(
            name=id.name,
            description="Bob in the chat room.",
            background_story="Bob is a data scientist who loves to analyze data.",
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAI(model="gpt-4-turbo"),  # type: ignore
        ),
    )
    charlie = runtime.register_and_get_proxy(
        "Charlie",
        lambda rt, id: ChatRoomAgent(
            name=id.name,
            description="Charlie in the chat room.",
            background_story="Charlie is a designer who loves to create art.",
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAI(model="gpt-4-turbo"),  # type: ignore
        ),
    )
    app.welcoming_notice = f"""Welcome to the chat room demo with the following participants:
1. 👧 {alice.id.name}: {alice.metadata['description']}
2. 👱🏼‍♂️ {bob.id.name}: {bob.metadata['description']}
3. 👨🏾‍🦳 {charlie.id.name}: {charlie.metadata['description']}

Each participant decides on its own whether to respond to the latest message.

You can greet the chat room by typing your first message below.
"""


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    app = TextualChatApp(runtime, user_name="You")
    chat_room(runtime, app)
    asyncio.create_task(start_runtime(runtime))
    await app.run_async()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat room demo with self-driving AI agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)
        handler = logging.FileHandler("chat_room.log")
        logging.getLogger("agnext").addHandler(handler)
    asyncio.run(main())
