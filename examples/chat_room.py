"""This is an example of a chat room with AI agents. It demonstrates how to use the
`TypeRoutedAgent` class to create custom agents that can use custom message types,
and interact with other using event-based messaging without an orchestrator."""

import argparse
import asyncio
import json
from dataclasses import dataclass

from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.memory import BufferedChatMemory, ChatMemory
from agnext.chat.types import TextMessage
from agnext.chat.utils import convert_messages_to_llm_messages
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import ChatCompletionClient, OpenAI, SystemMessage
from agnext.core import AgentRuntime, CancellationToken
from colorama import Fore, Style, init


# Define a custom message type for chat room messages.
@dataclass
class ChatRoomMessage(TextMessage):  # type: ignore
    pass


sep = "-" * 50

init(autoreset=True)


# Define a custom agent that can handle chat room messages.
class ChatRoomAgent(TypeRoutedAgent):  # type: ignore
    def __init__(  # type: ignore
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,  # type: ignore
        background_story: str,
        memory: ChatMemory,  # type: ignore
        model_client: ChatCompletionClient,  # type: ignore
        color: str = Style.RESET_ALL,
    ) -> None:  # type: ignore
        super().__init__(name, description, runtime)
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
        self._color = color

    @message_handler()  # type: ignore
    async def on_chat_room_message(self, message: ChatRoomMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        # Save the message to memory as structured JSON.
        from_message = TextMessage(
            content=json.dumps({"sender": message.source, "content": message.content}), source=message.source
        )
        self._memory.add_message(from_message)

        # Get a response from the model.
        raw_response = await self._client.create(
            self._system_messages + convert_messages_to_llm_messages(self._memory.get_messages(), self_name=self.name),
            json_output=True,
        )
        assert isinstance(raw_response.content, str)

        # Save the response to memory.
        self._memory.add_message(ChatRoomMessage(source=self.name, content=raw_response.content))

        # Parse the response.
        data = json.loads(raw_response.content)
        respond = data.get("respond")
        response = data.get("response")

        # Publish the response if needed.
        if respond is True or str(respond).lower().strip() == "true":
            await self._publish_message(ChatRoomMessage(source=self.name, content=str(response)))
            print(f"{sep}\n{self._color}{self.name}:{Style.RESET_ALL}\n{response}")


# Define a chat room with participants -- the runtime is the chat room.
def chat_room(runtime: AgentRuntime) -> None:  # type: ignore
    _ = ChatRoomAgent(
        name="Alice",
        description="Alice in the chat room.",
        runtime=runtime,
        background_story="Alice is a software engineer who loves to code.",
        memory=BufferedChatMemory(buffer_size=10),
        model_client=OpenAI(model="gpt-4-turbo"),  # type: ignore
        color=Fore.CYAN,
    )
    _ = ChatRoomAgent(
        name="Bob",
        description="Bob in the chat room.",
        runtime=runtime,
        background_story="Bob is a data scientist who loves to analyze data.",
        memory=BufferedChatMemory(buffer_size=10),
        model_client=OpenAI(model="gpt-4-turbo"),  # type: ignore
        color=Fore.GREEN,
    )
    _ = ChatRoomAgent(
        name="Charlie",
        description="Charlie in the chat room.",
        runtime=runtime,
        background_story="Charlie is a designer who loves to create art.",
        memory=BufferedChatMemory(buffer_size=10),
        model_client=OpenAI(model="gpt-4-turbo"),  # type: ignore
        color=Fore.MAGENTA,
    )


async def get_user_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


async def main(user_name: str, wait_seconds: int) -> None:
    runtime = SingleThreadedAgentRuntime()
    chat_room(runtime)
    while True:
        # TODO: allow user to input at any time while runtime is running.
        # Get user input and send messages to the chat room.
        # TODO: use Textual to build the UI.
        user_input = await get_user_input(f"{sep}\nYou:\n")
        if user_input.strip():
            # Publish user message if it is not empty.
            await runtime.publish_message(ChatRoomMessage(source=user_name, content=user_input))
        # Wait for agents to respond.
        while runtime.unprocessed_messages:
            await runtime.process_next()
            await asyncio.sleep(wait_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chat room simulation.")
    parser.add_argument(
        "--user-name",
        type=str,
        default="Host",
        help="The name of the user who is participating in the chat room.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=5,
        help="The number of seconds to wait between processing messages.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.user_name, args.wait_seconds))
