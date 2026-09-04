import asyncio
from typing import Sequence

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.agents._message_filter_agent import (
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core import CancellationToken


class RecordingAgent(BaseChatAgent):
    def __init__(self, name: str):
        super().__init__(name=name, description="records message order")
        self.received_order: list[str] = []

    @property
    def produced_message_types(self):
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        self.received_order = [f"{m.source}:{m.content}" for m in messages]
        return Response(chat_message=TextMessage(content="ack", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


def test_apply_filter_preserves_chronological_order() -> None:
    """Messages should be returned in their original chronological order,
    regardless of the order sources are listed in per_source."""
    inner = RecordingAgent("B_inner")
    filtered_agent = MessageFilterAgent(
        name="B",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="A", position="last", count=1),
                PerSourceFilter(source="B", position="last", count=10),
            ]
        ),
    )

    transcript = [
        TextMessage(content="please solve X", source="user"),  # t0
        TextMessage(content="A's first attempt", source="A"),  # t1
        TextMessage(content="B's first review", source="B"),  # t2
        TextMessage(content="A's second attempt", source="A"),  # t3
    ]

    asyncio.run(filtered_agent.on_messages(transcript, CancellationToken()))

    # Chronological order: user(t0) -> A(t1) -> B(t2) -> A(t3)
    # Filter keeps: user(first 1), A(last 1 = t3), B(last 10 = t2)
    # Result should be in chronological order: user, B(t2), A(t3)
    assert inner.received_order == [
        "user:please solve X",
        "B:B's first review",
        "A:A's second attempt",
    ]


def test_apply_filter_with_first_position() -> None:
    """Should keep only the first N messages from a source."""
    inner = RecordingAgent("test_inner")
    filtered_agent = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=2),
            ]
        ),
    )

    transcript = [
        TextMessage(content="msg1", source="user"),
        TextMessage(content="msg2", source="assistant"),
        TextMessage(content="msg3", source="user"),
        TextMessage(content="msg4", source="user"),
    ]

    asyncio.run(filtered_agent.on_messages(transcript, CancellationToken()))

    assert inner.received_order == ["user:msg1", "user:msg3"]


def test_apply_filter_with_last_position() -> None:
    """Should keep only the last N messages from a source."""
    inner = RecordingAgent("test_inner")
    filtered_agent = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="assistant", position="last", count=1),
            ]
        ),
    )

    transcript = [
        TextMessage(content="user1", source="user"),
        TextMessage(content="asst1", source="assistant"),
        TextMessage(content="user2", source="user"),
        TextMessage(content="asst2", source="assistant"),
    ]

    asyncio.run(filtered_agent.on_messages(transcript, CancellationToken()))

    assert inner.received_order == ["assistant:asst2"]


def test_apply_filter_with_no_position_keeps_all() -> None:
    """When position is None, all messages from that source should be kept."""
    inner = RecordingAgent("test_inner")
    filtered_agent = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user"),
            ]
        ),
    )

    transcript = [
        TextMessage(content="user1", source="user"),
        TextMessage(content="asst1", source="assistant"),
        TextMessage(content="user2", source="user"),
    ]

    asyncio.run(filtered_agent.on_messages(transcript, CancellationToken()))

    assert inner.received_order == ["user:user1", "user:user2"]


def test_apply_filter_empty_transcript() -> None:
    """Should handle an empty message list gracefully."""
    inner = RecordingAgent("test_inner")
    filtered_agent = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
            ]
        ),
    )

    asyncio.run(filtered_agent.on_messages([], CancellationToken()))

    assert inner.received_order == []
