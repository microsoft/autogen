from typing import List, Sequence

from ..agents.base import BaseChatAgent
from ..messages import ChatMessage
from ..runtimes import SingleThreadedRuntime


class GroupChat(BaseChatAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: SingleThreadedRuntime,
        agents: Sequence[BaseChatAgent],
        num_rounds: int,
    ) -> None:
        super().__init__(name, description, runtime)
        self._agents = agents
        self._num_rounds = num_rounds
        self._history: List[ChatMessage] = []

    async def on_chat_message(self, message: ChatMessage) -> ChatMessage:
        if message.reset:
            # Reset the history.
            self._history = []
        if message.save_message_only:
            # TODO: what should we do with save_message_only messages for this pattern?
            return ChatMessage(body="OK", sender=self.name)

        self._history.append(message)
        previous_speaker: BaseChatAgent | None = None
        round = 0

        while round < self._num_rounds:
            # TODO: add support for advanced speaker selection.
            # Select speaker (round-robin for now).
            speaker = self._agents[round % len(self._agents)]

            # Send the last message to non-speaking agents.
            for agent in [agent for agent in self._agents if agent is not previous_speaker and agent is not speaker]:
                _ = await self._send_message(
                    ChatMessage(
                        body=self._history[-1].body,
                        sender=self._history[-1].sender,
                        save_message_only=True,
                    ),
                    agent,
                )

            # Send the last message to the speaking agent and ask to speak.
            if previous_speaker is not speaker:
                response = await self._send_message(
                    ChatMessage(body=self._history[-1].body, sender=self._history[-1].sender),
                    speaker,
                )
            else:
                # The same speaker is speaking again.
                # TODO: should support a separate message type for request to speak only.
                response = await self._send_message(
                    ChatMessage(body="", sender=self.name),
                    speaker,
                )

            # 4. Append the response to the history.
            self._history.append(response)

            # 5. Update the previous speaker.
            previous_speaker = speaker

            # 6. Increment the round.
            round += 1

        # Construct the final response.
        response_body = "\n".join([f"{message.sender}: {message.body}" for message in self._history])
        return ChatMessage(body=response_body, sender=self.name)
