"""Comprehensive tests for the MessageStore abstraction and InMemoryMessageStore implementation."""

import asyncio
import time
from typing import Any, List, Mapping, Sequence
from unittest.mock import patch

import pytest

from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.state import InMemoryMessageStore, MessageStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_msg(content: str, source: str = "user") -> TextMessage:
    """Create a simple TextMessage for testing."""
    return TextMessage(content=content, source=source)


class DummyMessageStore(MessageStore):
    """Minimal concrete subclass used only to test the ABC contract."""

    def __init__(self, *, ttl: float | None = None) -> None:
        super().__init__(ttl=ttl)
        self._msgs: List[BaseAgentEvent | BaseChatMessage] = []

    async def add_messages(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        self._msgs.extend(messages)

    async def get_messages(self) -> List[BaseAgentEvent | BaseChatMessage]:
        return list(self._msgs)

    async def clear(self) -> None:
        self._msgs.clear()

    async def save_state(self) -> Mapping[str, Any]:
        return {"messages": [m.dump() for m in self._msgs]}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        from autogen_agentchat.messages import MessageFactory

        factory = MessageFactory()
        self._msgs = [factory.create(m) for m in state.get("messages", [])]


# ---------------------------------------------------------------------------
# Tests – ABC & construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abc_cannot_be_instantiated() -> None:
    """MessageStore is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        MessageStore()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_ttl_must_be_positive() -> None:
    """A non-positive TTL must raise ValueError."""
    with pytest.raises(ValueError, match="positive"):
        InMemoryMessageStore(ttl=0)
    with pytest.raises(ValueError, match="positive"):
        InMemoryMessageStore(ttl=-5)


@pytest.mark.asyncio
async def test_ttl_none_is_allowed() -> None:
    """TTL=None means messages never expire."""
    store = InMemoryMessageStore(ttl=None)
    assert store.ttl is None


@pytest.mark.asyncio
async def test_ttl_property() -> None:
    """The ttl property should return the configured value."""
    store = InMemoryMessageStore(ttl=60.0)
    assert store.ttl == 60.0


# ---------------------------------------------------------------------------
# Tests – basic CRUD (InMemoryMessageStore)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_and_get_messages() -> None:
    """Messages added via add_messages should be retrievable via get_messages."""
    store = InMemoryMessageStore()
    msg1 = _make_msg("hello")
    msg2 = _make_msg("world")
    await store.add_messages([msg1, msg2])
    result = await store.get_messages()
    assert len(result) == 2
    assert result[0].content == "hello"
    assert result[1].content == "world"


@pytest.mark.asyncio
async def test_add_messages_preserves_order() -> None:
    """Multiple add_messages calls should preserve insertion order."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("a")])
    await store.add_messages([_make_msg("b"), _make_msg("c")])
    contents = [m.content for m in await store.get_messages()]
    assert contents == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_get_messages_returns_copy() -> None:
    """get_messages should return a new list each time (not a reference to internal state)."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("x")])
    list1 = await store.get_messages()
    list2 = await store.get_messages()
    assert list1 is not list2
    assert list1 == list2


@pytest.mark.asyncio
async def test_clear_removes_all() -> None:
    """clear() should remove all messages."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("a"), _make_msg("b")])
    await store.clear()
    result = await store.get_messages()
    assert len(result) == 0


@pytest.mark.asyncio
async def test_clear_on_empty_store() -> None:
    """Clearing an already-empty store should not raise."""
    store = InMemoryMessageStore()
    await store.clear()
    assert await store.get_messages() == []


@pytest.mark.asyncio
async def test_add_empty_sequence() -> None:
    """Adding an empty sequence should be a no-op."""
    store = InMemoryMessageStore()
    await store.add_messages([])
    assert await store.get_messages() == []


# ---------------------------------------------------------------------------
# Tests – TTL expiration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ttl_expires_messages() -> None:
    """Messages older than the TTL should not appear in get_messages."""
    store = InMemoryMessageStore(ttl=1.0)
    await store.add_messages([_make_msg("old")])

    # Manually adjust the timestamp to simulate time passing.
    store._timestamps[0] = time.monotonic() - 2.0

    await store.add_messages([_make_msg("new")])
    result = await store.get_messages()
    assert len(result) == 1
    assert result[0].content == "new"


@pytest.mark.asyncio
async def test_ttl_all_expired() -> None:
    """When all messages are expired, get_messages returns an empty list."""
    store = InMemoryMessageStore(ttl=0.5)
    await store.add_messages([_make_msg("a"), _make_msg("b")])

    # Backdate all timestamps.
    now = time.monotonic()
    store._timestamps = [now - 1.0, now - 1.0]

    result = await store.get_messages()
    assert result == []


@pytest.mark.asyncio
async def test_ttl_no_expiry_when_none() -> None:
    """When TTL is None, messages should never expire regardless of age."""
    store = InMemoryMessageStore(ttl=None)
    await store.add_messages([_make_msg("forever")])
    # Backdate far into the past.
    store._timestamps[0] = time.monotonic() - 999999
    result = await store.get_messages()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_ttl_boundary() -> None:
    """A message exactly at the TTL boundary should still be included."""
    store = InMemoryMessageStore(ttl=5.0)
    await store.add_messages([_make_msg("boundary")])
    # Set timestamp to exactly the cutoff.
    store._timestamps[0] = time.monotonic() - 5.0
    result = await store.get_messages()
    # The message should be pruned because cutoff = now - ttl, and ts < cutoff.
    # (ts == cutoff means it's exactly at the boundary -- still valid since we use >= cutoff)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Tests – save_state / load_state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_load_state() -> None:
    """State should round-trip through save_state and load_state."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("saved1"), _make_msg("saved2")])
    state = await store.save_state()

    new_store = InMemoryMessageStore()
    await new_store.load_state(state)
    messages = await new_store.get_messages()
    assert len(messages) == 2
    assert messages[0].content == "saved1"
    assert messages[1].content == "saved2"


@pytest.mark.asyncio
async def test_load_state_replaces_existing() -> None:
    """load_state should replace the current contents, not append."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("original")])

    other = InMemoryMessageStore()
    await other.add_messages([_make_msg("replacement")])
    state = await other.save_state()

    await store.load_state(state)
    messages = await store.get_messages()
    assert len(messages) == 1
    assert messages[0].content == "replacement"


@pytest.mark.asyncio
async def test_load_empty_state() -> None:
    """Loading an empty state dict should result in an empty store."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("stuff")])
    await store.load_state({})
    assert await store.get_messages() == []


# ---------------------------------------------------------------------------
# Tests – synchronous helpers (backwards compatibility)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extend_sync_helper() -> None:
    """The extend() sync helper should add messages identically to add_messages."""
    store = InMemoryMessageStore()
    store.extend([_make_msg("sync1"), _make_msg("sync2")])
    result = await store.get_messages()
    assert len(result) == 2
    assert result[0].content == "sync1"


@pytest.mark.asyncio
async def test_messages_property() -> None:
    """The messages property should return the internal list."""
    store = InMemoryMessageStore()
    await store.add_messages([_make_msg("via_property")])
    assert len(store.messages) == 1
    assert store.messages[0].content == "via_property"


# ---------------------------------------------------------------------------
# Tests – DummyMessageStore (custom implementation contract)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_store_implements_contract() -> None:
    """A custom MessageStore subclass should work through the standard API."""
    store = DummyMessageStore()
    await store.add_messages([_make_msg("custom")])
    result = await store.get_messages()
    assert len(result) == 1
    await store.clear()
    assert await store.get_messages() == []


@pytest.mark.asyncio
async def test_custom_store_ttl_property() -> None:
    """Custom stores should inherit the TTL property from the base class."""
    store = DummyMessageStore(ttl=120.0)
    assert store.ttl == 120.0


@pytest.mark.asyncio
async def test_custom_store_save_load() -> None:
    """Custom store save/load round-trip."""
    store = DummyMessageStore()
    await store.add_messages([_make_msg("persist")])
    state = await store.save_state()

    store2 = DummyMessageStore()
    await store2.load_state(state)
    msgs = await store2.get_messages()
    assert len(msgs) == 1
    assert msgs[0].content == "persist"
