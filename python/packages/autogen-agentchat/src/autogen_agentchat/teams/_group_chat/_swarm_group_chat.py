import logging
from typing import Callable, List

from ... import EVENT_LOGGER_NAME
from ...base import ChatAgent, TerminationCondition
from ...messages import AgentMessage, HandoffMessage
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class SwarmGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker based on handoff message only."""

    def __init__(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        message_thread: List[AgentMessage],
        termination_condition: TerminationCondition | None,
    ) -> None:
        super().__init__(
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_descriptions,
            message_thread,
            termination_condition,
        )
        self._current_speaker = participant_topic_types[0]

    async def select_speaker(self, thread: List[AgentMessage]) -> str:
        """Select a speaker from the participants based on handoff message."""
        if len(thread) > 0 and isinstance(thread[-1], HandoffMessage):
            self._current_speaker = thread[-1].target
            if self._current_speaker not in self._participant_topic_types:
                raise ValueError("The selected speaker in the handoff message is not a participant.")
            return self._current_speaker
        else:
            return self._current_speaker


class Swarm(BaseGroupChat):
    """A group chat team that selects the next speaker based on handoff message only.

    The first participant in the list of participants is the initial speaker.
    The next speaker is selected based on the :class:`~autogen_agentchat.messages.HandoffMessage` message
    sent by the current speaker. If no handoff message is sent, the current speaker
    continues to be the speaker.

    Args:
        participants (List[ChatAgent]): The agents participating in the group chat. The first agent in the list is the initial speaker.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run indefinitely.

    Examples:

        .. code-block:: python

            import asyncio
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import Swarm
            from autogen_agentchat.task import MaxMessageTermination


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent(
                    "Alice",
                    model_client=model_client,
                    handoffs=["Bob"],
                    system_message="You are Alice and you only answer questions about yourself.",
                )
                agent2 = AssistantAgent(
                    "Bob", model_client=model_client, system_message="You are Bob and your birthday is on 1st January."
                )

                termination = MaxMessageTermination(3)
                team = Swarm([agent1, agent2], termination_condition=termination)

                stream = team.run_stream("What is bob's birthday?")
                async for message in stream:
                    print(message)


            asyncio.run(main())
    """

    def __init__(
        self, participants: List[ChatAgent], termination_condition: TerminationCondition | None = None
    ) -> None:
        super().__init__(
            participants, group_chat_manager_class=SwarmGroupChatManager, termination_condition=termination_condition
        )
        # The first participant must be able to produce handoff messages.
        first_participant = self._participants[0]
        if HandoffMessage not in first_participant.produced_message_types:
            raise ValueError("The first participant must be able to produce a handoff messages.")

    def _create_group_chat_manager_factory(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        message_thread: List[AgentMessage],
        termination_condition: TerminationCondition | None,
    ) -> Callable[[], SwarmGroupChatManager]:
        def _factory() -> SwarmGroupChatManager:
            return SwarmGroupChatManager(
                group_topic_type,
                output_topic_type,
                participant_topic_types,
                participant_descriptions,
                message_thread,
                termination_condition,
            )

        return _factory
