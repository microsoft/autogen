import logging
import re
from typing import Any, Callable, Dict, List, Mapping, Sequence

from autogen_core.models import ChatCompletionClient, SystemMessage

from ... import TRACE_LOGGER_NAME
from ...base import ChatAgent, TerminationCondition
from ...messages import (
    AgentMessage,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from ...state import SelectorManagerState
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


class SelectorGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker using a ChatCompletion
    model and a custom selector function."""

    def __init__(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        model_client: ChatCompletionClient,
        selector_prompt: str,
        allow_repeated_speaker: bool,
        selector_func: Callable[[Sequence[AgentMessage]], str | None] | None,
    ) -> None:
        super().__init__(
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_descriptions,
            termination_condition,
            max_turns,
        )
        self._model_client = model_client
        self._selector_prompt = selector_prompt
        self._previous_speaker: str | None = None
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func

    async def validate_group_state(self, message: ChatMessage | None) -> None:
        pass

    async def reset(self) -> None:
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._previous_speaker = None

    async def save_state(self) -> Mapping[str, Any]:
        state = SelectorManagerState(
            message_thread=list(self._message_thread),
            current_turn=self._current_turn,
            previous_speaker=self._previous_speaker,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        selector_state = SelectorManagerState.model_validate(state)
        self._message_thread = list(selector_state.message_thread)
        self._current_turn = selector_state.current_turn
        self._previous_speaker = selector_state.previous_speaker

    async def select_speaker(self, thread: List[AgentMessage]) -> str:
        """Selects the next speaker in a group chat using a ChatCompletion client,
        with the selector function as override if it returns a speaker name.

        A key assumption is that the agent type is the same as the topic type, which we use as the agent name.
        """

        # Use the selector function if provided.
        if self._selector_func is not None:
            speaker = self._selector_func(thread)
            if speaker is not None:
                # Skip the model based selection.
                return speaker

        # Construct the history of the conversation.
        history_messages: List[str] = []
        for msg in thread:
            if isinstance(msg, ToolCallMessage | ToolCallResultMessage):
                # Ignore tool call messages.
                continue
            # The agent type must be the same as the topic type, which we use as the agent name.
            message = f"{msg.source}:"
            if isinstance(msg, TextMessage | StopMessage | HandoffMessage):
                message += f" {msg.content}"
            elif isinstance(msg, MultiModalMessage):
                for item in msg.content:
                    if isinstance(item, str):
                        message += f" {item}"
                    else:
                        message += " [Image]"
            else:
                raise ValueError(f"Unexpected message type in selector: {type(msg)}")
            history_messages.append(message)
        history = "\n".join(history_messages)

        # Construct agent roles, we are using the participant topic type as the agent name.
        roles = "\n".join(
            [
                f"{topic_type}: {description}".strip()
                for topic_type, description in zip(
                    self._participant_topic_types, self._participant_descriptions, strict=True
                )
            ]
        )

        # Construct agent list to be selected, skip the previous speaker if not allowed.
        if self._previous_speaker is not None and not self._allow_repeated_speaker:
            participants = [p for p in self._participant_topic_types if p != self._previous_speaker]
        else:
            participants = self._participant_topic_types
        assert len(participants) > 0

        # Select the next speaker.
        if len(participants) > 1:
            select_speaker_prompt = self._selector_prompt.format(
                roles=roles, participants=str(participants), history=history
            )
            select_speaker_messages = [SystemMessage(content=select_speaker_prompt)]
            response = await self._model_client.create(messages=select_speaker_messages)
            assert isinstance(response.content, str)
            mentions = self._mentioned_agents(response.content, self._participant_topic_types)
            if len(mentions) != 1:
                raise ValueError(f"Expected exactly one agent to be mentioned, but got {mentions}")
            agent_name = list(mentions.keys())[0]
            if (
                not self._allow_repeated_speaker
                and self._previous_speaker is not None
                and agent_name == self._previous_speaker
            ):
                trace_logger.warning(f"Selector selected the previous speaker: {agent_name}")
        else:
            agent_name = participants[0]
        self._previous_speaker = agent_name
        trace_logger.debug(f"Selected speaker: {agent_name}")
        return agent_name

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


class SelectorGroupChat(BaseGroupChat):
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
            Must contain '{roles}', '{participants}', and '{history}' to be filled in.
        allow_repeated_speaker (bool, optional): Whether to allow the same speaker to be selected
            consecutively. Defaults to False.
        selector_func (Callable[[Sequence[AgentMessage]], str | None], optional): A custom selector
            function that takes the conversation history and returns the name of the next speaker.
            If provided, this function will be used to override the model to select the next speaker.
            If the function returns None, the model will be used to select the next speaker.

    Raises:
        ValueError: If the number of participants is less than two or if the selector prompt is invalid.

    Examples:

    A team with multiple participants:

        .. code-block:: python

            import asyncio
            from autogen_ext.models import OpenAIChatCompletionClient
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
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console
            from autogen_agentchat.messages import AgentMessage


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

                def selector_func(messages: Sequence[AgentMessage]) -> str | None:
                    if len(messages) == 1 or messages[-1].content == "Incorrect!":
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

    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        selector_prompt: str = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
""",
        allow_repeated_speaker: bool = False,
        selector_func: Callable[[Sequence[AgentMessage]], str | None] | None = None,
    ):
        super().__init__(
            participants,
            group_chat_manager_class=SelectorGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
        )
        # Validate the participants.
        if len(participants) < 2:
            raise ValueError("At least two participants are required for SelectorGroupChat.")
        # Validate the selector prompt.
        if "{roles}" not in selector_prompt:
            raise ValueError("The selector prompt must contain '{roles}'")
        if "{participants}" not in selector_prompt:
            raise ValueError("The selector prompt must contain '{participants}'")
        if "{history}" not in selector_prompt:
            raise ValueError("The selector prompt must contain '{history}'")
        self._selector_prompt = selector_prompt
        self._model_client = model_client
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func

    def _create_group_chat_manager_factory(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
    ) -> Callable[[], BaseGroupChatManager]:
        return lambda: SelectorGroupChatManager(
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_descriptions,
            termination_condition,
            max_turns,
            self._model_client,
            self._selector_prompt,
            self._allow_repeated_speaker,
            self._selector_func,
        )
