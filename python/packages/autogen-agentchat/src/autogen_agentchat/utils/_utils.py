from typing import List, Sequence, Union

from autogen_core import FunctionCall, Image
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
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


def _get_role(message: LLMMessage) -> str:
    """Get the effective role of a message for alternation checking."""
    if isinstance(message, SystemMessage):
        return "system"
    elif isinstance(message, UserMessage):
        return "user"
    elif isinstance(message, AssistantMessage):
        return "assistant"
    elif isinstance(message, FunctionExecutionResultMessage):
        # Function results are treated as user-role messages by most APIs
        return "user"
    return "unknown"


def _merge_user_contents(contents: List[str]) -> str:
    """Merge multiple user message contents into a single string."""
    return "\n".join(c for c in contents if c)


def _merge_assistant_contents(contents: List[str]) -> str:
    """Merge multiple assistant message contents into a single string."""
    return "\n".join(c for c in contents if c)


def ensure_alternating_roles(messages: Sequence[LLMMessage]) -> List[LLMMessage]:
    """Ensure messages follow strict alternating user-assistant roles.

    This is required by certain model APIs (e.g., DeepSeek R1, Mistral) that reject
    requests with consecutive messages of the same role.

    The strategy is:
    1. Preserve leading system messages as-is.
    2. For consecutive user-role messages (UserMessage or FunctionExecutionResultMessage),
       merge their text content into a single UserMessage.
    3. For consecutive assistant messages, merge their text content into a single
       AssistantMessage.
    4. If FunctionExecutionResultMessage contains tool results (non-text), insert an
       empty assistant message before it to maintain alternation when needed.
    5. Between two assistant messages, inject an empty user message.
    6. Between two user messages, inject an empty assistant message.

    Args:
        messages: The original message sequence.

    Returns:
        A new list of messages with strict alternating user-assistant roles.
    """
    if not messages:
        return []

    result: List[LLMMessage] = []

    # Preserve leading system messages
    idx = 0
    while idx < len(messages) and isinstance(messages[idx], SystemMessage):
        result.append(messages[idx])
        idx += 1

    if idx >= len(messages):
        return result

    # Process remaining messages, enforcing alternation
    for i in range(idx, len(messages)):
        msg = messages[i]
        role = _get_role(msg)

        if role == "system":
            # Convert non-leading system messages to user messages
            result.append(UserMessage(content=msg.content, source="system"))  # type: ignore
            continue

        if not result or _get_role(result[-1]) == "system":
            # First non-system message, just add it
            result.append(msg)
            continue

        prev_role = _get_role(result[-1])

        if role == prev_role:
            # Same role as previous -- merge content
            if role == "user":
                prev_msg = result[-1]
                if isinstance(prev_msg, UserMessage) and isinstance(msg, UserMessage):
                    prev_content = content_to_str(prev_msg.content)
                    curr_content = content_to_str(msg.content)
                    merged = _merge_user_contents([prev_content, curr_content])
                    result[-1] = UserMessage(content=merged, source=prev_msg.source)
                elif isinstance(prev_msg, UserMessage) and isinstance(msg, FunctionExecutionResultMessage):
                    # Merge function result text into the previous user message
                    prev_content = content_to_str(prev_msg.content)
                    func_content = "\n".join(r.content for r in msg.content)
                    merged = _merge_user_contents([prev_content, func_content])
                    result[-1] = UserMessage(content=merged, source=prev_msg.source)
                elif isinstance(prev_msg, FunctionExecutionResultMessage) and isinstance(msg, UserMessage):
                    # Convert previous to UserMessage and merge
                    prev_content = "\n".join(r.content for r in prev_msg.content)
                    curr_content = content_to_str(msg.content)
                    merged = _merge_user_contents([prev_content, curr_content])
                    result[-1] = UserMessage(content=merged, source=msg.source)
                elif isinstance(prev_msg, FunctionExecutionResultMessage) and isinstance(
                    msg, FunctionExecutionResultMessage
                ):
                    # Merge two function result messages
                    result[-1] = FunctionExecutionResultMessage(
                        content=list(prev_msg.content) + list(msg.content)
                    )
                else:
                    # Fallback: inject an assistant message to break the sequence
                    result.append(AssistantMessage(content="", source="system"))
                    result.append(msg)
            elif role == "assistant":
                prev_msg = result[-1]
                if isinstance(prev_msg, AssistantMessage) and isinstance(msg, AssistantMessage):
                    prev_content = content_to_str(prev_msg.content)
                    curr_content = content_to_str(msg.content)
                    merged = _merge_assistant_contents([prev_content, curr_content])
                    # Merge thoughts if present
                    thoughts = [t for t in [prev_msg.thought, msg.thought] if t]
                    merged_thought = "\n".join(thoughts) if thoughts else None
                    result[-1] = AssistantMessage(
                        content=merged, source=prev_msg.source, thought=merged_thought
                    )
                else:
                    # Fallback: inject a user message to break the sequence
                    result.append(UserMessage(content="", source="system"))
                    result.append(msg)
            else:
                # Unknown same-role situation, inject opposite role
                result.append(UserMessage(content="", source="system"))
                result.append(msg)
        elif role == "user" and prev_role == "assistant":
            # Correct alternation
            result.append(msg)
        elif role == "assistant" and prev_role == "user":
            # Correct alternation
            result.append(msg)
        else:
            # Any other transition, just append
            result.append(msg)

    return result
