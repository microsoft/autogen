import asyncio
import logging
import re
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Union, cast

from autogen_core import AgentRuntime, CancellationToken, Component, ComponentModel
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    ModelFamily,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel
from typing_extensions import Self

from ... import TRACE_LOGGER_NAME
from ...agents import BaseChatAgent
from ...base import ChatAgent, TerminationCondition
from ...messages import (
    BaseAgentEvent,
    BaseChatMessage,
    MessageFactory,
)
from ...state import SelectorManagerState
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager
from ._events import GroupChatTermination

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

SyncSelectorFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], str | None]
AsyncSelectorFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[str | None]]
SelectorFuncType = Union[SyncSelectorFunc | AsyncSelectorFunc]

SyncCandidateFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], List[str]]
AsyncCandidateFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[List[str]]]
CandidateFuncType = Union[SyncCandidateFunc | AsyncCandidateFunc]


class SelectorGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker using a ChatCompletion
    model and a custom selector function."""

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
        model_client: ChatCompletionClient,
        selector_prompt: str,
        allow_repeated_speaker: bool,
        selector_func: Optional[SelectorFuncType],
        max_selector_attempts: int,
        candidate_func: Optional[CandidateFuncType],
        emit_team_events: bool,
        model_context: ChatCompletionContext | None,
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
        self._model_client = model_client
        self._selector_prompt = selector_prompt
        self._previous_speaker: str | None = None
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func
        self._is_selector_func_async = iscoroutinefunction(self._selector_func)
        self._max_selector_attempts = max_selector_attempts
        self._candidate_func = candidate_func
        self._is_candidate_func_async = iscoroutinefunction(self._candidate_func)
        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()
        self._cancellation_token = CancellationToken()

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def reset(self) -> None:
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._previous_speaker = None

    async def save_state(self) -> Mapping[str, Any]:
        state = SelectorManagerState(
            message_thread=[msg.dump() for msg in self._message_thread],
            current_turn=self._current_turn,
            previous_speaker=self._previous_speaker,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        selector_state = SelectorManagerState.model_validate(state)
        self._message_thread = [self._message_factory.create(msg) for msg in selector_state.message_thread]
        self._current_turn = selector_state.current_turn
        self._previous_speaker = selector_state.previous_speaker

    async def select_speaker(self, thread: List[BaseAgentEvent | BaseChatMessage]) -> str:
        """Selects the next speaker in a group chat using a ChatCompletion client,
        with the selector function as override if it returns a speaker name.

        A key assumption is that the agent type is the same as the topic type, which we use as the agent name.
        """

        # Use the selector function if provided.
        if self._selector_func is not None:
            if self._is_selector_func_async:
                async_selector_func = cast(AsyncSelectorFunc, self._selector_func)
                speaker = await async_selector_func(thread)
            else:
                sync_selector_func = cast(SyncSelectorFunc, self._selector_func)
                speaker = sync_selector_func(thread)
            if speaker is not None:
                if speaker not in self._participant_names:
                    raise ValueError(
                        f"Selector function returned an invalid speaker name: {speaker}. "
                        f"Expected one of: {self._participant_names}."
                    )
                # Skip the model based selection.
                return speaker

        # Use the candidate function to filter participants if provided
        if self._candidate_func is not None:
            if self._is_candidate_func_async:
                async_candidate_func = cast(AsyncCandidateFunc, self._candidate_func)
                participants = await async_candidate_func(thread)
            else:
                sync_candidate_func = cast(SyncCandidateFunc, self._candidate_func)
                participants = sync_candidate_func(thread)
            if not participants:
                raise ValueError("Candidate function must return a non-empty list of participant names.")
            if not all(p in self._participant_names for p in participants):
                raise ValueError(
                    f"Candidate function returned invalid participant names: {participants}. "
                    f"Expected one of: {self._participant_names}."
                )
        else:
            # Construct the candidate agent list to be selected from, skip the previous speaker if not allowed.
            if self._previous_speaker is not None and not self._allow_repeated_speaker:
                participants = [p for p in self._participant_names if p != self._previous_speaker]
            else:
                participants = list(self._participant_names)

        assert len(participants) > 0

        # Construct the history of the conversation.
        history = self.construct_message_history(thread)

        # Construct agent roles.
        # Each agent sould appear on a single line.
        roles = ""
        for topic_type, description in zip(self._participant_names, self._participant_descriptions, strict=True):
            roles += re.sub(r"\s+", " ", f"{topic_type}: {description}").strip() + "\n"
        roles = roles.strip()

        # Select the next speaker.
        if len(participants) > 1:
            agent_name = await self._select_speaker(roles, participants, history, self._max_selector_attempts)
        else:
            agent_name = participants[0]
        self._previous_speaker = agent_name
        trace_logger.debug(f"Selected speaker: {agent_name}")
        return agent_name

    def construct_message_history(
        self, message_history: Sequence[Union[BaseChatMessage, BaseAgentEvent, UserMessage, AssistantMessage]]
    ) -> str:
        # Construct the history of the conversation.
        history_messages: List[str] = []
        for msg in message_history:
            if isinstance(msg, BaseChatMessage):
                message = f"{msg.source}: {msg.to_model_text()}"
                history_messages.append(message.rstrip() + "\n\n")
            elif isinstance(msg, UserMessage) or isinstance(msg, AssistantMessage):
                message = f"{msg.source}: {msg.content}"
                history_messages.append(
                    message.rstrip() + "\n\n"
                )  # Create some consistency for how messages are separated in the transcript

        history: str = "\n".join(history_messages)
        return history

    async def _select_speaker(self, roles: str, participants: List[str], history: str, max_attempts: int) -> str:
        model_context_messages = await self._model_context.get_messages()
        model_context_history = self.construct_message_history(model_context_messages)  # type: ignore
        history = model_context_history + history

        select_speaker_prompt = self._selector_prompt.format(
            roles=roles, participants=str(participants), history=history
        )

        select_speaker_messages: List[SystemMessage | UserMessage | AssistantMessage]
        if ModelFamily.is_openai(self._model_client.model_info["family"]):
            select_speaker_messages = [SystemMessage(content=select_speaker_prompt)]
        else:
            # Many other models need a UserMessage to respond to
            select_speaker_messages = [UserMessage(content=select_speaker_prompt, source="user")]

        num_attempts = 0
        while num_attempts < max_attempts:
            num_attempts += 1
            response = await self._model_client.create(messages=select_speaker_messages)
            assert isinstance(response.content, str)
            select_speaker_messages.append(AssistantMessage(content=response.content, source="selector"))
            # NOTE: we use all participant names to check for mentions, even if the previous speaker is not allowed.
            # This is because the model may still select the previous speaker, and we want to catch that.
            mentions = self._mentioned_agents(response.content, self._participant_names)
            if len(mentions) == 0:
                trace_logger.debug(f"Model failed to select a valid name: {response.content} (attempt {num_attempts})")
                feedback = f"No valid name was mentioned. Please select from: {str(participants)}."
                select_speaker_messages.append(UserMessage(content=feedback, source="user"))
            elif len(mentions) > 1:
                trace_logger.debug(f"Model selected multiple names: {str(mentions)} (attempt {num_attempts})")
                feedback = (
                    f"Expected exactly one name to be mentioned. Please select only one from: {str(participants)}."
                )
                select_speaker_messages.append(UserMessage(content=feedback, source="user"))
            else:
                agent_name = list(mentions.keys())[0]
                if (
                    not self._allow_repeated_speaker
                    and self._previous_speaker is not None
                    and agent_name == self._previous_speaker
                ):
                    trace_logger.debug(f"Model selected the previous speaker: {agent_name} (attempt {num_attempts})")
                    feedback = (
                        f"Repeated speaker is not allowed, please select a different name from: {str(participants)}."
                    )
                    select_speaker_messages.append(UserMessage(content=feedback, source="user"))
                else:
                    # Valid selection
                    trace_logger.debug(f"Model selected a valid name: {agent_name} (attempt {num_attempts})")
                    return agent_name

        if self._previous_speaker is not None:
            trace_logger.warning(f"Model failed to select a speaker after {max_attempts}, using the previous speaker.")
            return self._previous_speaker
        trace_logger.warning(
            f"Model failed to select a speaker after {max_attempts} and there was no previous speaker, using the first participant."
        )
        return participants[0]

    def _mentioned_agents(self, message_content: str, agent_names: List[str]) -> Dict[str, int]:
        """Counts the number of times each agent is mentioned in the provided message content.
        Agent names will match under any of the following conditions (all case-sensitive):
        - Exact name match
        - If the agent name has underscores it will match with spaces instead (e.g. 'Story_writer' == 'Story writer')
        - If the agent name has underscores it will match with '\\_' instead of '_' (e.g. 'Story_writer' == 'Story\\_writer')

        Args:
            message_content (Union[str, List]): The content of the message, either as a single string or a list of strings.
            agents (List[Agent]): A list of Agent objects, each having a 'name' attribute to be searched in the message content.

        Returns:
            Dict: a counter for mentioned agents.
        """
        mentions: Dict[str, int] = dict()
        for name in agent_names:
            # Finds agent mentions, taking word boundaries into account,
            # accommodates escaping underscores and underscores as spaces
            regex = (
                r"(?<=\W)("
                + re.escape(name)
                + r"|"
                + re.escape(name.replace("_", " "))
                + r"|"
                + re.escape(name.replace("_", r"\_"))
                + r")(?=\W)"
            )
            # Pad the message to help with matching
            count = len(re.findall(regex, f" {message_content} "))
            if count > 0:
                mentions[name] = count
        return mentions


class SelectorGroupChatConfig(BaseModel):
    """The declarative configuration for SelectorGroupChat."""

    participants: List[ComponentModel]
    model_client: ComponentModel
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    selector_prompt: str
    allow_repeated_speaker: bool
    # selector_func: ComponentModel | None
    max_selector_attempts: int = 3
    emit_team_events: bool = False


class SelectorGroupChat(BaseGroupChat, Component[SelectorGroupChatConfig]):
    """A group chat team that have participants takes turn to publish a message
    to all, using a ChatCompletion model to select the next speaker after each message.

    Args:
        participants (List[ChatAgent]): The participants in the group chat,
            must have unique names and at least two participants.
        model_client (ChatCompletionClient): The ChatCompletion model client used
            to select the next speaker.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run indefinitely.
        max_turns (int, optional): The maximum number of turns in the group chat before stopping. Defaults to None, meaning no limit.
        selector_prompt (str, optional): The prompt template to use for selecting the next speaker.
            Available fields: '{roles}', '{participants}', and '{history}'.
        allow_repeated_speaker (bool, optional): Whether to include the previous speaker in the list of candidates to be selected for the next turn.
            Defaults to False. The model may still select the previous speaker -- a warning will be logged if this happens.
        max_selector_attempts (int, optional): The maximum number of attempts to select a speaker using the model. Defaults to 3.
            If the model fails to select a speaker after the maximum number of attempts, the previous speaker will be used if available,
            otherwise the first participant will be used.
        selector_func (Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], str | None], Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[str | None]], optional): A custom selector
            function that takes the conversation history and returns the name of the next speaker.
            If provided, this function will be used to override the model to select the next speaker.
            If the function returns None, the model will be used to select the next speaker.
        candidate_func (Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], List[str]], Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[List[str]]], optional):
            A custom function that takes the conversation history and returns a filtered list of candidates for the next speaker
            selection using model. If the function returns an empty list or `None`, `SelectorGroupChat` will raise a `ValueError`.
            This function is only used if `selector_func` is not set. The `allow_repeated_speaker` will be ignored if set.
        emit_team_events (bool, optional): Whether to emit team events through :meth:`BaseGroupChat.run_stream`. Defaults to False.

    Raises:
        ValueError: If the number of participants is less than two or if the selector prompt is invalid.

    Examples:

    A team with multiple participants:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                async def lookup_hotel(location: str) -> str:
                    return f"Here are some hotels in {location}: hotel1, hotel2, hotel3."

                async def lookup_flight(origin: str, destination: str) -> str:
                    return f"Here are some flights from {origin} to {destination}: flight1, flight2, flight3."

                async def book_trip() -> str:
                    return "Your trip is booked!"

                travel_advisor = AssistantAgent(
                    "Travel_Advisor",
                    model_client,
                    tools=[book_trip],
                    description="Helps with travel planning.",
                )
                hotel_agent = AssistantAgent(
                    "Hotel_Agent",
                    model_client,
                    tools=[lookup_hotel],
                    description="Helps with hotel booking.",
                )
                flight_agent = AssistantAgent(
                    "Flight_Agent",
                    model_client,
                    tools=[lookup_flight],
                    description="Helps with flight booking.",
                )
                termination = TextMentionTermination("TERMINATE")
                team = SelectorGroupChat(
                    [travel_advisor, hotel_agent, flight_agent],
                    model_client=model_client,
                    termination_condition=termination,
                )
                await Console(team.run_stream(task="Book a 3-day trip to new york."))


            asyncio.run(main())

    A team with a custom selector function:

        .. code-block:: python

            import asyncio
            from typing import Sequence
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console
            from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                def check_calculation(x: int, y: int, answer: int) -> str:
                    if x + y == answer:
                        return "Correct!"
                    else:
                        return "Incorrect!"

                agent1 = AssistantAgent(
                    "Agent1",
                    model_client,
                    description="For calculation",
                    system_message="Calculate the sum of two numbers",
                )
                agent2 = AssistantAgent(
                    "Agent2",
                    model_client,
                    tools=[check_calculation],
                    description="For checking calculation",
                    system_message="Check the answer and respond with 'Correct!' or 'Incorrect!'",
                )

                def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
                    if len(messages) == 1 or messages[-1].to_text() == "Incorrect!":
                        return "Agent1"
                    if messages[-1].source == "Agent1":
                        return "Agent2"
                    return None

                termination = TextMentionTermination("Correct!")
                team = SelectorGroupChat(
                    [agent1, agent2],
                    model_client=model_client,
                    selector_func=selector_func,
                    termination_condition=termination,
                )

                await Console(team.run_stream(task="What is 1 + 1?"))


            asyncio.run(main())
    """

    component_config_schema = SelectorGroupChatConfig
    component_provider_override = "autogen_agentchat.teams.SelectorGroupChat"

    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        selector_prompt: str = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
""",
        allow_repeated_speaker: bool = False,
        max_selector_attempts: int = 3,
        selector_func: Optional[SelectorFuncType] = None,
        candidate_func: Optional[CandidateFuncType] = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
        emit_team_events: bool = False,
        model_context: ChatCompletionContext | None = None,
    ):
        super().__init__(
            participants,
            group_chat_manager_name="SelectorGroupChatManager",
            group_chat_manager_class=SelectorGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            custom_message_types=custom_message_types,
            emit_team_events=emit_team_events,
        )
        # Validate the participants.
        if len(participants) < 2:
            raise ValueError("At least two participants are required for SelectorGroupChat.")
        self._selector_prompt = selector_prompt
        self._model_client = model_client
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func
        self._max_selector_attempts = max_selector_attempts
        self._candidate_func = candidate_func
        self._model_context = model_context

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
    ) -> Callable[[], BaseGroupChatManager]:
        return lambda: SelectorGroupChatManager(
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
            self._model_client,
            self._selector_prompt,
            self._allow_repeated_speaker,
            self._selector_func,
            self._max_selector_attempts,
            self._candidate_func,
            self._emit_team_events,
            self._model_context,
        )

    def _to_config(self) -> SelectorGroupChatConfig:
        return SelectorGroupChatConfig(
            participants=[participant.dump_component() for participant in self._participants],
            model_client=self._model_client.dump_component(),
            termination_condition=self._termination_condition.dump_component() if self._termination_condition else None,
            max_turns=self._max_turns,
            selector_prompt=self._selector_prompt,
            allow_repeated_speaker=self._allow_repeated_speaker,
            max_selector_attempts=self._max_selector_attempts,
            # selector_func=self._selector_func.dump_component() if self._selector_func else None,
            emit_team_events=self._emit_team_events,
        )

    @classmethod
    def _from_config(cls, config: SelectorGroupChatConfig) -> Self:
        return cls(
            participants=[BaseChatAgent.load_component(participant) for participant in config.participants],
            model_client=ChatCompletionClient.load_component(config.model_client),
            termination_condition=TerminationCondition.load_component(config.termination_condition)
            if config.termination_condition
            else None,
            max_turns=config.max_turns,
            selector_prompt=config.selector_prompt,
            allow_repeated_speaker=config.allow_repeated_speaker,
            max_selector_attempts=config.max_selector_attempts,
            # selector_func=ComponentLoader.load_component(config.selector_func, Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], str | None])
            # if config.selector_func
            # else None,
            emit_team_events=config.emit_team_events,
        )
