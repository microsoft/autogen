from typing import Any, Callable, List, Mapping

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
    """An agent that manages a group chat through event-driven orchestration.

    Args:
        name (str): The name of the agent.
        description (str): The description of the agent.
        runtime (AgentRuntime): The runtime to register the agent.
        participants (List[Agent]): The list of participants in the group chat.
        memory (ChatMemory): The memory to store and retrieve messages.
        model_client (ChatCompletionClient, optional): The client to use for the model.
            If provided, the agent will use the model to select the next speaker.
            If not provided, the agent will select the next speaker from the list of participants
            according to the order given.
        termination_word (str, optional): The word that terminates the group chat. Defaults to "TERMINATE".
        on_message_received (Callable[[TextMessage], None], optional): A custom handler to call when a message is received.
            Defaults to None.
    """

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
        """Handle a reset message. This method clears the memory."""
        await self._memory.clear()

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        """Handle a text message. This method adds the message to the memory, selects the next speaker,
        and sends a message to the selected speaker to publish a response."""
        # Call the custom on_message_received handler if provided.
        if self._on_message_received is not None:
            self._on_message_received(message)

        # Check if the message is the termination word.
        if message.content.strip() == self._termination_word:
            # Terminate the group chat by not selecting the next speaker.
            return

        # Save the message to chat memory.
        await self._memory.add_message(message)

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

    def save_state(self) -> Mapping[str, Any]:
        return {
            "memory": self._memory.save_state(),
            "termination_word": self._termination_word,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._memory.load_state(state["memory"])
        self._termination_word = state["termination_word"]
