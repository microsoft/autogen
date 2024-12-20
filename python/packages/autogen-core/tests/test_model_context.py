from typing import List

import pytest
from autogen_core.model_context import (
    BufferedChatCompletionContext,
    HeadAndTailChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_core.models import AssistantMessage, LLMMessage, UserMessage


@pytest.mark.asyncio
async def test_buffered_model_context() -> None:
    model_context = BufferedChatCompletionContext(buffer_size=2)
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    await model_context.add_message(messages[0])
    await model_context.add_message(messages[1])
    await model_context.add_message(messages[2])

    retrieved = await model_context.get_messages()
    assert len(retrieved) == 2
    assert retrieved[0] == messages[1]
    assert retrieved[1] == messages[2]

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    await model_context.add_message(messages[0])
    await model_context.add_message(messages[1])
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 2
    assert retrieved[0] == messages[0]
    assert retrieved[1] == messages[1]


@pytest.mark.asyncio
async def test_head_and_tail_model_context() -> None:
    model_context = HeadAndTailChatCompletionContext(head_size=1, tail_size=1)
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
        AssistantMessage(content="Pike place, space needle, mt rainer", source="assistant"),
        UserMessage(content="More places?", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrived = await model_context.get_messages()
    assert len(retrived) == 3  # 1 head, 1 tail + 1 placeholder.
    assert retrived[0] == messages[0]
    assert retrived[2] == messages[-1]

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    for msg in messages:
        await model_context.add_message(msg)
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrived = await model_context.get_messages()
    assert len(retrived) == 3
    assert retrived[0] == messages[0]
    assert retrived[2] == messages[-1]


@pytest.mark.asyncio
async def test_unbounded_model_context() -> None:
    model_context = UnboundedChatCompletionContext()
    messages: List[LLMMessage] = [
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="What can I do for you?", source="assistant"),
        UserMessage(content="Tell what are some fun things to do in seattle.", source="user"),
    ]
    for msg in messages:
        await model_context.add_message(msg)

    retrieved = await model_context.get_messages()
    assert len(retrieved) == 3
    assert retrieved == messages

    await model_context.clear()
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 0

    # Test saving and loading state.
    for msg in messages:
        await model_context.add_message(msg)
    state = await model_context.save_state()
    await model_context.clear()
    await model_context.load_state(state)
    retrieved = await model_context.get_messages()
    assert len(retrieved) == 3
    assert retrieved == messages
