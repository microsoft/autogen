import logging
import re
from typing import Callable, Dict, List, Sequence

from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from .... import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from ....base import ChatAgent, TerminationCondition
from ....messages import (
    AgentMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from .._base_group_chat import BaseGroupChat
from .._base_group_chat_manager import BaseGroupChatManager
from ._ledger_orchestrator_manager import LedgerOrchestratorManager

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class OrchestratorGroupChat(BaseGroupChat):
    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        termination_condition: TerminationCondition | None = None,
    ):
        super().__init__(
            participants, group_chat_manager_class=LedgerOrchestratorManager, termination_condition=termination_condition
        )
        # Validate the participants.
        if len(participants) == 0:
            raise ValueError("At least one participant is required for OrchestratorGroupChat.")
        self._model_client = model_client

    def _create_group_chat_manager_factory(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
    ) -> Callable[[], LedgerOrchestratorManager]:
        # TODO: Do something about the termination conditions
        return lambda: LedgerOrchestratorManager(
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_descriptions,
            self._model_client,
        )
