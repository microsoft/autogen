from dataclasses import dataclass
import random
import asyncio
from typing import List
from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.application_components.single_threaded_agent_runtime import SingleThreadedAgentRuntime
from agnext.core.agent_runtime import AgentRuntime
from agnext.core.message import Message


# TODO: a runtime should be able to handle multiple types of messages
# TODO: allow request and response to be different message types
# should support this in handlers.
@dataclass
class GroupChatMessage(Message):
    body: str
    sender: str
    require_response: bool


class GroupChatParticipant(TypeRoutedAgent[GroupChatMessage]):
    def __init__(self, name: str, runtime: AgentRuntime[GroupChatMessage]) -> None:
        super().__init__(name, runtime)

    @message_handler(GroupChatMessage)
    async def on_new_message(self, message: GroupChatMessage) -> GroupChatMessage:
        print(f"{self.name} received message from {message.sender}: {message.body}")
        if not message.require_response:
            return GroupChatMessage(body="OK", sender=self.name, require_response=False)
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
        return GroupChatMessage(body=response_body, sender=self.name, require_response=False)


class RoundRobinChat(TypeRoutedAgent[GroupChatMessage]):
    def __init__(
        self, name: str, runtime: AgentRuntime[GroupChatMessage], agents: List[GroupChatParticipant], num_rounds: int
    ) -> None:
        super().__init__(name, runtime)
        self._agents = agents
        self._num_rounds = num_rounds

    @message_handler(GroupChatMessage)
    async def on_new_message(self, message: GroupChatMessage) -> GroupChatMessage:
        print(f"{self.name} received task request from {message.sender}: {message.body}")

        history = [message]
        previous_speaker: TypeRoutedAgent[GroupChatMessage] | None = None
        round = 0

        while round < self._num_rounds:
            # 1. Select speaker.
            speaker = self._agents[round % len(self._agents)]

            # 2. Send the last message to non-speaking agents.
            for agent in self._agents:
                if agent is not previous_speaker and agent is not speaker:
                    # TODO: should support a separate message type for just passing on a message.
                    _ = await self._send_message(
                        GroupChatMessage(body=history[-1].body, sender=history[-1].sender, require_response=False),
                        agent,
                    )

            # 3. Send the last message to the speaking agent and ask to speak.
            if previous_speaker is not speaker:
                response = await self._send_message(
                    GroupChatMessage(body=history[-1].body, sender=history[-1].sender, require_response=True), speaker
                )
            else:
                # The same speaker is speaking again.
                # TODO: should support a separate message type for request to speak only.
                response = await self._send_message(
                    GroupChatMessage(body="", sender=self.name, require_response=True), speaker
                )
            print(f"Speaker {speaker.name} responded with: {response.body}")

            # 4. Append the response to the history.
            history.append(response)

            # 5. Update the previous speaker.
            previous_speaker = speaker

            # 6. Increment the round.
            round += 1

        # Construct the final response.
        response_body = "\n".join([f"{message.sender}: {message.body}" for message in history])
        return GroupChatMessage(body=response_body, sender=self.name, require_response=False)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime[GroupChatMessage]()
    participants = [GroupChatParticipant(f"participant_{i}", runtime) for i in range(3)]
    chat = RoundRobinChat("chat_room", runtime, participants, num_rounds=10)

    response = runtime.send_message(GroupChatMessage(body="Hello!", sender="external", require_response=True), chat)

    while not response.done():
        await runtime.process_next()

    print((await response).body)


if __name__ == "__main__":
    asyncio.run(main())
