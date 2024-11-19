import pytest

from autogen_agentchat.base import TerminatedException
from autogen_agentchat.messages import TextMessage, StopMessage
from autogen_ext.task import SourceMatchTermination


@pytest.mark.asyncio
async def test_agent_name_termination() -> None:
    termination = SourceMatchTermination(sources=["Assistant"])
    assert await termination([]) is None

    continue_messages = [
        TextMessage(content="Hello", source="agent"),
        TextMessage(content="Hello", source="user")
    ]
    assert await termination(continue_messages) is None

    terminate_messages = [
        TextMessage(content="Hello", source="agent"),
        TextMessage(content="Hello", source="Assistant"),
        TextMessage(content="Hello", source="user")
    ]
    result = await termination(terminate_messages)
    assert isinstance(result, StopMessage)
    assert termination.terminated
    with pytest.raises(TerminatedException):
        await termination([])
    await termination.reset()
    assert not termination.terminated
