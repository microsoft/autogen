import logging
import re
from typing import Callable, Dict, List

from autogen_core.components.models import ChatCompletionClient, SystemMessage

from ... import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from ...base import ChatAgent, TerminationCondition
from ...messages import MultiModalMessage, StopMessage, TextMessage
from .._events import (
    GroupChatPublishEvent,
    GroupChatSelectSpeakerEvent,
)
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class SelectorGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker using a ChatCompletion
    model."""

    def __init__(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
        model_client: ChatCompletionClient,
        selector_prompt: str,
        allow_repeated_speaker: bool,
    ) -> None:
        super().__init__(
            parent_topic_type,
            group_topic_type,
            participant_topic_types,
            participant_descriptions,
            termination_condition,
        )
        self._model_client = model_client
        self._selector_prompt = selector_prompt
        self._previous_speaker: str | None = None
        self._allow_repeated_speaker = allow_repeated_speaker

    async def select_speaker(self, thread: List[GroupChatPublishEvent]) -> str:
        """Selects the next speaker in a group chat using a ChatCompletion client.

        A key assumption is that the agent type is the same as the topic type, which we use as the agent name.
        """
        history_messages: List[str] = []
        for event in thread:
            msg = event.agent_message
            source = event.source
            if source is None:
                message = ""
            else:
                # The agent type must be the same as the topic type, which we use as the agent name.
                message = f"{source.type}:"
            if isinstance(msg, TextMessage | StopMessage):
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
            select_speaker_messages = [SystemMessage(select_speaker_prompt)]
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
        event_logger.debug(GroupChatSelectSpeakerEvent(selected_speaker=agent_name, source=self.id))
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
            count = len(re.findall(regex, f" {message_content} "))  # Pad the message to help with matching
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
        selector_prompt (str, optional): The prompt template to use for selecting the next speaker.
            Must contain '{roles}', '{participants}', and '{history}' to be filled in.
        allow_repeated_speaker (bool, optional): Whether to allow the same speaker to be selected
            consecutively. Defaults to False.

    Raises:
        ValueError: If the number of participants is less than two or if the selector prompt is invalid.

    Examples:

    A team with multiple participants:

        .. code-block:: python

            from autogen_agentchat.agents import ToolUseAssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat, StopMessageTermination

            travel_advisor = ToolUseAssistantAgent("Travel_Advisor", model_client=..., registered_tools=...)
            hotel_agent = ToolUseAssistantAgent("Hotel_Agent", model_client=..., registered_tools=...)
            flight_agent = ToolUseAssistantAgent("Flight_Agent", model_client=..., registered_tools=...)
            team = SelectorGroupChat([travel_advisor, hotel_agent, flight_agent], model_client=...)
            await team.run("Book a 3-day trip to new york.", termination_condition=StopMessageTermination())
    """

    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        selector_prompt: str = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
""",
        allow_repeated_speaker: bool = False,
    ):
        super().__init__(participants, group_chat_manager_class=SelectorGroupChatManager)
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

    def _create_group_chat_manager_factory(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
    ) -> Callable[[], BaseGroupChatManager]:
        return lambda: SelectorGroupChatManager(
            parent_topic_type,
            group_topic_type,
            participant_topic_types,
            participant_descriptions,
            termination_condition,
            self._model_client,
            self._selector_prompt,
            self._allow_repeated_speaker,
        )
