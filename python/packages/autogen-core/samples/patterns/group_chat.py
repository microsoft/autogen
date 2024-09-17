"""
This example shows how to use publish-subscribe to implement
a simple round-robin group chat among multiple agents:
each agent in the group chat takes turns speaking in a round-robin fashion.
The conversation ends after a specified number of rounds.

1. Upon receiving a message, the group chat manager selects the next speaker
in a round-robin fashion and sends a request to speak message to the selected speaker.
2. Upon receiving a request to speak message, the speaker generates a response
to the last message in the memory and publishes the response.
3. The conversation continues until the specified number of rounds is reached.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext
from autogen_core.components import DefaultTopicId, RoutedAgent, message_handler
from autogen_core.components._default_subscription import DefaultSubscription
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autogen_core.base import MessageContext
from common.utils import get_chat_completion_client_from_envs


@dataclass
class Message:
    source: str
    content: str


@dataclass
class RequestToSpeak:
    pass


@dataclass
class Termination:
    pass


class RoundRobinGroupChatManager(RoutedAgent):
    def __init__(
        self,
        description: str,
        participants: List[AgentId],
        num_rounds: int,
    ) -> None:
        super().__init__(description)
        self._participants = participants
        self._num_rounds = num_rounds
        self._round_count = 0

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        # Select the next speaker in a round-robin fashion
        speaker = self._participants[self._round_count % len(self._participants)]
        self._round_count += 1
        if self._round_count > self._num_rounds * len(self._participants):
            # End the conversation after the specified number of rounds.
            await self.publish_message(Termination(), DefaultTopicId())
            return
        # Send a request to speak message to the selected speaker.
        await self.send_message(RequestToSpeak(), speaker)


class GroupChatParticipant(RoutedAgent):
    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description)
        self._system_messages = system_messages
        self._model_client = model_client
        self._memory: List[Message] = []

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        self._memory.append(message)

    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        # Generate a response to the last message in the memory
        if not self._memory:
            return
        llm_messages: List[LLMMessage] = []
        for m in self._memory[-10:]:
            if m.source == self.metadata["type"]:
                llm_messages.append(AssistantMessage(content=m.content, source=self.metadata["type"]))
            else:
                llm_messages.append(UserMessage(content=m.content, source=m.source))
        response = await self._model_client.create(self._system_messages + llm_messages)
        assert isinstance(response.content, str)
        speech = Message(content=response.content, source=self.metadata["type"])
        self._memory.append(speech)
        await self.publish_message(speech, topic_id=DefaultTopicId())


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Register the participants.
    await runtime.register(
        "DataScientist",
        lambda: GroupChatParticipant(
            description="A data scientist",
            system_messages=[SystemMessage("You are a data scientist.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
        ),
        lambda: [DefaultSubscription()],
    )

    await runtime.register(
        "Engineer",
        lambda: GroupChatParticipant(
            description="An engineer",
            system_messages=[SystemMessage("You are an engineer.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
        ),
        lambda: [DefaultSubscription()],
    )
    await runtime.register(
        "Artist",
        lambda: GroupChatParticipant(
            description="An artist",
            system_messages=[SystemMessage("You are an artist.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
        ),
        lambda: [DefaultSubscription()],
    )

    # Register the group chat manager.
    await runtime.register(
        "GroupChatManager",
        lambda: RoundRobinGroupChatManager(
            description="A group chat manager",
            participants=[
                AgentId("DataScientist", AgentInstantiationContext.current_agent_id().key),
                AgentId("Engineer", AgentInstantiationContext.current_agent_id().key),
                AgentId("Artist", AgentInstantiationContext.current_agent_id().key),
            ],
            num_rounds=3,
        ),
        lambda: [DefaultSubscription()],
    )

    # Start the runtime.
    runtime.start()

    # Start the conversation.
    await runtime.publish_message(Message(content="Hello, everyone!", source="Moderator"), topic_id=DefaultTopicId())

    await runtime.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
