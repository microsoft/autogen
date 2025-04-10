from typing import List

from autogen_core.model_context import (
    SummarizedChatCompletionContext,
    SummarizngFunction,
)
from autogen_core.model_context.conditions import MaxMessageCompletion
from autogen_core.models import LLMMessage


def buffered_summary(buffer_count: int) -> SummarizngFunction:
    """Create a buffered summary function.
    This function summarizes the last `buffer_count` messages.
    It is used to create a buffered summarized chat completion context.
    Args:
        buffer_count (int): The size of the buffer.
    Returns:
        SummarizngFunction: The buffered summary function.
    """

    def _buffered_summary(
        messages: List[LLMMessage],
        non_summarized_messages: List[LLMMessage],
    ) -> List[LLMMessage]:
        """Summarize the last `buffer_count` messages."""
        if len(messages) > buffer_count:
            return messages[-buffer_count:]
        return messages

    return _buffered_summary


def buffered_summarized_chat_completion_context(
    buffer_count: int,
    max_messages: int | None = None,
    initial_messages: List[LLMMessage] | None = None,
) -> SummarizedChatCompletionContext:
    """Build a buffered summarized chat completion context.

    Args:
        buffer_count (int): The size of the buffer.
        trigger_count (int | None): The size of the trigger. When is None, the trigger count is set to the buffer count.
        initial_messages (List[LLMMessage] | None): The initial messages.

    Returns:
        SummarizedChatCompletionContext: The buffered summarized chat completion context.
    """

    if max_messages is None:
        max_messages = buffer_count

    return SummarizedChatCompletionContext(
        summarizing_func=buffered_summary(buffer_count),
        summarizing_condition=MaxMessageCompletion(
            max_messages=max_messages,
        ),
        initial_messages=initial_messages,
    )
