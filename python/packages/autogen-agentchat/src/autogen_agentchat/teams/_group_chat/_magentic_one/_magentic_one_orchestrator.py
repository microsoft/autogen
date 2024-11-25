import json
from typing import Any, List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, Image, event, rpc
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    UserMessage,
)

from ....base import Response
from ....messages import (
    AgentMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
)
from .._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatStart,
    GroupChatTermination,
)
from .._sequential_routed_agent import SequentialRoutedAgent
from ._prompts import (
    ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_UPDATE_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
)


class MagenticOneOrchestrator(SequentialRoutedAgent):
    def __init__(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        max_turns: int | None,
        model_client: ChatCompletionClient,
        max_stalls: int,
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

        self._name: str = "orchestrator"
        self._model_client: ChatCompletionClient = model_client
        self._max_turns: int | None = max_turns
        self._max_stalls: int = max_stalls

        self._task: str = ""
        self._facts: str = ""
        self._plan: str = ""
        self._n_rounds: int = 0
        self._n_stalls: int = 0

        self._team_description: str = "\n".join(
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

    def _get_task_ledger_facts_update_prompt(self, task: str, facts: str) -> str:
        return ORCHESTRATOR_TASK_LEDGER_FACTS_UPDATE_PROMPT.format(task=task, facts=facts)

    def _get_task_ledger_plan_update_prompt(self, team: str) -> str:
        return ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT.format(team=team)

    def _get_final_answer_prompt(self, task: str) -> str:
        return ORCHESTRATOR_FINAL_ANSWER_PROMPT.format(task=task)

    @rpc
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle the start of a group chat by selecting a speaker to start the conversation."""
        assert message is not None and message.message is not None

        # Log the start message.
        await self.publish_message(message, topic_id=DefaultTopicId(type=self._output_topic_type))

        # Create the initial task ledger
        #################################
        self._task = self._content_to_str(message.message.content)
        planning_conversation: List[LLMMessage] = []

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
        self._n_stalls = 0
        await self._reenter_inner_loop()

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        self._message_thread.append(message.agent_response.chat_message)
        await self._orchestrate_step()

    @rpc
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

    async def _reenter_inner_loop(self) -> None:
        # Reset the agents
        await self.publish_message(
            GroupChatReset(),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )
        self._message_thread.clear()

        # Prepare the ledger
        ledger_message = TextMessage(
            content=self._get_task_ledger_full_prompt(self._task, self._team_description, self._facts, self._plan),
            source=self._name,
        )

        # Save my copy
        self._message_thread.append(ledger_message)

        # Log it
        await self.publish_message(
            GroupChatMessage(message=ledger_message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )

        # Broadcast
        await self.publish_message(
            GroupChatAgentResponse(agent_response=Response(chat_message=ledger_message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )

        # Restart the inner loop
        await self._orchestrate_step()

    async def _orchestrate_step(self) -> None:
        # Check if we reached the maximum number of rounds
        if self._max_turns is not None and self._n_rounds > self._max_turns:
            await self._prepare_final_answer("Max rounds reached.")
            return
        self._n_rounds += 1

        # Update the progress ledger
        context = self._thread_to_context()

        progress_ledger_prompt = self._get_progress_ledger_prompt(
            self._task, self._team_description, self._participant_topic_types
        )
        context.append(UserMessage(content=progress_ledger_prompt, source=self._name))

        response = await self._model_client.create(context, json_output=True)

        assert isinstance(response.content, str)
        progress_ledger = json.loads(response.content)

        # Check for task completion
        if progress_ledger["is_request_satisfied"]["answer"]:
            await self._prepare_final_answer(progress_ledger["is_request_satisfied"]["reason"])
            return

        # Check for stalling
        if not progress_ledger["is_progress_being_made"]["answer"]:
            self._n_stalls += 1
        elif progress_ledger["is_in_loop"]["answer"]:
            self._n_stalls += 1
        else:
            self._n_stalls = max(0, self._n_stalls - 1)

        # Too much stalling
        if self._n_stalls >= self._max_stalls:
            await self._update_task_ledger()
            await self._reenter_inner_loop()
            return

        # Broadcst the next step
        message = TextMessage(content=progress_ledger["instruction_or_question"]["answer"], source=self._name)
        self._message_thread.append(message)  # My copy

        # Log it
        await self.publish_message(
            GroupChatMessage(message=message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )

        # Broadcast it
        await self.publish_message(  # Broadcast
            GroupChatAgentResponse(agent_response=Response(chat_message=message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )

        # Request that the step be completed
        next_speaker = progress_ledger["next_speaker"]["answer"]
        await self.publish_message(GroupChatRequestPublish(), topic_id=DefaultTopicId(type=next_speaker))

    async def _update_task_ledger(self) -> None:
        context = self._thread_to_context()

        # Update the facts
        update_facts_prompt = self._get_task_ledger_facts_update_prompt(self._task, self._facts)
        context.append(UserMessage(content=update_facts_prompt, source=self._name))

        response = await self._model_client.create(context)

        assert isinstance(response.content, str)
        self._facts = response.content
        context.append(AssistantMessage(content=self._facts, source=self._name))

        # Update the plan
        update_plan_prompt = self._get_task_ledger_plan_update_prompt(self._team_description)
        context.append(UserMessage(content=update_plan_prompt, source=self._name))

        response = await self._model_client.create(context)

        assert isinstance(response.content, str)
        self._plan = response.content

    async def _prepare_final_answer(self, reason: str) -> None:
        context = self._thread_to_context()

        # Get the final answer
        final_answer_prompt = self._get_final_answer_prompt(self._task)
        context.append(UserMessage(content=final_answer_prompt, source=self._name))

        response = await self._model_client.create(context)
        assert isinstance(response.content, str)
        message = TextMessage(content=response.content, source=self._name)

        self._message_thread.append(message)  # My copy

        # Log it
        await self.publish_message(
            GroupChatMessage(message=message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )

        # Broadcast
        await self.publish_message(
            GroupChatAgentResponse(agent_response=Response(chat_message=message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )

        # Signal termination
        await self.publish_message(
            GroupChatTermination(message=StopMessage(content=reason, source=self._name)),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )

    def _thread_to_context(self) -> List[LLMMessage]:
        context: List[LLMMessage] = []
        for m in self._message_thread:
            if m.source == self._name:
                assert isinstance(m, TextMessage)
                context.append(AssistantMessage(content=m.content, source=m.source))
            else:
                assert isinstance(m, TextMessage) or isinstance(m, MultiModalMessage)
                context.append(UserMessage(content=m.content, source=m.source))
        return context

    def _content_to_str(self, content: str | List[str | Image]) -> str:
        if isinstance(content, str):
            return content
        else:
            result: List[str] = []
            for c in content:
                if isinstance(c, str):
                    result.append(c)
                else:
                    result.append("<image>")
        return "\n".join(result)
