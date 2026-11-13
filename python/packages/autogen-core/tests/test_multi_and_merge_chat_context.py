import pytest
from typing import List
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
    MultiChatCompletionContext,
    MergeSystemChatCompletionContext,
    TokenLimitedChatCompletionContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResultMessage,
    LLMMessage,
    UserMessage,
    SystemMessage
)

@pytest.mark.asyncio
async def test_multi_chat_completion_context_combines_contexts():
    ctx1 = UnboundedChatCompletionContext()
    ctx2 = TokenLimitedChatCompletionContext(20)

    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]

    multi_ctx = MultiChatCompletionContext([ctx1, ctx2])

    messages = await multi_ctx.get_messages()
    assert len(messages) == 2
    assert messages[0].content == "Hello!"
    assert messages[1].content == "What can I do for you?"


@pytest.mark.asyncio
async def test_merge_system_chat_completion_context_merges_system_messages():
    merge_ctx = MergeSystemChatCompletionContext()
    messages = [
        SystemMessage(content="Rule 1: Be polite."),
        SystemMessage(content="Rule 2: Respond clearly."),
        UserMessage(content="What’s your name?", source="user"),
    ]

    for msg in messages:
        await merge_ctx.add_message(msg)

    merged = await merge_ctx.get_messages()

    assert len(merged) == 2
    assert isinstance(merged[0], SystemMessage)
    assert "Rule 1" in merged[0].content and "Rule 2" in merged[0].content

    # The user message should still be present
    assert isinstance(merged[1], UserMessage)
    assert merged[1].content == "What’s your name?"
