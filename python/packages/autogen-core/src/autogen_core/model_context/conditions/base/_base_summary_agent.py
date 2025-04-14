from abc import ABC, abstractmethod
from typing import List, Sequence
from pydantic import BaseModel

from autogen_core.models import ChatCompletionClient
from autogen_core import ComponentBase, CancellationToken
from ....models import LLMMessage, SystemMessage
from autogen_agentchat.utils import remove_images

class BaseSummaryAgent(ABC, ComponentBase[BaseModel]):
    """
    Base class for summary agents.
    """

    component_type = "summary_agent"

    def __init__(
            self,
            name: str,
            model_client: ChatCompletionClient,
            cancellation_token: CancellationToken | None = None,
            *,
            system_message: str,
        ):
        self._name = name
        self._model_client = model_client
        self._system_message = [SystemMessage(content=system_message)]
        self._cancellation_token = cancellation_token


    @property
    def name(self) -> str:
        """The name of the agent."""
        return self._name

    @abstractmethod
    def run(
        self,
        task: List[LLMMessage] | None = None,
        original_task: List[LLMMessage] | None = None,
    ) -> List[LLMMessage]:
        """
        Run the summary agent.
        Args:
            task: The task to run.
            original_task: The original task to run.
        Returns:
            The result of the run.
        """
        ...

    @staticmethod
    def _get_compatible_context(model_client: ChatCompletionClient, messages: List[LLMMessage]) -> Sequence[LLMMessage]:
        """Ensure that the messages are compatible with the underlying client, by removing images if needed."""
        if model_client.model_info["vision"]:
            return messages
        else:
            return remove_images(messages)