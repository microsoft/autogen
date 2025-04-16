import asyncio
import logging
from typing import Callable, List

from autogen_core import AgentRuntime, Component, ComponentModel
from autogen_core.models import ChatCompletionClient
from pydantic import BaseModel
from typing_extensions import Self

from .... import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from ....base import ChatAgent, TerminationCondition
from ....messages import BaseAgentEvent, BaseChatMessage, MessageFactory
from .._base_group_chat import BaseGroupChat
from .._events import GroupChatTermination
from ._magentic_one_orchestrator import MagenticOneOrchestrator
from ._prompts import ORCHESTRATOR_FINAL_ANSWER_PROMPT

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class MagenticOneGroupChatConfig(BaseModel):
    """The declarative configuration for a MagenticOneGroupChat."""

    participants: List[ComponentModel]
    model_client: ComponentModel
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    max_stalls: int
    final_answer_prompt: str
    emit_team_events: bool = False


class MagenticOneGroupChat(BaseGroupChat, Component[MagenticOneGroupChatConfig]):
    """A team that runs a group chat with participants managed by the MagenticOneOrchestrator.

    The orchestrator handles the conversation flow, ensuring that the task is completed
    efficiently by managing the participants' interactions.

    The orchestrator is based on the Magentic-One architecture, which is a generalist multi-agent system for solving complex tasks (see references below).

    Args:
        participants (List[ChatAgent]): The participants in the group chat.
        model_client (ChatCompletionClient): The model client used for generating responses.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run based on the orchestrator logic or until the maximum number of turns is reached.
        max_turns (int, optional): The maximum number of turns in the group chat before stopping. Defaults to 20.
        max_stalls (int, optional): The maximum number of stalls allowed before re-planning. Defaults to 3.
        final_answer_prompt (str, optional): The LLM prompt used to generate the final answer or response from the team's transcript. A default (sensible for GPT-4o class models) is provided.
        emit_team_events (bool, optional): Whether to emit team events through :meth:`BaseGroupChat.run_stream`. Defaults to False.

    Raises:
        ValueError: In orchestration logic if progress ledger does not have required keys or if next speaker is not valid.

    Examples:

    MagenticOneGroupChat with one assistant agent:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import MagenticOneGroupChat
            from autogen_agentchat.ui import Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                assistant = AssistantAgent(
                    "Assistant",
                    model_client=model_client,
                )
                team = MagenticOneGroupChat([assistant], model_client=model_client)
                await Console(team.run_stream(task="Provide a different proof to Fermat last theorem"))


            asyncio.run(main())

    References:

        If you use the MagenticOneGroupChat in your work, please cite the following paper:

        .. code-block:: bibtex

            @article{fourney2024magentic,
                title={Magentic-one: A generalist multi-agent system for solving complex tasks},
                author={Fourney, Adam and Bansal, Gagan and Mozannar, Hussein and Tan, Cheng and Salinas, Eduardo and Niedtner, Friederike and Proebsting, Grace and Bassman, Griffin and Gerrits, Jack and Alber, Jacob and others},
                journal={arXiv preprint arXiv:2411.04468},
                year={2024}
            }
    """

    component_config_schema = MagenticOneGroupChatConfig
    component_provider_override = "autogen_agentchat.teams.MagenticOneGroupChat"

    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = 20,
        runtime: AgentRuntime | None = None,
        max_stalls: int = 3,
        final_answer_prompt: str = ORCHESTRATOR_FINAL_ANSWER_PROMPT,
        emit_team_events: bool = False,
    ):
        super().__init__(
            participants,
            group_chat_manager_name="MagenticOneOrchestrator",
            group_chat_manager_class=MagenticOneOrchestrator,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            emit_team_events=emit_team_events,
        )

        # Validate the participants.
        if len(participants) == 0:
            raise ValueError("At least one participant is required for MagenticOneGroupChat.")
        self._model_client = model_client
        self._max_stalls = max_stalls
        self._final_answer_prompt = final_answer_prompt

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
    ) -> Callable[[], MagenticOneOrchestrator]:
        return lambda: MagenticOneOrchestrator(
            name,
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_names,
            participant_descriptions,
            max_turns,
            message_factory,
            self._model_client,
            self._max_stalls,
            self._final_answer_prompt,
            output_message_queue,
            termination_condition,
            self._emit_team_events,
        )

    def _to_config(self) -> MagenticOneGroupChatConfig:
        participants = [participant.dump_component() for participant in self._participants]
        termination_condition = self._termination_condition.dump_component() if self._termination_condition else None
        return MagenticOneGroupChatConfig(
            participants=participants,
            model_client=self._model_client.dump_component(),
            termination_condition=termination_condition,
            max_turns=self._max_turns,
            max_stalls=self._max_stalls,
            final_answer_prompt=self._final_answer_prompt,
            emit_team_events=self._emit_team_events,
        )

    @classmethod
    def _from_config(cls, config: MagenticOneGroupChatConfig) -> Self:
        participants = [ChatAgent.load_component(participant) for participant in config.participants]
        model_client = ChatCompletionClient.load_component(config.model_client)
        termination_condition = (
            TerminationCondition.load_component(config.termination_condition) if config.termination_condition else None
        )
        return cls(
            participants,
            model_client,
            termination_condition=termination_condition,
            max_turns=config.max_turns,
            max_stalls=config.max_stalls,
            final_answer_prompt=config.final_answer_prompt,
            emit_team_events=config.emit_team_events,
        )
