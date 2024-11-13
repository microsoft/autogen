import json
from abc import ABC, abstractmethod
from typing import Any, List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from ....base import TerminationCondition, Response
from ....messages import (
    TextMessage,
    AgentMessage, 
    StopMessage,
)
from .._events import (
    GroupChatAgentResponse,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatStart,
    GroupChatTermination,
    GroupChatMessage,
)
#from .._base_group_chat_manager import BaseGroupChatManager
from .._sequential_routed_agent import SequentialRoutedAgent


from ._prompts import (
    ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT,
    ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
)

#class LedgerOrchestratorManager(BaseGroupChatManager):
class LedgerOrchestratorManager(SequentialRoutedAgent, ABC):
 
    def __init__(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        model_client: ChatCompletionClient,
    ):
        super().__init__(description="Group chat manager")
        self._group_topic_type = group_topic_type
        self._output_topic_type = output_topic_type
        if len(participant_topic_types) != len(participant_descriptions):
            raise ValueError("The number of participant topic types, agent types, and descriptions must be the same.")
        if len(set(participant_topic_types)) != len(participant_topic_types):
            raise ValueError("The participant topic types must be unique.")
        if group_topic_type in participant_topic_types:
            raise ValueError("The group topic type must not be in the participant topic types.")
        self._participant_topic_types = participant_topic_types
        self._participant_descriptions = participant_descriptions
        self._message_thread: List[AgentMessage] = []

        self._name = "orchestrator"
        self._model_client = model_client
        self._task = None
        self._facts = None
        self._plan = None
        self._team_description = "\n".join(
            [
                f"{topic_type}: {description}".strip()
                for topic_type, description in zip(
                    self._participant_topic_types, self._participant_descriptions, strict=True
                )
            ]
        )

    def _get_task_ledger_facts_prompt(self, task: str) -> str:
        return ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT.format(task=task)

    def _get_task_ledger_plan_prompt(self, team: str) -> str:
        return ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT.format(team=team)

    def _get_task_ledger_full_prompt(self, task: str, team: str, facts: str, plan: str) -> str:
        return ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT.format(task=task, team=team, facts=facts, plan=plan)

    def _get_progress_ledger_prompt(self, task: str, team: str, names: List[str]) -> str:
        return ORCHESTRATOR_PROGRESS_LEDGER_PROMPT.format(task=task, team=team, names=", ".join(names))

    @event
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle the start of a group chat by selecting a speaker to start the conversation."""
        assert message is not None

        # Log the start message.
        await self.publish_message(message, topic_id=DefaultTopicId(type=self._output_topic_type))

        # Create the initial task ledger
        ################################# 
        self._task = message.message.content
        planning_conversation = []

        # 1. GATHER FACTS
        # create a closed book task and generate a response and update the chat history
        planning_conversation.append(
            UserMessage(content=self._get_task_ledger_facts_prompt(self._task), source=self._name)
        )
        response = await self._model_client.create(planning_conversation)

        assert isinstance(response.content, str)
        self._facts = response.content
        planning_conversation.append(AssistantMessage(content=self._facts, source=self._name))


        # 2. CREATE A PLAN
        ## plan based on available information
        planning_conversation.append(
            UserMessage(content=self._get_task_ledger_plan_prompt(self._team_description), source=self._name)
        )
        response = await self._model_client.create(planning_conversation)

        assert isinstance(response.content, str)
        self._plan = response.content

        # Kick things off
        await self._reenter_inner_loop()

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        self._message_thread.append(message.agent_response.chat_message)
        await self._orchestrate_step()

    @event
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        # Reset the group chat manager.
        await self.reset()

    async def select_speaker(self, thread: List[AgentMessage]) -> str:
        """Select a speaker from the participants and return the
        topic type of the selected speaker."""
        return ""

    async def reset(self) -> None:
        """Reset the group chat manager."""
        pass

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in group chat manager: {type(message)}")


    async def _reenter_inner_loop(self):
        # TODO: Reset the agents

        # Broadcast the new plan
        ledger_message = TextMessage(
            content=self._get_task_ledger_full_prompt(self._task, self._team_description, self._facts, self._plan),
            source=self._name
        )

        self._message_thread.append(ledger_message) # My copy
        await self.publish_message( # Broadcast
            GroupChatAgentResponse(agent_response=Response(chat_message=ledger_message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )

        # Restart the inner loop
        await self._orchestrate_step()


    async def _orchestrate_step(self) -> None:

        # Update the progress ledger
        context = []
        for m in self._message_thread:
            if m.source == self._name:
                context.append(AssistantMessage(content=m.content, source=m.source))
            else:
                context.append(UserMessage(content=m.content, source=m.source))

        progress_ledger_prompt = self._get_progress_ledger_prompt(self._task, self._team_description, self._participant_topic_types)
        context.append(UserMessage(content=progress_ledger_prompt, source=self._name))

        response = await self._model_client.create(
            context,
            json_output=True
        )

        progress_ledger = json.loads(response.content)

        # Broadcst the next step
        message = TextMessage(
            content=progress_ledger["instruction_or_question"]["answer"],
            source=self._name
        )
        self._message_thread.append(message) # My copy

        # Log it
        await self.publish_message(
            GroupChatMessage(message=message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )

        # Broadcast it
        await self.publish_message( # Broadcast
            GroupChatAgentResponse(agent_response=Response(chat_message=message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )

        # Request that it be completed
        next_speaker = progress_ledger["next_speaker"]["answer"]
        await self.publish_message(GroupChatRequestPublish(), topic_id=DefaultTopicId(type=next_speaker))
