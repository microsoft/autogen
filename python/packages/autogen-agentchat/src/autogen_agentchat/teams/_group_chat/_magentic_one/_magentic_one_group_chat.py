import logging
from typing import Callable, List

from autogen_core.components.models import ChatCompletionClient

from .... import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from ....base import ChatAgent, TerminationCondition
from .._base_group_chat import BaseGroupChat
from ._magentic_one_orchestrator import MagenticOneOrchestrator
from ._prompts import ORCHESTRATOR_FINAL_ANSWER_PROMPT

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class MagenticOneGroupChat(BaseGroupChat):
    """A team that runs a group chat with participants managed by the MagenticOneOrchestrator.

    The orchestrator handles the conversation flow, ensuring that the task is completed
    efficiently by managing the participants' interactions.

    Args:
        participants (List[ChatAgent]): The participants in the group chat.
        model_client (ChatCompletionClient): The model client used for generating responses.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run based on the orchestrator logic or until the maximum number of turns is reached.
        max_turns (int, optional): The maximum number of turns in the group chat before stopping. Defaults to 20.
        max_stalls (int, optional): The maximum number of stalls allowed before re-planning. Defaults to 3.
        final_answer_prompt (str, optional): The LLM prompt used to generate the final answer or response from the team's transcript. A default (sensible for GPT-4o class models) is provided.

    Raises:
        ValueError: In orchestration logic if progress ledger does not have required keys or if next speaker is not valid.

    Examples:

    MagenticOneGroupChat with one assistant agent:

        .. code-block:: python

            import asyncio
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import MagenticOneGroupChat
            from autogen_agentchat.task import Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                assistant = AssistantAgent(
                    "Assistant",
                    model_client=model_client,
                )
                team = MagenticOneGroupChat([assistant], model_client=model_client)
                await Console(team.run_stream(task="Provide a different proof to Fermat last theorem"))


            asyncio.run(main())
    """

    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = 20,
        max_stalls: int = 3,
        final_answer_prompt: str = ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ):
        super().__init__(
            participants,
            group_chat_manager_class=MagenticOneOrchestrator,
            termination_condition=termination_condition,
            max_turns=max_turns,
        )

        # Validate the participants.
        if len(participants) == 0:
            raise ValueError("At least one participant is required for MagenticOneGroupChat.")
        self._model_client = model_client
        self._max_stalls = max_stalls
        self._final_answer_prompt = final_answer_prompt

    def _create_group_chat_manager_factory(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
    ) -> Callable[[], MagenticOneOrchestrator]:
        return lambda: MagenticOneOrchestrator(
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_descriptions,
            max_turns,
            self._model_client,
            self._max_stalls,
            self._final_answer_prompt,
            termination_condition,
        )
