"""Utility functions for working with message threads and contexts."""

from typing import List

from autogen_core.models import (
    AssistantMessage,
    LLMMessage,
    UserMessage,
)

from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    BaseTextChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from autogen_agentchat.utils import remove_images


def thread_to_context(
    messages: List[BaseAgentEvent | BaseChatMessage],
    agent_name: str,
    is_multimodal: bool = False,
) -> List[LLMMessage]:
    """Convert the message thread to a context for the model.

    Args:
        messages: List of messages and events from the chat thread
        agent_name: Name of the agent converting the context
        is_multimodal: Whether to preserve images in multimodal messages

    Returns:
        List of LLM messages suitable for model consumption
    """
    context: List[LLMMessage] = []
    for m in messages:
        if isinstance(m, ToolCallRequestEvent | ToolCallExecutionEvent):
            # Ignore tool call messages.
            continue
        elif isinstance(m, StopMessage | HandoffMessage):
            context.append(UserMessage(content=m.content, source=m.source))
        elif m.source == agent_name:
            assert isinstance(m, TextMessage), f"{type(m)}"
            context.append(AssistantMessage(content=m.content, source=m.source))
        elif m.source == "user_proxy" or m.source == "user":
            assert isinstance(m, TextMessage | MultiModalMessage), f"{type(m)}"
            if isinstance(m.content, str):
                # Simple string content
                context.append(UserMessage(content=m.content, source=m.source))
            else:
                # List content (multimodal)
                context.append(UserMessage(content=m.content, source=m.source))  # type: ignore
        else:
            assert isinstance(m, BaseTextChatMessage) or isinstance(
                m, MultiModalMessage
            ), f"{type(m)}"
            context.append(UserMessage(content=m.content, source=m.source))

    if is_multimodal:
        return context
    else:
        return remove_images(context)
