from typing import Sequence

from autogen_core.models import AssistantMessage, LLMMessage


def rstrip_last_assistant_message(messages: Sequence[LLMMessage]) -> Sequence[LLMMessage]:
    """
    Remove trailing whitespace from the last assistant message, dropping the
    message entirely if that leaves it empty. Some providers (e.g. Anthropic)
    reject text content blocks that are empty or end in whitespace.

    Only the trailing message is affected; earlier messages in the sequence
    are left untouched even if they are also `AssistantMessage`s.
    """
    if messages and isinstance(messages[-1], AssistantMessage):
        if isinstance(messages[-1].content, str):
            messages[-1].content = messages[-1].content.rstrip()
            if messages[-1].content == "":
                messages = messages[:-1]

    return messages
