import asyncio

import pytest
from autogen_agentchat.base import TerminatedException
from autogen_agentchat.conditions import (
    ExternalTermination,
    HandoffTermination,
    MaxMessageTermination,
    SourceMatchTermination,
    StopMessageTermination,
    TextMentionTermination,
    TimeoutTermination,
    TokenUsageTermination,
)
from autogen_agentchat.messages import HandoffMessage, StopMessage, TextMessage
from autogen_core.models import RequestUsage


@pytest.mark.asyncio
async def test_handoff_termination() -> None:
    termination = HandoffTermination("target")
    assert await termination([]) is None
    await termination.reset()
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await termination.reset()
    assert await termination([HandoffMessage(target="target", source="user", content="Hello")]) is not None
    assert termination.terminated
    await termination.reset()
    assert await termination([HandoffMessage(target="another", source="user", content="Hello")]) is None
    assert not termination.terminated
    await termination.reset()
    assert (
        await termination(
            [
                TextMessage(content="Hello", source="user"),
                HandoffMessage(target="target", source="user", content="Hello"),
            ]
        )
        is not None
    )
    assert termination.terminated
    await termination.reset()


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


@pytest.mark.asyncio
async def test_timeout_termination() -> None:
    termination = TimeoutTermination(0.1)  # 100ms timeout

    assert await termination([]) is None
    assert not termination.terminated

    await asyncio.sleep(0.2)

    assert await termination([]) is not None
    assert termination.terminated

    await termination.reset()
    assert not termination.terminated
    assert await termination([]) is None

    assert await termination([TextMessage(content="Hello", source="user")]) is None
    await asyncio.sleep(0.2)
    assert await termination([TextMessage(content="World", source="user")]) is not None


@pytest.mark.asyncio
async def test_external_termination() -> None:
    termination = ExternalTermination()

    assert await termination([]) is None
    assert not termination.terminated

    termination.set()
    assert await termination([]) is not None
    assert termination.terminated

    await termination.reset()
    assert await termination([]) is None


@pytest.mark.asyncio
async def test_source_match_termination() -> None:
    termination = SourceMatchTermination(sources=["Assistant"])
    assert await termination([]) is None

    continue_messages = [TextMessage(content="Hello", source="agent"), TextMessage(content="Hello", source="user")]
    assert await termination(continue_messages) is None

    terminate_messages = [
        TextMessage(content="Hello", source="agent"),
        TextMessage(content="Hello", source="Assistant"),
        TextMessage(content="Hello", source="user"),
    ]
    result = await termination(terminate_messages)
    assert isinstance(result, StopMessage)
    assert termination.terminated

    with pytest.raises(TerminatedException):
        await termination([])
    await termination.reset()
    assert not termination.terminated
