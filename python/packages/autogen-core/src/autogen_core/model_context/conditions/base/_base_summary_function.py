import logging
from abc import ABC, abstractmethod
from typing import Any, List, Mapping

from pydantic import BaseModel

from .... import EVENT_LOGGER_NAME
from ...._component_config import ComponentBase
from ....models import LLMMessage

logger = logging.getLogger(EVENT_LOGGER_NAME)


class BaseSummaryFunction(ABC, ComponentBase[BaseModel]):
    component_type = "summary_function"

    def __init__(
        self,
        name: str,
    ) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def run(self, messages: List[LLMMessage], non_summary_messages: List[LLMMessage]) -> List[LLMMessage]: ...

    def save_state_json(self) -> Mapping[str, Any]:
        return {}

    def load_state_json(self, state: Mapping[str, Any]) -> None:
        pass
