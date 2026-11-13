import asyncio
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from autogen_core import (
    AgentId,
    ClosureAgent,
    ClosureContext,
    DefaultSubscription,
    DefaultTopicId,
    MessageContext,
    SingleThreadedAgentRuntime,
)
from autogen_core.exceptions import CantHandleException


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


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["warn", "error", "ignore"])
async def test_any_closure_receives_arbitrary_messages(
    policy: Literal["warn", "error", "ignore"], recwarn: pytest.WarningsRecorder
) -> None:
    runtime = SingleThreadedAgentRuntime()
    received: list[Any] = []

    async def receive(closure_ctx: ClosureContext, message: Any, ctx: MessageContext) -> Any:
        received.append(message)
        return message

    await ClosureAgent.register_closure(
        runtime, "catch_all", receive, unknown_type_policy=policy, subscriptions=lambda: [DefaultSubscription()]
    )
    messages = [Message("dataclass"), "text", 42, {"value": "mapping"}]
    runtime.start()
    try:
        for message in messages:
            assert await runtime.send_message(message, AgentId("catch_all", "default")) is message
        await runtime.publish_message(Message("published"), topic_id=DefaultTopicId())
    finally:
        await runtime.stop_when_idle()

    assert received == [*messages, Message("published")]
    assert not recwarn.list


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["warn", "error"])
async def test_typed_closure_still_rejects_unknown_messages(policy: Literal["warn", "error"]) -> None:
    runtime = SingleThreadedAgentRuntime()
    received: list[Message] = []

    async def receive(closure_ctx: ClosureContext, message: Message, ctx: MessageContext) -> None:
        received.append(message)

    await ClosureAgent.register_closure(runtime, "typed", receive, unknown_type_policy=policy)
    runtime.start()
    try:
        if policy == "warn":
            with pytest.warns(UserWarning, match="Message type"):
                assert await runtime.send_message("not a Message", AgentId("typed", "default")) is None
        else:
            with pytest.raises(CantHandleException):
                await runtime.send_message("not a Message", AgentId("typed", "default"))
    finally:
        await runtime.stop_when_idle()
    assert received == []
