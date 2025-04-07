from typing import List

from autogen_core.models import LLMMessage
from autogen_core.model_context import (
    SummarizngFunction,
)

def buffered_summary(buffer_count: int) -> SummarizngFunction:
    def _buffered_summary(
        messages: List[LLMMessage],
        non_summarized_messages: List[LLMMessage],
    ) -> str:
        """Summarize the last `buffer_count` messages."""
        if len(messages) > buffer_count:
            return messages[-buffer_count:]
        return messages
    
    return _buffered_summary
