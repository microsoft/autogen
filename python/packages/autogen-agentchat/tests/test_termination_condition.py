import pytest
from autogen_agentchat.messages import StopMessage, TextMessage
from autogen_agentchat.task import (
    MaxMessageTermination,
    StopMessageTermination,
    TextMentionTermination,
    TokenUsageTermination,
)
from autogen_core.components.models import RequestUsage


@pytest.mark.asyncio
async def test_stop_message_termination() -> None:
    termination = StopMessageTermination()
    assert await termination([]) is None
    await termination.reset()
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await termination.reset()
    assert await termination([StopMessage(content="Stop", source="user")]) is not None
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is None
    )
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), StopMessage(content="Stop", source="user")])
        is not None
    )


@pytest.mark.asyncio
async def test_max_message_termination() -> None:
    termination = MaxMessageTermination(2)
    assert await termination([]) is None
    await termination.reset()
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is not None
    )


@pytest.mark.asyncio
async def test_mention_termination() -> None:
    termination = TextMentionTermination("stop")
    assert await termination([]) is None
    await termination.reset()
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await termination.reset()
    assert await termination([TextMessage(content="stop", source="user")]) is not None
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="stop", source="user")])
        is not None
    )


@pytest.mark.asyncio
async def test_token_usage_termination() -> None:
    termination = TokenUsageTermination(max_total_token=10)
    assert await termination([]) is None
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(
                    content="Hello", source="user", models_usage=RequestUsage(prompt_tokens=10, completion_tokens=10)
                )
            ]
        )
        is not None
    )
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(
                    content="Hello", source="user", models_usage=RequestUsage(prompt_tokens=1, completion_tokens=1)
                ),
                TextMessage(
                    content="World", source="agent", models_usage=RequestUsage(prompt_tokens=1, completion_tokens=1)
                ),
            ]
        )
        is None
    )
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(
                    content="Hello", source="user", models_usage=RequestUsage(prompt_tokens=5, completion_tokens=0)
                ),
                TextMessage(
                    content="stop", source="user", models_usage=RequestUsage(prompt_tokens=0, completion_tokens=5)
                ),
            ]
        )
        is not None
    )


@pytest.mark.asyncio
async def test_and_termination() -> None:
    termination = MaxMessageTermination(2) & TextMentionTermination("stop")
    assert await termination([]) is None
    await termination.reset()
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is None
    )
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="stop", source="user")])
        is not None
    )


@pytest.mark.asyncio
async def test_or_termination() -> None:
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
    assert await termination([]) is None
    await termination.reset()
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is None
    )
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="stop", source="user")])
        is not None
    )
    await termination.reset()
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="Hello", source="user")])
        is None
    )
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(content="Hello", source="user"),
                TextMessage(content="Hello", source="user"),
                TextMessage(content="Hello", source="user"),
            ]
        )
        is not None
    )
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(content="Hello", source="user"),
                TextMessage(content="Hello", source="user"),
                TextMessage(content="stop", source="user"),
            ]
        )
        is not None
    )
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(content="Hello", source="user"),
                TextMessage(content="Hello", source="user"),
                TextMessage(content="Hello", source="user"),
                TextMessage(content="stop", source="user"),
            ]
        )
        is not None
    )
