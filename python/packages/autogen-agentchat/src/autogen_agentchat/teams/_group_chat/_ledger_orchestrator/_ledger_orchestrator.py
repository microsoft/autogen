import logging
from typing import Callable, List

from autogen_core.components.models import ChatCompletionClient

from .... import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from ....base import ChatAgent, TerminationCondition
from .._base_group_chat import BaseGroupChat
from ._ledger_orchestrator_manager import LedgerOrchestratorManager

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class OrchestratorGroupChat(BaseGroupChat):
    def __init__(
        self,
        participants: List[ChatAgent],
        model_client: ChatCompletionClient,
        *,
        max_rounds: int = 20,
        max_stalls: int = 3,
    ):
        super().__init__(
            participants,
            group_chat_manager_class=LedgerOrchestratorManager,
            termination_condition=None,
        )
        # Validate the participants.
        if len(participants) == 0:
            raise ValueError("At least one participant is required for OrchestratorGroupChat.")
        self._model_client = model_client
        self._max_rounds = max_rounds
        self._max_stalls = max_stalls

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
            self._max_rounds,
            self._max_stalls,
        )
