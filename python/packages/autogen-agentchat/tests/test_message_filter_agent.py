from typing import Sequence

import pytest
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.agents._message_filter_agent import (
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core import CancellationToken


class _RecordingAgent(BaseChatAgent):
    """Records the exact sequence of messages it receives, for assertions."""

    def __init__(self, name: str) -> None:
        super().__init__(name=name, description="records message order")
        self.received: list[BaseChatMessage] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        self.received = list(messages)
        return Response(chat_message=TextMessage(content="ack", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self.received = []


@pytest.mark.asyncio
async def test_message_filter_agent_preserves_chronological_order() -> None:
    """Regression test: filtered messages from multiple sources must come out in their
    original chronological order, not in the order per_source lists its sources."""
    transcript = [
        TextMessage(content="please solve X", source="user"),
        TextMessage(content="A's first attempt", source="A"),
        TextMessage(content="B's first review", source="B"),
        TextMessage(content="A's second attempt", source="A"),
    ]

    inner = _RecordingAgent("inner")
    agent = MessageFilterAgent(
        name="B",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                # Deliberately listed out of chronological order: "A" is listed before
                # "B" here, even though B's kept message (t2) predates A's kept message (t3).
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="A", position="last", count=1),
                PerSourceFilter(source="B", position="last", count=10),
            ]
        ),
    )

    await agent.on_messages(transcript, CancellationToken())

    assert [m.source for m in inner.received] == ["user", "B", "A"]
    assert [m.content for m in inner.received] == [
        "please solve X",
        "B's first review",
        "A's second attempt",
    ]


@pytest.mark.asyncio
async def test_message_filter_agent_first_and_last_counts_per_source() -> None:
    """Sanity check that first-N/last-N selection within a single source is unaffected
    by the chronological-ordering fix."""
    transcript = [
        TextMessage(content="user msg", source="user"),
        TextMessage(content="A msg 1", source="A"),
        TextMessage(content="A msg 2", source="A"),
        TextMessage(content="A msg 3", source="A"),
    ]

    inner = _RecordingAgent("inner")
    agent = MessageFilterAgent(
        name="wrapper",
        wrapped_agent=inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="A", position="last", count=2),
            ]
        ),
    )

    await agent.on_messages(transcript, CancellationToken())

    assert [m.content for m in inner.received] == ["user msg", "A msg 2", "A msg 3"]
