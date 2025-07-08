import asyncio
from typing import Any, Callable, List, Mapping, Sequence

from autogen_core import AgentRuntime, Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from ...base import ChatAgent, Team, TerminationCondition
from ...messages import BaseAgentEvent, BaseChatMessage, MessageFactory
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
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        emit_team_events: bool,
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
            emit_team_events,
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

    async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str] | str:
        """Select a speaker from the participants in a round-robin fashion.

        .. note::

            This method always returns a single speaker.
        """
        current_speaker_index = self._next_speaker_index
        self._next_speaker_index = (current_speaker_index + 1) % len(self._participant_names)
        current_speaker = self._participant_names[current_speaker_index]
        return current_speaker


class RoundRobinGroupChatConfig(BaseModel):
    """The declarative configuration RoundRobinGroupChat."""

    name: str | None = None
    description: str | None = None
    participants: List[ComponentModel]
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    emit_team_events: bool = False


class RoundRobinGroupChat(BaseGroupChat, Component[RoundRobinGroupChatConfig]):
    """A team that runs a group chat with participants taking turns in a round-robin fashion
    to publish a message to all.

    If an :class:`~autogen_agentchat.base.ChatAgent` is a participant,
    the :class:`~autogen_agentchat.messages.BaseChatMessage` from the agent response's
    :attr:`~autogen_agentchat.base.Response.chat_message` will be published
    to other participants in the group chat.

    If a :class:`~autogen_agentchat.base.Team` is a participant,
    the :class:`~autogen_agentchat.messages.BaseChatMessage`
    from the team result' :attr:`~autogen_agentchat.base.TaskResult.messages` will be published
    to other participants in the group chat.

    If a single participant is in the team, the participant will be the only speaker.

    Args:
        participants (List[ChatAgent | Team]): The participants in the group chat.
        name (str | None, optional): The name of the group chat, using :attr:`~autogen_agentchat.teams.RoundRobinGroupChat.DEFAULT_NAME` if not provided.
            The name is used by a parent team to identify this group chat so it must be unique within the parent team.
        description (str | None, optional): The description of the group chat, using :attr:`~autogen_agentchat.teams.RoundRobinGroupChat.DEFAULT_DESCRIPTION` if not provided.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run indefinitely.
        max_turns (int, optional): The maximum number of turns in the group chat before stopping. Defaults to None, meaning no limit.
        custom_message_types (List[type[BaseAgentEvent | BaseChatMessage]], optional): A list of custom message types that will be used in the group chat.
            If you are using custom message types or your agents produces custom message types, you need to specify them here.
            Make sure your custom message types are subclasses of :class:`~autogen_agentchat.messages.BaseAgentEvent` or :class:`~autogen_agentchat.messages.BaseChatMessage`.
        emit_team_events (bool, optional): Whether to emit team events through :meth:`BaseGroupChat.run_stream`. Defaults to False.

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

    DEFAULT_NAME = "RoundRobinGroupChat"
    DEFAULT_DESCRIPTION = "A team of agents."

    def __init__(
        self,
        participants: List[ChatAgent | Team],
        *,
        name: str | None = None,
        description: str | None = None,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
        emit_team_events: bool = False,
    ) -> None:
        super().__init__(
            name=name or self.DEFAULT_NAME,
            description=description or self.DEFAULT_DESCRIPTION,
            participants=participants,
            group_chat_manager_name="RoundRobinGroupChatManager",
            group_chat_manager_class=RoundRobinGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            custom_message_types=custom_message_types,
            emit_team_events=emit_team_events,
        )

    def _create_group_chat_manager_factory(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
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
                self._emit_team_events,
            )

        return _factory

    def _to_config(self) -> RoundRobinGroupChatConfig:
        participants = [participant.dump_component() for participant in self._participants]
        termination_condition = self._termination_condition.dump_component() if self._termination_condition else None
        return RoundRobinGroupChatConfig(
            name=self._name,
            description=self._description,
            participants=participants,
            termination_condition=termination_condition,
            max_turns=self._max_turns,
            emit_team_events=self._emit_team_events,
        )

    @classmethod
    def _from_config(cls, config: RoundRobinGroupChatConfig) -> Self:
        participants: List[ChatAgent | Team] = []
        for participant in config.participants:
            if participant.component_type == Team.component_type:
                participants.append(Team.load_component(participant))
            else:
                participants.append(ChatAgent.load_component(participant))

        termination_condition = (
            TerminationCondition.load_component(config.termination_condition) if config.termination_condition else None
        )
        return cls(
            participants,
            name=config.name,
            description=config.description,
            termination_condition=termination_condition,
            max_turns=config.max_turns,
            emit_team_events=config.emit_team_events,
        )
