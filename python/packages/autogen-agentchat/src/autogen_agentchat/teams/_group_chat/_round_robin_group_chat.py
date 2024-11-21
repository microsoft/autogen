from typing import Callable, List

from ...base import ChatAgent, TerminationCondition
from ...messages import AgentMessage, ChatMessage
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager


class RoundRobinGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker in a round-robin fashion."""

    def __init__(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
        max_turns: int | None = None,
    ) -> None:
        super().__init__(
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_descriptions,
            termination_condition,
            max_turns,
        )
        self._next_speaker_index = 0

    async def validate_group_state(self, message: ChatMessage | None) -> None:
        pass

    async def reset(self) -> None:
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._next_speaker_index = 0

    async def select_speaker(self, thread: List[AgentMessage]) -> str:
        """Select a speaker from the participants in a round-robin fashion."""
        current_speaker_index = self._next_speaker_index
        self._next_speaker_index = (current_speaker_index + 1) % len(self._participant_topic_types)
        current_speaker = self._participant_topic_types[current_speaker_index]
        return current_speaker


class RoundRobinGroupChat(BaseGroupChat):
    """A team that runs a group chat with participants taking turns in a round-robin fashion
    to publish a message to all.

    If a single participant is in the team, the participant will be the only speaker.

    Args:
        participants (List[BaseChatAgent]): The participants in the group chat.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run indefinitely.
        max_turns (int, optional): The maximum number of turns in the group chat before stopping. Defaults to None, meaning no limit.

    Raises:
        ValueError: If no participants are provided or if participant names are not unique.

    Examples:

    A team with one participant with tools:

        .. code-block:: python

            import asyncio
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.task import TextMentionTermination, Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                async def get_weather(location: str) -> str:
                    return f"The weather in {location} is sunny."

                assistant = AssistantAgent(
                    "Assistant",
                    model_client=model_client,
                    tools=[get_weather],
                )
                termination = TextMentionTermination("TERMINATE")
                team = RoundRobinGroupChat([assistant], termination_condition=termination)
                await Console(team.run_stream(task="What's the weather in New York?"))


            asyncio.run(main())

    A team with multiple participants:

        .. code-block:: python

            import asyncio
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.task import TextMentionTermination, Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = TextMentionTermination("TERMINATE")
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)
                await Console(team.run_stream(task="Tell me some jokes."))


            asyncio.run(main())
    """

    def __init__(
        self,
        participants: List[ChatAgent],
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
    ) -> None:
        super().__init__(
            participants,
            group_chat_manager_class=RoundRobinGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
        )

    def _create_group_chat_manager_factory(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
    ) -> Callable[[], RoundRobinGroupChatManager]:
        def _factory() -> RoundRobinGroupChatManager:
            return RoundRobinGroupChatManager(
                group_topic_type,
                output_topic_type,
                participant_topic_types,
                participant_descriptions,
                termination_condition,
                max_turns,
            )

        return _factory
