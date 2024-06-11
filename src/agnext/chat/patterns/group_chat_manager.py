from typing import Callable, List

from ...components import TypeRoutedAgent, message_handler
from ...components.models import ChatCompletionClient
from ...core import Agent, AgentRuntime, CancellationToken
from ..memory import ChatMemory
from ..types import (
    PublishNow,
    Reset,
    TextMessage,
)
from .group_chat_utils import select_speaker


class GroupChatManager(TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        participants: List[Agent],
        memory: ChatMemory,
        model_client: ChatCompletionClient | None = None,
        termination_word: str = "TERMINATE",
        on_message_received: Callable[[TextMessage], None] | None = None,
    ):
        super().__init__(name, description, runtime)
        self._memory = memory
        self._client = model_client
        self._participants = participants
        self._termination_word = termination_word
        self._on_message_received = on_message_received

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        self._memory.clear()

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        # Call the custom on_message_received handler if provided.
        if self._on_message_received is not None:
            self._on_message_received(message)

        # Check if the message is the termination word.
        if message.content.strip() == self._termination_word:
            # Terminate the group chat by not selecting the next speaker.
            return

        # Save the message to chat memory.
        self._memory.add_message(message)

        # Select speaker.
        if self._client is None:
            # If no model client is provided, select the next speaker from the list of participants.
            last_speaker_name = message.source
            last_speaker_index = next(
                (i for i, p in enumerate(self._participants) if p.name == last_speaker_name), None
            )
            if last_speaker_index is None:
                # If the last speaker is not found, select the first speaker in the list.
                next_speaker_index = 0
            else:
                next_speaker_index = (last_speaker_index + 1) % len(self._participants)
            speaker = self._participants[next_speaker_index]
        else:
            # If a model client is provided, select the speaker based on the model output.
            speaker = await select_speaker(self._memory, self._client, self._participants)

        # Send the message to the selected speaker to ask it to publish a response.
        await self._send_message(PublishNow(), speaker)
