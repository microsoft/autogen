import logging
from typing import Any, Callable, List, Mapping

from autogen_core import AgentId, AgentProxy, MessageContext, RoutedAgent, message_handler
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import ChatCompletionClient, UserMessage

from ..types import (
    MultiModalMessage,
    PublishNow,
    Reset,
    TextMessage,
)
from ._group_chat_utils import select_speaker

logger = logging.getLogger("autogen_core.events")


class GroupChatManager(RoutedAgent):
    """An agent that manages a group chat through event-driven orchestration.

    Args:
        name (str): The name of the agent.
        description (str): The description of the agent.
        runtime (AgentRuntime): The runtime to register the agent.
        participants (List[AgentId]): The list of participants in the group chat.
        model_context (ChatCompletionContext): The context manager for storing
            and retrieving ChatCompletion messages.
        model_client (ChatCompletionClient, optional): The client to use for the model.
            If provided, the agent will use the model to select the next speaker.
            If not provided, the agent will select the next speaker from the list of participants
            according to the order given.
        termination_word (str, optional): The word that terminates the group chat. Defaults to "TERMINATE".
        transitions (Mapping[AgentId, List[AgentId]], optional): The transitions between agents.
            Keys are the agents, and values are the list of agents that can follow the key agent. Defaults to {}.
            If provided, the group chat manager will use the transitions to select the next speaker.
            If a transition is not provided for an agent, the choices fallback to all participants.
            If no model client is provided, a transition must have a single value.
        on_message_received (Callable[[TextMessage], None], optional): A custom handler to call when a message is received.
            Defaults to None.
    """

    def __init__(
        self,
        description: str,
        participants: List[AgentId],
        model_context: ChatCompletionContext,
        model_client: ChatCompletionClient | None = None,
        termination_word: str = "TERMINATE",
        transitions: Mapping[AgentId, List[AgentId]] = {},
        on_message_received: Callable[[TextMessage | MultiModalMessage], None] | None = None,
    ):
        super().__init__(description)
        self._model_context = model_context
        self._client = model_client
        self._participants = participants
        self._participant_proxies = dict((p, AgentProxy(p, self.runtime)) for p in participants)
        self._termination_word = termination_word
        for key, value in transitions.items():
            if not value:
                # Make sure no empty transitions are provided.
                raise ValueError(f"Empty transition list provided for {key.type}.")
            if key not in participants:
                # Make sure all keys are in the list of participants.
                raise ValueError(f"Transition key {key.type} not found in participants.")
            for v in value:
                if v not in participants:
                    # Make sure all values are in the list of participants.
                    raise ValueError(f"Transition value {v.type} not found in participants.")
            if self._client is None:
                # Make sure there is only one transition for each key if no model client is provided.
                if len(value) > 1:
                    raise ValueError(f"Multiple transitions provided for {key.type} but no model client is provided.")
        self._tranistions = transitions
        self._on_message_received = on_message_received

    @message_handler()
    async def on_reset(self, message: Reset, ctx: MessageContext) -> None:
        """Handle a reset message. This method clears the memory."""
        await self._model_context.clear()

    @message_handler()
    async def on_new_message(self, message: TextMessage | MultiModalMessage, ctx: MessageContext) -> None:
        """Handle a message. This method adds the message to the memory, selects the next speaker,
        and sends a message to the selected speaker to publish a response."""
        # Call the custom on_message_received handler if provided.
        if self._on_message_received is not None:
            self._on_message_received(message)

        # Check if the message contains the termination word.
        if isinstance(message, TextMessage) and self._termination_word in message.content:
            # Terminate the group chat by not selecting the next speaker.
            return

        # Save the message to chat memory.
        await self._model_context.add_message(UserMessage(content=message.content, source=message.source))

        # Get the last speaker.
        last_speaker_name = message.source
        last_speaker_index = next((i for i, p in enumerate(self._participants) if p.type == last_speaker_name), None)

        # Get the candidates for the next speaker.
        if last_speaker_index is not None:
            logger.debug(f"Last speaker: {last_speaker_name}")
            last_speaker = self._participants[last_speaker_index]
            if self._tranistions.get(last_speaker) is not None:
                candidates = [c for c in self._participants if c in self._tranistions[last_speaker]]
            else:
                candidates = self._participants
        else:
            candidates = self._participants
        logger.debug(f"Group chat manager next speaker candidates: {[c.type for c in candidates]}")

        # Select speaker.
        if len(candidates) == 0:
            speaker = None
        elif len(candidates) == 1:
            speaker = candidates[0]
        else:
            # More than one candidate, select the next speaker.
            if self._client is None:
                # If no model client is provided, candidates must be the list of participants.
                assert candidates == self._participants
                # If no model client is provided, select the next speaker from the list of participants.
                if last_speaker_index is not None:
                    next_speaker_index = (last_speaker_index + 1) % len(self._participants)
                    speaker = self._participants[next_speaker_index]
                else:
                    # If no last speaker, select the first speaker.
                    speaker = candidates[0]
            else:
                # If a model client is provided, select the speaker based on the transitions and the model.
                speaker_index = await select_speaker(
                    self._model_context, self._client, [self._participant_proxies[c] for c in candidates]
                )
                speaker = candidates[speaker_index]

        logger.debug(f"Group chat manager selected speaker: {speaker.type if speaker is not None else None}")

        if speaker is not None:
            # Send the message to the selected speaker to ask it to publish a response.
            await self.send_message(PublishNow(), speaker)

    async def save_state(self) -> Mapping[str, Any]:
        return {
            "chat_history": await self._model_context.save_state(),
            "termination_word": self._termination_word,
        }

    async def load_state(self, state: Mapping[str, Any]) -> None:
        # Load the chat history.
        await self._model_context.load_state(state["chat_history"])
        # Load the termination word.
        self._termination_word = state["termination_word"]
