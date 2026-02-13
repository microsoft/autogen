from typing import List, Union

from autogen_core import FunctionCall, Image
from autogen_core.models import AssistantMessage, FunctionExecutionResult, LLMMessage, SystemMessage, UserMessage
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


def ensure_alternating_roles(messages: List[LLMMessage]) -> List[LLMMessage]:
    """Ensure messages have strictly alternating user-assistant roles.

    Some model APIs (DeepSeek R1, Mistral) require strict alternation between
    user and assistant messages. This function transforms message sequences to
    meet this requirement by merging consecutive messages with the same role.

    Strategy: Merge consecutive messages with the same role into a single message.
    This preserves all content while ensuring alternation.

    Args:
        messages: List of LLMMessages that may have consecutive same-role messages.

    Returns:
        List of LLMMessages with strictly alternating user-assistant roles.
        SystemMessages are preserved at their original positions.

    Example:
        Input:  [User("A"), User("B"), Assistant("C"), Assistant("D")]
        Output: [User("A\\n\\nB"), Assistant("C\\n\\nD")]
    """
    if not messages:
        return messages

    result: List[LLMMessage] = []

    for msg in messages:
        # SystemMessages are passed through without role checking
        if isinstance(msg, SystemMessage):
            result.append(msg)
            continue

        # Get the last non-system message for role comparison
        last_non_system = None
        for prev in reversed(result):
            if not isinstance(prev, SystemMessage):
                last_non_system = prev
                break

        if last_non_system is None:
            # First non-system message, just add it
            result.append(msg)
        elif type(msg) == type(last_non_system):
            # Same role as previous - merge content
            merged = _merge_messages(last_non_system, msg)
            # Replace the last non-system message with merged version
            for i in range(len(result) - 1, -1, -1):
                if not isinstance(result[i], SystemMessage):
                    result[i] = merged
                    break
        else:
            # Different role - just append
            result.append(msg)

    return result


def _merge_messages(msg1: LLMMessage, msg2: LLMMessage) -> LLMMessage:
    """Merge two messages of the same type into one.

    Args:
        msg1: First message.
        msg2: Second message (same type as msg1).

    Returns:
        A new message with combined content.
    """
    if isinstance(msg1, UserMessage) and isinstance(msg2, UserMessage):
        # Combine content with separator
        content1 = content_to_str(msg1.content) if isinstance(msg1.content, list) else msg1.content
        content2 = content_to_str(msg2.content) if isinstance(msg2.content, list) else msg2.content
        merged_content = f"{content1}\n\n{content2}"
        return UserMessage(content=merged_content, source=msg1.source)

    elif isinstance(msg1, AssistantMessage) and isinstance(msg2, AssistantMessage):
        # For AssistantMessage, handle both string content and FunctionCall lists
        if isinstance(msg1.content, str) and isinstance(msg2.content, str):
            merged_content = f"{msg1.content}\n\n{msg2.content}"
            # Merge thoughts if present
            thought = None
            if msg1.thought and msg2.thought:
                thought = f"{msg1.thought}\n\n{msg2.thought}"
            elif msg1.thought:
                thought = msg1.thought
            elif msg2.thought:
                thought = msg2.thought
            return AssistantMessage(content=merged_content, source=msg1.source, thought=thought)
        elif isinstance(msg1.content, list) and isinstance(msg2.content, list):
            # Both are function call lists - combine them
            merged_calls = list(msg1.content) + list(msg2.content)
            return AssistantMessage(content=merged_calls, source=msg1.source, thought=msg1.thought)
        else:
            # Mixed content types - convert to strings and merge
            content1 = str(msg1.content)
            content2 = str(msg2.content)
            return AssistantMessage(content=f"{content1}\n\n{content2}", source=msg1.source, thought=msg1.thought)

    # Fallback: return the first message (shouldn't happen with proper typing)
    return msg1
