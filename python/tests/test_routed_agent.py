from dataclasses import dataclass
import pytest
import logging

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeSubscription
from agnext.base import TopicId

from test_utils import LoopbackAgent


@dataclass
class UnhandledMessageType: ...


@pytest.mark.asyncio
async def test_routed_agent(caplog: pytest.LogCaptureFixture) -> None:
    runtime = SingleThreadedAgentRuntime()
    with caplog.at_level(logging.INFO):
        await runtime.register("loopback", lambda: LoopbackAgent(), lambda: [TypeSubscription("default", "loopback")])
        runtime.start()
        await runtime.publish_message(UnhandledMessageType(), topic_id=TopicId("default", "default"))
        await runtime.stop_when_idle()
    assert any("Unhandled message: " in e.message for e in caplog.records)
