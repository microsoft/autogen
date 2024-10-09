import pytest
from autogen_agentchat.agents import StopMessage, TextMessage
from autogen_agentchat.teams import MaxMessageTermination, StopMessageTermination, TextMentionTermination


@pytest.mark.asyncio
async def test_stop_message_termination() -> None:
    termination = StopMessageTermination()
    assert await termination([]) is None
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    assert await termination([StopMessage(content="Stop", source="user")]) is not None
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is None
    )
    assert (
        await termination([TextMessage(content="Hello", source="user"), StopMessage(content="Stop", source="user")])
        is not None
    )


@pytest.mark.asyncio
async def test_max_message_termination() -> None:
    termination = MaxMessageTermination(2)
    assert await termination([]) is None
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is not None
    )


@pytest.mark.asyncio
async def test_mention_termination() -> None:
    termination = TextMentionTermination("stop")
    assert await termination([]) is None
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    assert await termination([TextMessage(content="stop", source="user")]) is not None
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="stop", source="user")])
        is not None
    )


@pytest.mark.asyncio
async def test_and_termination() -> None:
    termination = MaxMessageTermination(2) & TextMentionTermination("stop")
    assert await termination([]) is None
    termination = MaxMessageTermination(2) & TextMentionTermination("stop")
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    termination = MaxMessageTermination(2) & TextMentionTermination("stop")
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is not None
    )
    termination = MaxMessageTermination(2) & TextMentionTermination("stop")
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="stop", source="user")])
        is not None
    )


@pytest.mark.asyncio
async def test_or_termination() -> None:
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
    assert await termination([]) is None
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
    assert await termination([TextMessage(content="Hello", source="user")]) is None
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="World", source="agent")])
        is None
    )
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="stop", source="user")])
        is not None
    )
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
    assert (
        await termination([TextMessage(content="Hello", source="user"), TextMessage(content="Hello", source="user")])
        is None
    )
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
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
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
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
    termination = MaxMessageTermination(3) | TextMentionTermination("stop")
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
