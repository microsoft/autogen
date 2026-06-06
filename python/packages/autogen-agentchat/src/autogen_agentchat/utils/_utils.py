from typing import List, Sequence, Union

from autogen_core import FunctionCall, Image
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResult,
    LLMMessage,
    ModelFamily,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel

# Type aliases for convenience
_StructuredContent = BaseModel
_UserContent = Union[str, List[Union[str, Image]]]
_AssistantContent = Union[str, List[FunctionCall]]
_FunctionExecutionContent = List[FunctionExecutionResult]
_SystemContent = str


def content_to_str(
    content: _UserContent | _AssistantContent | _FunctionExecutionContent | _SystemContent | _StructuredContent,
) -> str:
    """Convert the content of an LLMMessage to a string."""
    if isinstance(content, str):
        return content
    elif isinstance(content, BaseModel):
        return content.model_dump_json()
    else:
        result: List[str] = []
        for c in content:
            if isinstance(c, str):
                result.append(c)
            elif isinstance(c, Image):
                result.append("<image>")
            else:
                result.append(str(c))

    return "\n".join(result)


def remove_images(messages: List[LLMMessage]) -> List[LLMMessage]:
    """Remove images from a list of LLMMessages"""
    str_messages: List[LLMMessage] = []
    for message in messages:
        if isinstance(message, UserMessage) and isinstance(message.content, list):
            str_messages.append(UserMessage(content=content_to_str(message.content), source=message.source))
        else:
            str_messages.append(message)
    return str_messages


def _ensure_alternating_roles(
    messages: Sequence[LLMMessage],
    family: str,
) -> List[LLMMessage]:
    """Ensure consecutive messages have alternating user/assistant roles for models that require it.

    For models in the R1 or Mistral families, this function inserts a placeholder
    ``UserMessage(content=".", source="user")`` when two consecutive messages share
    the same conversational role (user or assistant). This satisfies strict
    role-alternation requirements of these model families.

    Args:
        messages: The message sequence to enforce alternating roles on.
        family: The model family string (e.g., ``ModelFamily.R1``).

    Returns:
        A new list of messages with alternating roles enforced. Messages from
        families that do not require alternation are returned as-is.
    """
    # Only apply to R1 and Mistral families.
    if family != ModelFamily.R1 and not ModelFamily.is_mistral(family):
        return list(messages)

    result: List[LLMMessage] = []
    for msg in messages:
        if not result:
            result.append(msg)
            continue
        prev_role = _get_llm_message_role(result[-1])
        curr_role = _get_llm_message_role(msg)
        # Only enforce alternation between user and assistant roles.
        if prev_role in ("user", "assistant") and curr_role in ("user", "assistant") and prev_role == curr_role:
            result.append(UserMessage(content=".", source="user"))
        result.append(msg)
    return result


def _get_llm_message_role(msg: LLMMessage) -> str:
    """Get the logical role of an LLMMessage for alternating role enforcement."""
    if isinstance(msg, SystemMessage):
        return "system"
    elif isinstance(msg, UserMessage):
        return "user"
    elif isinstance(msg, AssistantMessage):
        return "assistant"
    elif isinstance(msg, FunctionExecutionResultMessage):
        return "function"
    else:
        return "other"
