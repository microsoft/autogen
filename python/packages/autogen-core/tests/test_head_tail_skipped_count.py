from typing import List

import pytest

from autogen_core import FunctionCall
from autogen_core.model_context import HeadAndTailChatCompletionContext
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    UserMessage,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("head_size", [1, 2])
@pytest.mark.parametrize("tail_size", [1, 2])
async def test_skipped_count_includes_removed_boundary_messages(head_size: int, tail_size: int) -> None:
    messages: List[LLMMessage] = []
    for i in range(2):
        messages.extend(
            [
                UserMessage(content=f"question {i}", source="user"),
                AssistantMessage(content=[FunctionCall(id=str(i), name="lookup", arguments="{}")], source="assistant"),
                FunctionExecutionResultMessage(
                    content=[FunctionExecutionResult(content="result", name="lookup", call_id=str(i))]
                ),
                AssistantMessage(content=f"answer {i}", source="assistant"),
            ]
        )
    context = HeadAndTailChatCompletionContext(head_size=head_size, tail_size=tail_size, initial_messages=messages)

    result = await context.get_messages()

    # Boundary tool calls/results are omitted, so all four windows retain the same two messages.
    assert result == [
        messages[0],
        UserMessage(content="Skipped 6 messages.", source="System"),
        messages[-1],
    ]
    assert (await context.save_state())["messages"] == [message.model_dump() for message in messages]


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [0, 1, 2])
async def test_short_context_does_not_insert_skipped_placeholder(size: int) -> None:
    messages: List[LLMMessage] = [UserMessage(content=str(i), source="user") for i in range(size)]
    context = HeadAndTailChatCompletionContext(head_size=1, tail_size=1, initial_messages=messages)
    assert await context.get_messages() == messages
