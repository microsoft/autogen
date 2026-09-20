"""Ordering tests for MessageFilterAgent._apply_filter.

Covers the chronological-ordering fix for
https://github.com/microsoft/autogen/issues/7971: _apply_filter used to emit
messages grouped by filter in per_source config order instead of the order the
messages appear in the input sequence. The fix re-sorts the collected messages
on their original positions, using an identity-keyed index map so that
value-identical duplicate messages keep their true positions.

Test style mirrors tests/test_group_chat_graph.py: an echo agent records the
messages the wrapped agent actually receives, which is the observable effect
of the bug.
"""

from typing import Sequence

import pytest
from autogen_agentchat.agents import (
    BaseChatAgent,
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core import CancellationToken, Component
from pydantic import BaseModel


class _EchoAgentConfig(BaseModel):
    name: str
    description: str = "Echo test agent"


class _EchoAgent(BaseChatAgent, Component[_EchoAgentConfig]):
    component_config_schema = _EchoAgentConfig
    component_provider_override = "test_message_filter_agent_order._EchoAgent"

    def __init__(self, name: str, description: str = "Echo test agent") -> None:
        super().__init__(name=name, description=description)
        self.received_messages: list[BaseChatMessage] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        self.received_messages.extend(messages)
        return Response(chat_message=TextMessage(content="ACK", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self.received_messages.clear()

    def _to_config(self) -> _EchoAgentConfig:
        return _EchoAgentConfig(name=self.name, description=self.description)

    @classmethod
    def _from_config(cls, config: _EchoAgentConfig) -> "_EchoAgent":
        return cls(name=config.name, description=config.description)


async def _filtered_messages(
    messages: Sequence[BaseChatMessage], per_source: list[PerSourceFilter]
) -> list[BaseChatMessage]:
    inner = _EchoAgent("inner")
    wrapper = MessageFilterAgent(
        name="wrapper",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=per_source),
    )
    await wrapper.on_messages(messages, CancellationToken())
    return list(inner.received_messages)


def _contents(messages: Sequence[BaseChatMessage]) -> list[str]:
    return [m.content for m in messages]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_documented_loop_example_is_chronological() -> None:
    """The A -> B -> A -> B -> C example from issue #7971.

    With per_source=[user-first(1), A-last(1), B-last(N)] (B's config from the
    class docstring) and history [user, A(older), B(own), A(newer)], the old
    code emitted [user, A(newer), B(own)] -- config order. The wrapped agent
    must instead see the chronological selection [user, B(own), A(newer)].
    """
    messages = [
        TextMessage(source="user", content="task"),
        TextMessage(source="A", content="draft v1"),
        TextMessage(source="B", content="reviewing"),
        TextMessage(source="A", content="draft v2"),
    ]
    filtered = await _filtered_messages(
        messages,
        per_source=[
            PerSourceFilter(source="user", position="first", count=1),
            PerSourceFilter(source="A", position="last", count=1),
            PerSourceFilter(source="B", position="last", count=10),
        ],
    )
    assert _contents(filtered) == ["task", "reviewing", "draft v2"]


@pytest.mark.asyncio
async def test_subset_preserved_in_chronological_order() -> None:
    """Window selection still drops messages, but survivors keep timeline order."""
    messages = [
        TextMessage(source="A", content="a1"),
        TextMessage(source="B", content="b1"),
        TextMessage(source="A", content="a2"),
        TextMessage(source="B", content="b2"),
    ]
    filtered = await _filtered_messages(
        messages,
        per_source=[
            PerSourceFilter(source="B", position="last", count=2),
            PerSourceFilter(source="A", position="last", count=1),
        ],
    )
    assert _contents(filtered) == ["b1", "a2", "b2"]


@pytest.mark.asyncio
async def test_single_source_filter_keeps_original_order() -> None:
    """With one filter the re-sort is a no-op: output order matches input order."""
    messages = [
        TextMessage(source="A", content="a1"),
        TextMessage(source="A", content="a2"),
        TextMessage(source="A", content="a3"),
    ]
    filtered = await _filtered_messages(
        messages,
        per_source=[PerSourceFilter(source="A", position="last", count=2)],
    )
    assert _contents(filtered) == ["a2", "a3"]


@pytest.mark.asyncio
async def test_unfiltered_sources_are_excluded() -> None:
    """Sources with no entry in per_source are still dropped entirely."""
    messages = [
        TextMessage(source="user", content="hello"),
        TextMessage(source="system", content="sys"),
        TextMessage(source="A", content="other"),
    ]
    filtered = await _filtered_messages(
        messages,
        per_source=[PerSourceFilter(source="user", position="first", count=1)],
    )
    assert _contents(filtered) == ["hello"]


@pytest.mark.asyncio
async def test_empty_per_source_config_yields_no_messages() -> None:
    inner = _EchoAgent("inner")
    wrapper = MessageFilterAgent(
        name="wrapper",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[]),
    )
    messages = [
        TextMessage(source="user", content="hello"),
        TextMessage(source="A", content="other"),
    ]
    await wrapper.on_messages(messages, CancellationToken())
    assert inner.received_messages == []


@pytest.mark.asyncio
async def test_first_n_selects_earliest_message() -> None:
    """first(N) windows pick the earliest messages, and the output is still
    chronological even when the filters are listed in a different order."""
    messages = [
        TextMessage(source="user", content="u1"),
        TextMessage(source="A", content="a1"),
        TextMessage(source="B", content="b1"),
        TextMessage(source="A", content="a2"),
    ]
    filtered = await _filtered_messages(
        messages,
        per_source=[
            PerSourceFilter(source="B", position="last", count=1),
            PerSourceFilter(source="A", position="first", count=1),
            PerSourceFilter(source="user", position="first", count=1),
        ],
    )
    # a1 (not a2) proves first(1) semantics; [u1, a1, b1] proves the re-sort.
    assert _contents(filtered) == ["u1", "a1", "b1"]


@pytest.mark.asyncio
async def test_value_identical_duplicates_keep_chronological_order() -> None:
    """Regression test for the identity-keyed index map.

    Two distinct message objects can compare equal: BaseChatMessage.__eq__ is
    pydantic value equality, so a message and its model_copy() (same id) are
    ==. A re-sort keyed on messages.index(m) would map both to the first
    duplicate's position, and the stable sort would then keep them in config
    order. The identity-keyed map gives each object its true position.
    """
    older_ack = TextMessage(source="A", content="ack")
    newer_ack = older_ack.model_copy()
    assert newer_ack == older_ack
    assert newer_ack is not older_ack

    messages = [older_ack, newer_ack]
    filtered = await _filtered_messages(
        messages,
        per_source=[
            PerSourceFilter(source="A", position="last", count=1),
            PerSourceFilter(source="A", position="first", count=1),
        ],
    )
    # Config order emits [newer, older]; chronology is [older, newer].
    # Identity comparison is required here: the two messages are ==, so a
    # plain equality assertion could not tell the orders apart.
    assert len(filtered) == 2
    assert filtered[0] is older_ack
    assert filtered[1] is newer_ack
