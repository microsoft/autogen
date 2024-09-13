import asyncio
from dataclasses import dataclass

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentRuntime, MessageContext, TopicId
from autogen_core.components import ClosureAgent
from autogen_core.components._type_subscription import TypeSubscription


@dataclass
class Message:
    content: str


@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    runtime = SingleThreadedAgentRuntime()

    queue = asyncio.Queue[tuple[str, str]]()

    async def log_message(_runtime: AgentRuntime, id: AgentId, message: Message, ctx: MessageContext) -> None:
        key = id.key
        await queue.put((key, message.content))

    await runtime.register("name", lambda: ClosureAgent("my_agent", log_message))
    await runtime.add_subscription(TypeSubscription("default", "name"))
    topic_id = TopicId("default", "default")
    runtime.start()

    await runtime.publish_message(Message("first message"), topic_id=topic_id)
    await runtime.publish_message(Message("second message"), topic_id=topic_id)
    await runtime.publish_message(Message("third message"), topic_id=topic_id)

    await runtime.stop_when_idle()

    assert queue.qsize() == 3
    assert queue.get_nowait() == ("default", "first message")
    assert queue.get_nowait() == ("default", "second message")
    assert queue.get_nowait() == ("default", "third message")
    assert queue.empty()
