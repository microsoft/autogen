import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Mapping

from autogen_core import AgentId, CancellationToken, DefaultTopicId, MessageContext, event, rpc
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    UserMessage,
)

from .... import TRACE_LOGGER_NAME
from ....base import Response, TerminationCondition
from ....messages import (
    BaseAgentEvent,
    BaseChatMessage,
    HandoffMessage,
    MessageFactory,
    MultiModalMessage,
    SelectSpeakerEvent,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from ....state import MagenticOneOrchestratorState
from ....utils import remove_images
from .._base_group_chat_manager import BaseGroupChatManager
from .._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatStart,
    GroupChatTermination,
)
from ._prompts import (
    ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_UPDATE_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
)

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


class MagenticOneOrchestrator(BaseGroupChatManager):
    """The MagenticOneOrchestrator manages a group chat with ledger based orchestration."""

    def __init__(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        max_turns: int | None,
        message_factory: MessageFactory,
        model_client: ChatCompletionClient,
        max_stalls: int,
        final_answer_prompt: str,
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        emit_team_events: bool,
    ):
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
            emit_team_events=emit_team_events,
        )
        self._model_client = model_client
        self._max_stalls = max_stalls
        self._final_answer_prompt = final_answer_prompt
        self._max_json_retries = 10
        self._task = ""
        self._facts = ""
        self._plan = ""
        self._n_rounds = 0
        self._n_stalls = 0

        # Produce a team description. Each agent sould appear on a single line.
        self._team_description = ""
        for topic_type, description in zip(self._participant_names, self._participant_descriptions, strict=True):
            self._team_description += re.sub(r"\s+", " ", f"{topic_type}: {description}").strip() + "\n"
        self._team_description = self._team_description.strip()

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
        if self._final_answer_prompt == ORCHESTRATOR_FINAL_ANSWER_PROMPT:
            return ORCHESTRATOR_FINAL_ANSWER_PROMPT.format(task=task)
        else:
            return self._final_answer_prompt

    async def _log_message(self, log_message: str) -> None:
        trace_logger.debug(log_message)

    @rpc
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:  # type: ignore
        """Handle the start of a task."""

        # Check if the conversation has already terminated.
        if self._termination_condition is not None and self._termination_condition.terminated:
            early_stop_message = StopMessage(content="The group chat has already terminated.", source=self._name)
            # Signal termination.
            await self._signal_termination(early_stop_message)
            # Stop the group chat.
            return
        assert message is not None and message.messages is not None

        # Validate the group state given all the messages.
        await self.validate_group_state(message.messages)

        # Log the message to the output topic.
        await self.publish_message(message, topic_id=DefaultTopicId(type=self._output_topic_type))
        # Log the message to the output queue.
        for msg in message.messages:
            await self._output_message_queue.put(msg)

        # Outer Loop for first time
        # Create the initial task ledger
        #################################
        # Combine all message contents for task
        self._task = " ".join([msg.to_model_text() for msg in message.messages])
        planning_conversation: List[LLMMessage] = []

        # 1. GATHER FACTS
        # create a closed book task and generate a response and update the chat history
        planning_conversation.append(
            UserMessage(content=self._get_task_ledger_facts_prompt(self._task), source=self._name)
        )
        response = await self._model_client.create(
            self._get_compatible_context(planning_conversation), cancellation_token=ctx.cancellation_token
        )

        assert isinstance(response.content, str)
        self._facts = response.content
        planning_conversation.append(AssistantMessage(content=self._facts, source=self._name))

        # 2. CREATE A PLAN
        ## plan based on available information
        planning_conversation.append(
            UserMessage(content=self._get_task_ledger_plan_prompt(self._team_description), source=self._name)
        )
        response = await self._model_client.create(
            self._get_compatible_context(planning_conversation), cancellation_token=ctx.cancellation_token
        )

        assert isinstance(response.content, str)
        self._plan = response.content

        # Kick things off
        self._n_stalls = 0
        await self._reenter_outer_loop(ctx.cancellation_token)

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:  # type: ignore
        delta: List[BaseAgentEvent | BaseChatMessage] = []
        if message.agent_response.inner_messages is not None:
            for inner_message in message.agent_response.inner_messages:
                delta.append(inner_message)
        await self.update_message_thread([message.agent_response.chat_message])
        delta.append(message.agent_response.chat_message)

        if self._termination_condition is not None:
            stop_message = await self._termination_condition(delta)
            if stop_message is not None:
                # Reset the termination conditions.
                await self._termination_condition.reset()
                # Signal termination.
                await self._signal_termination(stop_message)
                return
        await self._orchestrate_step(ctx.cancellation_token)

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def save_state(self) -> Mapping[str, Any]:
        state = MagenticOneOrchestratorState(
            message_thread=[msg.dump() for msg in self._message_thread],
            current_turn=self._current_turn,
            task=self._task,
            facts=self._facts,
            plan=self._plan,
            n_rounds=self._n_rounds,
            n_stalls=self._n_stalls,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        orchestrator_state = MagenticOneOrchestratorState.model_validate(state)
        self._message_thread = [self._message_factory.create(message) for message in orchestrator_state.message_thread]
        self._current_turn = orchestrator_state.current_turn
        self._task = orchestrator_state.task
        self._facts = orchestrator_state.facts
        self._plan = orchestrator_state.plan
        self._n_rounds = orchestrator_state.n_rounds
        self._n_stalls = orchestrator_state.n_stalls

    async def select_speaker(self, thread: List[BaseAgentEvent | BaseChatMessage]) -> str:
        """Not used in this orchestrator, we select next speaker in _orchestrate_step."""
        return ""

    async def reset(self) -> None:
        """Reset the group chat manager."""
        self._message_thread.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._n_rounds = 0
        self._n_stalls = 0
        self._task = ""
        self._facts = ""
        self._plan = ""

    async def _reenter_outer_loop(self, cancellation_token: CancellationToken) -> None:
        """Re-enter Outer loop of the orchestrator after creating task ledger."""
        # Reset the agents
        for participant_topic_type in self._participant_name_to_topic_type.values():
            await self._runtime.send_message(
                GroupChatReset(),
                recipient=AgentId(type=participant_topic_type, key=self.id.key),
                cancellation_token=cancellation_token,
            )
        # Reset partially the group chat manager
        self._message_thread.clear()

        # Prepare the ledger
        ledger_message = TextMessage(
            content=self._get_task_ledger_full_prompt(self._task, self._team_description, self._facts, self._plan),
            source=self._name,
        )

        # Save my copy
        await self.update_message_thread([ledger_message])

        # Log it to the output topic.
        await self.publish_message(
            GroupChatMessage(message=ledger_message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        # Log it to the output queue.
        await self._output_message_queue.put(ledger_message)

        # Broadcast
        await self.publish_message(
            GroupChatAgentResponse(agent_response=Response(chat_message=ledger_message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
        )

        # Restart the inner loop
        await self._orchestrate_step(cancellation_token=cancellation_token)

    async def _orchestrate_step(self, cancellation_token: CancellationToken) -> None:
        """Implements the inner loop of the orchestrator and selects next speaker."""
        # Check if we reached the maximum number of rounds
        if self._max_turns is not None and self._n_rounds > self._max_turns:
            await self._prepare_final_answer("Max rounds reached.", cancellation_token)
            return
        self._n_rounds += 1

        # Update the progress ledger
        context = self._thread_to_context()

        progress_ledger_prompt = self._get_progress_ledger_prompt(
            self._task, self._team_description, self._participant_names
        )
        context.append(UserMessage(content=progress_ledger_prompt, source=self._name))
        progress_ledger: Dict[str, Any] = {}
        assert self._max_json_retries > 0
        key_error: bool = False
        for _ in range(self._max_json_retries):
            response = await self._model_client.create(self._get_compatible_context(context), json_output=True)
            ledger_str = response.content
            try:
                assert isinstance(ledger_str, str)
                progress_ledger = json.loads(ledger_str)

                # If the team consists of a single agent, deterministically set the next speaker
                if len(self._participant_names) == 1:
                    progress_ledger["next_speaker"] = {
                        "reason": "The team consists of only one agent.",
                        "answer": self._participant_names[0],
                    }

                # Validate the structure
                required_keys = [
                    "is_request_satisfied",
                    "is_progress_being_made",
                    "is_in_loop",
                    "instruction_or_question",
                    "next_speaker",
                ]

                key_error = False
                for key in required_keys:
                    if (
                        key not in progress_ledger
                        or not isinstance(progress_ledger[key], dict)
                        or "answer" not in progress_ledger[key]
                        or "reason" not in progress_ledger[key]
                    ):
                        key_error = True
                        break

                # Validate the next speaker if the task is not yet complete
                if (
                    not progress_ledger["is_request_satisfied"]["answer"]
                    and progress_ledger["next_speaker"]["answer"] not in self._participant_names
                ):
                    key_error = True
                    break

                if not key_error:
                    break
                await self._log_message(f"Failed to parse ledger information, retrying: {ledger_str}")
            except (json.JSONDecodeError, TypeError):
                key_error = True
                await self._log_message("Invalid ledger format encountered, retrying...")
                continue
        if key_error:
            raise ValueError("Failed to parse ledger information after multiple retries.")
        await self._log_message(f"Progress Ledger: {progress_ledger}")

        # Check for task completion
        if progress_ledger["is_request_satisfied"]["answer"]:
            await self._log_message("Task completed, preparing final answer...")
            await self._prepare_final_answer(progress_ledger["is_request_satisfied"]["reason"], cancellation_token)
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
            await self._log_message("Stall count exceeded, re-planning with the outer loop...")
            await self._update_task_ledger(cancellation_token)
            await self._reenter_outer_loop(cancellation_token)
            return

        # Broadcast the next step
        message = TextMessage(content=progress_ledger["instruction_or_question"]["answer"], source=self._name)
        await self.update_message_thread([message])  # My copy

        await self._log_message(f"Next Speaker: {progress_ledger['next_speaker']['answer']}")
        # Log it to the output topic.
        await self.publish_message(
            GroupChatMessage(message=message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        # Log it to the output queue.
        await self._output_message_queue.put(message)

        # Broadcast it
        await self.publish_message(  # Broadcast
            GroupChatAgentResponse(agent_response=Response(chat_message=message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
            cancellation_token=cancellation_token,
        )

        # Request that the step be completed
        next_speaker = progress_ledger["next_speaker"]["answer"]
        # Check if the next speaker is valid
        if next_speaker not in self._participant_name_to_topic_type:
            raise ValueError(
                f"Invalid next speaker: {next_speaker} from the ledger, participants are: {self._participant_names}"
            )
        participant_topic_type = self._participant_name_to_topic_type[next_speaker]
        await self.publish_message(
            GroupChatRequestPublish(),
            topic_id=DefaultTopicId(type=participant_topic_type),
            cancellation_token=cancellation_token,
        )

        # Send the message to the next speaker
        if self._emit_team_events:
            select_msg = SelectSpeakerEvent(content=[next_speaker], source=self._name)
            await self.publish_message(
                GroupChatMessage(message=select_msg),
                topic_id=DefaultTopicId(type=self._output_topic_type),
            )
            await self._output_message_queue.put(select_msg)

    async def _update_task_ledger(self, cancellation_token: CancellationToken) -> None:
        """Update the task ledger (outer loop) with the latest facts and plan."""
        context = self._thread_to_context()

        # Update the facts
        update_facts_prompt = self._get_task_ledger_facts_update_prompt(self._task, self._facts)
        context.append(UserMessage(content=update_facts_prompt, source=self._name))

        response = await self._model_client.create(
            self._get_compatible_context(context), cancellation_token=cancellation_token
        )

        assert isinstance(response.content, str)
        self._facts = response.content
        context.append(AssistantMessage(content=self._facts, source=self._name))

        # Update the plan
        update_plan_prompt = self._get_task_ledger_plan_update_prompt(self._team_description)
        context.append(UserMessage(content=update_plan_prompt, source=self._name))

        response = await self._model_client.create(
            self._get_compatible_context(context), cancellation_token=cancellation_token
        )

        assert isinstance(response.content, str)
        self._plan = response.content

    async def _prepare_final_answer(self, reason: str, cancellation_token: CancellationToken) -> None:
        """Prepare the final answer for the task."""
        context = self._thread_to_context()

        # Get the final answer
        final_answer_prompt = self._get_final_answer_prompt(self._task)
        context.append(UserMessage(content=final_answer_prompt, source=self._name))

        response = await self._model_client.create(
            self._get_compatible_context(context), cancellation_token=cancellation_token
        )
        assert isinstance(response.content, str)
        message = TextMessage(content=response.content, source=self._name)

        await self.update_message_thread([message])  # My copy

        # Log it to the output topic.
        await self.publish_message(
            GroupChatMessage(message=message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        # Log it to the output queue.
        await self._output_message_queue.put(message)

        # Broadcast
        await self.publish_message(
            GroupChatAgentResponse(agent_response=Response(chat_message=message)),
            topic_id=DefaultTopicId(type=self._group_topic_type),
            cancellation_token=cancellation_token,
        )

        if self._termination_condition is not None:
            await self._termination_condition.reset()
        # Signal termination
        await self._signal_termination(StopMessage(content=reason, source=self._name))

    def _thread_to_context(self) -> List[LLMMessage]:
        """Convert the message thread to a context for the model."""
        context: List[LLMMessage] = []
        for m in self._message_thread:
            if isinstance(m, ToolCallRequestEvent | ToolCallExecutionEvent):
                # Ignore tool call messages.
                continue
            elif isinstance(m, StopMessage | HandoffMessage):
                context.append(UserMessage(content=m.content, source=m.source))
            elif m.source == self._name:
                assert isinstance(m, TextMessage | ToolCallSummaryMessage)
                context.append(AssistantMessage(content=m.content, source=m.source))
            else:
                assert isinstance(m, (TextMessage, MultiModalMessage, ToolCallSummaryMessage))
                context.append(UserMessage(content=m.content, source=m.source))
        return context

    def _get_compatible_context(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        """Ensure that the messages are compatible with the underlying client, by removing images if needed."""
        if self._model_client.model_info["vision"]:
            return messages
        else:
            return remove_images(messages)
