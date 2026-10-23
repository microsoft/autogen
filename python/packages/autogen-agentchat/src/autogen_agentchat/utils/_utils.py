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


def _merge_llm_messages(first: LLMMessage, second: LLMMessage) -> LLMMessage:
    """Merge two LLMMessages of the same type into one by concatenating their content.

    Only :py:class:`~autogen_core.models.UserMessage` and
    :py:class:`~autogen_core.models.AssistantMessage` may be merged; callers are
    responsible for ensuring both messages have the same type.

    Args:
        first: The earlier message whose ``source`` is preserved in the merged result.
        second: The later message whose content is appended.

    Returns:
        A new message of the same type with the combined content.
    """
    if isinstance(first, UserMessage) and isinstance(second, UserMessage):
        content1 = content_to_str(first.content) if isinstance(first.content, list) else first.content
        content2 = content_to_str(second.content) if isinstance(second.content, list) else second.content
        return UserMessage(content=f"{content1}\n\n{content2}", source=first.source)

    if isinstance(first, AssistantMessage) and isinstance(second, AssistantMessage):
        if isinstance(first.content, str) and isinstance(second.content, str):
            merged_thought: Union[str, None] = None
            if first.thought and second.thought:
                merged_thought = f"{first.thought}\n\n{second.thought}"
            elif first.thought:
                merged_thought = first.thought
            elif second.thought:
                merged_thought = second.thought
            return AssistantMessage(
                content=f"{first.content}\n\n{second.content}",
                source=first.source,
                thought=merged_thought,
            )
        if isinstance(first.content, list) and isinstance(second.content, list):
            # Both are lists of FunctionCall — concatenate the calls.
            return AssistantMessage(
                content=list(first.content) + list(second.content),
                source=first.source,
                thought=first.thought,
            )
        # Mixed content types (one string, one FunctionCall list) — convert both to str.
        return AssistantMessage(
            content=f"{str(first.content)}\n\n{str(second.content)}",
            source=first.source,
            thought=first.thought,
        )

    # Fallback — should not be reached with well-typed inputs.
    return first


def ensure_alternating_roles(messages: List[LLMMessage]) -> List[LLMMessage]:
    """Normalize a message list so that user and assistant roles strictly alternate.

    Some model APIs (e.g. DeepSeek R1, Mistral) return a ``400`` error when they
    receive consecutive messages with the same role.  This function resolves such
    violations by *merging* consecutive same-role messages into a single message
    whose content is the concatenation of the originals, separated by a blank line.

    :py:class:`~autogen_core.models.SystemMessage` objects are treated as
    transparent: they pass through unchanged and are *not* considered when
    determining role adjacency.

    Args:
        messages: The original message list, which may contain consecutive
            same-role messages.

    Returns:
        A new list where no two consecutive non-system messages share the same
        role.  The input list is not modified.

    Example::

        >>> from autogen_core.models import UserMessage, AssistantMessage
        >>> msgs = [
        ...     UserMessage(content="Hello", source="user"),
        ...     UserMessage(content="World", source="user"),
        ...     AssistantMessage(content="Hi there", source="assistant"),
        ... ]
        >>> result = ensure_alternating_roles(msgs)
        >>> len(result)
        2
        >>> result[0].content
        'Hello\\n\\nWorld'
    """
    if not messages:
        return messages

    result: List[LLMMessage] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            result.append(msg)
            continue

        # Find the last non-system message already in the result list.
        last_non_system: Union[LLMMessage, None] = None
        last_non_system_idx: int = -1
        for idx in range(len(result) - 1, -1, -1):
            if not isinstance(result[idx], SystemMessage):
                last_non_system = result[idx]
                last_non_system_idx = idx
                break

        if last_non_system is None:
            result.append(msg)
        elif type(msg) is type(last_non_system):
            # Same role — merge into the existing entry.
            result[last_non_system_idx] = _merge_llm_messages(last_non_system, msg)
        else:
            result.append(msg)

    return result
