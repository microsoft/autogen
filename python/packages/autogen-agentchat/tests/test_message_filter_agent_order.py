"""Tests for MessageFilterAgent chronological ordering preservation.

MessageFilterAgent._apply_filter must preserve the original chronological
order of the input messages regardless of the order sources are listed in
the per_source config. See issue #7971.
"""

import pytest
from autogen_agentchat.agents._message_filter_agent import (
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from autogen_agentchat.messages import TextMessage


class _NoOpAgent:
    """Lightweight callable stand-in that records filtered message order."""

    def __init__(self, name: str = "inner"):
        self.name = name
        self.description = "no-op"
        self.received_order: list[str] = []

    @property
    def produced_message_types(self):
        return (TextMessage,)

    async def on_messages(self, messages, cancellation_token):
        self.received_order = [f"{m.source}:{m.content}" for m in messages]
        # Return a minimal response-like object
        class _Resp:
            chat_message = TextMessage(content="ack", source=self.name)
        return _Resp()

    async def on_reset(self, cancellation_token):
        pass


@pytest.fixture
def chronological_transcript():
    """Transcript matching the documented A->B->A->B->C example from the class
    docstring. Chronological order: user(t0), A(t1), B(t2), A(t3)."""
    return [
        TextMessage(content="please solve X", source="user"),
        TextMessage(content="A first attempt", source="A"),
        TextMessage(content="B first review", source="B"),
        TextMessage(content="A second attempt", source="A"),
    ]


@pytest.mark.asyncio
async def test_preserves_chronological_order(chronological_transcript):
    """The emitted order must be chronological, not config-order."""
    inner = _NoOpAgent()
    filtered = MessageFilterAgent(
        name="B",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[
            PerSourceFilter(source="user", position="first", count=1),
            PerSourceFilter(source="A", position="last", count=1),
            PerSourceFilter(source="B", position="last", count=10),
        ]),
    )

    await filtered.on_messages(chronological_transcript, None)

    assert inner.received_order == [
        "user:please solve X",
        "B:B first review",
        "A:A second attempt",
    ], f"Expected chronological order, got {inner.received_order}"


@pytest.mark.asyncio
async def test_filter_results_are_subset(chronological_transcript):
    """Filtered results must be a subset of the input messages."""
    inner = _NoOpAgent()
    filtered = MessageFilterAgent(
        name="B",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[
            PerSourceFilter(source="user", position="first", count=1),
            PerSourceFilter(source="A", position="last", count=1),
        ]),
    )

    await filtered.on_messages(chronological_transcript, None)

    input_map = {f"{m.source}:{m.content}" for m in chronological_transcript}
    for received in inner.received_order:
        assert received in input_map, f"{received} not in input transcript"


@pytest.mark.asyncio
async def test_single_source_no_reordering():
    """Single-source filter should not change order."""
    transcript = [
        TextMessage(content="m0", source="A"),
        TextMessage(content="m1", source="A"),
        TextMessage(content="m2", source="A"),
        TextMessage(content="m3", source="A"),
    ]
    inner = _NoOpAgent()
    filtered = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[
            PerSourceFilter(source="A", position="last", count=2),
        ]),
    )

    await filtered.on_messages(transcript, None)

    # Should get last 2 messages in chronological order
    assert inner.received_order == ["A:m2", "A:m3"], (
        f"Expected ['A:m2','A:m3'], got {inner.received_order}"
    )


@pytest.mark.asyncio
async def test_unfiltered_source_excluded():
    """Messages from sources not in per_source must be excluded."""
    transcript = [
        TextMessage(content="keep me", source="A"),
        TextMessage(content="drop me", source="Z"),
        TextMessage(content="keep too", source="A"),
    ]
    inner = _NoOpAgent()
    filtered = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[
            PerSourceFilter(source="A"),
        ]),
    )

    await filtered.on_messages(transcript, None)
    assert inner.received_order == ["A:keep me", "A:keep too"]


@pytest.mark.asyncio
async def test_empty_per_source_returns_empty():
    """Empty per_source config must return an empty list."""
    inner = _NoOpAgent()
    filtered = MessageFilterAgent(
        name="test",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[]),
    )

    await filtered.on_messages(
        [TextMessage(content="hi", source="user")], None
    )
    assert inner.received_order == []
