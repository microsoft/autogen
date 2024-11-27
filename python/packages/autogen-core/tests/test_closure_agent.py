import asyncio
from dataclasses import dataclass

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import MessageContext
from autogen_core.components import ClosureAgent, ClosureContext, DefaultSubscription, DefaultTopicId


@dataclass
class Message:
    content: str


@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    runtime = SingleThreadedAgentRuntime()

    queue = asyncio.Queue[tuple[str, str]]()

    async def log_message(closure_ctx: ClosureContext, message: Message, ctx: MessageContext) -> None:
        key = closure_ctx.id.key
        await queue.put((key, message.content))

    await ClosureAgent.register_closure(runtime, "name", log_message, subscriptions=lambda: [DefaultSubscription()])
    runtime.start()

    await runtime.publish_message(Message("first message"), topic_id=DefaultTopicId())
    await runtime.publish_message(Message("second message"), topic_id=DefaultTopicId())
    await runtime.publish_message(Message("third message"), topic_id=DefaultTopicId())

    await runtime.stop_when_idle()

    assert queue.qsize() == 3
    assert queue.get_nowait() == ("default", "first message")
    assert queue.get_nowait() == ("default", "second message")
    assert queue.get_nowait() == ("default", "third message")
    assert queue.empty()
