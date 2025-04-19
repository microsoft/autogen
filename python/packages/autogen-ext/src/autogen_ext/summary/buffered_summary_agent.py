from typing import Dict, List, Optional, Union

from autogen_core.model_context.conditions.base import BaseSummaryAgent
from autogen_core.models import ChatCompletionClient, LLMMessage, AssistantMessage
from autogen_core import CancellationToken, ComponentModel

from pydantic import BaseModel


class BufferedSummaryAgentConfig(BaseModel):
    """The declarative configuration for the buffered summary agent agent."""

    name: str
    model_client: ComponentModel
    system_message: str | None = None
    cancellation_token: CancellationToken | None = None
    model_client_stream: bool = False

class BufferedSummaryAgent(BaseSummaryAgent):
    component_config_schema = BufferedSummaryAgentConfig
    component_provider_override = "autogen_ext.summary.BufferedSummaryAgent"
    """A buffered summary agent that summarizes the messages in the context
    using a LLM. 
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        summary_start: int = 0,
        summary_end: int = 0,
        *,
        system_message: str | None = None,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        if system_message is None:            
            summary_prompt="Summarize the conversation so far for your own memory",
            summary_format="This portion of conversation has been summarized as follow: {summary}",
            system_message = f"{summary_prompt}\n{summary_format}"        
        super().__init__(
            name=name,
            model_client=model_client,
            system_message=system_message,
            cancellation_token=cancellation_token,
        )

        self._summary_start = summary_start
        self._summary_end = summary_end

    async def run(
        self,
        task: List[LLMMessage] | None = None,
        original_task: List[LLMMessage] | None = None,
    ) -> List[LLMMessage]:
        """Run the summary agent."""
        if task is None:
            task = []
        if self._summary_start > 0 and self._summary_end < 0:
            task = task[self._summary_start:self._summary_end]
        elif self._summary_start > 0:
            task = task[self._summary_start:]
        elif self._summary_end < 0:
            task = task[:self._summary_end]

        task = self._system_message + task
        task = BaseSummaryAgent._get_compatible_context(
            self._model_client, task
        )

        result = await self._model_client.create(
            messages=task,
            cancellation_token=self._cancellation_token,
        )

        return [AssistantMessage(content=result.content, source="summary")]