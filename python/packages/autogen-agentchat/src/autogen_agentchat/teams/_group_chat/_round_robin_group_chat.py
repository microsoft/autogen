import asyncio
from typing import Any, Callable, List, Mapping, Union

from autogen_core import AgentRuntime, Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from ...base import ChatAgent, TerminationCondition
from ...messages import BaseAgentEvent, BaseChatMessage, MessageFactory, SelectSpeakerEvent
from ...state import RoundRobinManagerState
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager
from ._events import GroupChatTermination


class RoundRobinGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker in a round-robin fashion."""

    def __init__(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[
            Union[BaseAgentEvent, BaseChatMessage, GroupChatTermination, SelectSpeakerEvent]
        ],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        speaker_name: str | None = None,
    ) -> None:
        super().__init__(
            name,
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_names,
            participant_descriptions,
            output_message_queue,
            termination_condition,
            max_turns,
            message_factory,
            speaker_name=speaker_name,
        )
        self._next_speaker_index = 0

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def reset(self) -> None:
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._next_speaker_index = 0

    async def save_state(self) -> Mapping[str, Any]:
        state = RoundRobinManagerState(
            message_thread=[message.dump() for message in self._message_thread],
            current_turn=self._current_turn,
            next_speaker_index=self._next_speaker_index,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        round_robin_state = RoundRobinManagerState.model_validate(state)
        self._message_thread = [self._message_factory.create(message) for message in round_robin_state.message_thread]
        self._current_turn = round_robin_state.current_turn
        self._next_speaker_index = round_robin_state.next_speaker_index

    async def select_speaker(self, thread: List[BaseAgentEvent | BaseChatMessage]) -> str:
        """Select a speaker from the participants in a round-robin fashion."""
        current_speaker_index = self._next_speaker_index
        self._next_speaker_index = (current_speaker_index + 1) % len(self._participant_names)
        current_speaker = self._participant_names[current_speaker_index]
        return current_speaker


class RoundRobinGroupChatConfig(BaseModel):
    """The declarative configuration RoundRobinGroupChat."""

    participants: List[ComponentModel]
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None


class RoundRobinGroupChat(BaseGroupChat, Component[RoundRobinGroupChatConfig]):
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
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console


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
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = TextMentionTermination("TERMINATE")
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)
                await Console(team.run_stream(task="Tell me some jokes."))


            asyncio.run(main())
    """

    component_config_schema = RoundRobinGroupChatConfig
    component_provider_override = "autogen_agentchat.teams.RoundRobinGroupChat"

    # TODO: Add * to the constructor to separate the positional parameters from the kwargs.
    # This may be a breaking change so let's wait until a good time to do it.
    def __init__(
        self,
        participants: List[ChatAgent],
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
    ) -> None:
        super().__init__(
            participants,
            group_chat_manager_name="RoundRobinGroupChatManager",
            group_chat_manager_class=RoundRobinGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            custom_message_types=custom_message_types,
        )

    def _create_group_chat_manager_factory(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[
            Union[BaseAgentEvent, BaseChatMessage, GroupChatTermination, SelectSpeakerEvent]
        ],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        speaker_name: str | None = None,
    ) -> Callable[[], RoundRobinGroupChatManager]:
        def _factory() -> RoundRobinGroupChatManager:
            return RoundRobinGroupChatManager(
                name,
                group_topic_type,
                output_topic_type,
                participant_topic_types,
                participant_names,
                participant_descriptions,
                output_message_queue,
                termination_condition,
                max_turns,
                message_factory,
                speaker_name=speaker_name,
            )

        return _factory

    def _to_config(self) -> RoundRobinGroupChatConfig:
        participants = [participant.dump_component() for participant in self._participants]
        termination_condition = self._termination_condition.dump_component() if self._termination_condition else None
        return RoundRobinGroupChatConfig(
            participants=participants,
            termination_condition=termination_condition,
            max_turns=self._max_turns,
        )

    @classmethod
    def _from_config(cls, config: RoundRobinGroupChatConfig) -> Self:
        participants = [ChatAgent.load_component(participant) for participant in config.participants]
        termination_condition = (
            TerminationCondition.load_component(config.termination_condition) if config.termination_condition else None
        )
        return cls(participants, termination_condition=termination_condition, max_turns=config.max_turns)
