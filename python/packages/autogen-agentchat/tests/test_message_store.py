"""Tests for MessageStore abstraction and InMemoryMessageStore implementation."""

import asyncio
import time
from datetime import timedelta
from typing import Sequence

import pytest
from autogen_agentchat.teams import InMemoryMessageStore, MessageStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StringStore(MessageStore[str]):
    """Minimal concrete subclass of MessageStore used to verify the ABC contract."""

    def __init__(self) -> None:
        self._data: list[str] = []

    async def append(self, message: str) -> None:
        self._data.append(message)

    async def get_messages(self) -> Sequence[str]:
        return list(self._data)

    async def clear(self) -> None:
        self._data.clear()

    async def count(self) -> int:
        return len(self._data)


# ---------------------------------------------------------------------------
# Abstract interface tests (via concrete subclass)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_message_store_is_abstract() -> None:
    """MessageStore cannot be instantiated directly."""
    with pytest.raises(TypeError):
        MessageStore()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_custom_concrete_store_append_and_get() -> None:
    store = _StringStore()
    await store.append("hello")
    await store.append("world")
    messages = await store.get_messages()
    assert list(messages) == ["hello", "world"]


@pytest.mark.asyncio
async def test_custom_concrete_store_count() -> None:
    store = _StringStore()
    assert await store.count() == 0
    await store.append("a")
    assert await store.count() == 1
    await store.append("b")
    assert await store.count() == 2


@pytest.mark.asyncio
async def test_custom_concrete_store_clear() -> None:
    store = _StringStore()
    await store.append("a")
    await store.append("b")
    await store.clear()
    assert await store.count() == 0
    assert list(await store.get_messages()) == []


# ---------------------------------------------------------------------------
# InMemoryMessageStore – basic behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_store_starts_empty() -> None:
    store: InMemoryMessageStore[str] = InMemoryMessageStore()
    assert await store.count() == 0
    assert list(await store.get_messages()) == []


@pytest.mark.asyncio
async def test_in_memory_store_append_and_get() -> None:
    store: InMemoryMessageStore[str] = InMemoryMessageStore()
    await store.append("msg1")
    await store.append("msg2")
    await store.append("msg3")
    messages = list(await store.get_messages())
    assert messages == ["msg1", "msg2", "msg3"]


@pytest.mark.asyncio
async def test_in_memory_store_count() -> None:
    store: InMemoryMessageStore[int] = InMemoryMessageStore()
    for i in range(5):
        await store.append(i)
    assert await store.count() == 5


@pytest.mark.asyncio
async def test_in_memory_store_clear() -> None:
    store: InMemoryMessageStore[str] = InMemoryMessageStore()
    await store.append("a")
    await store.append("b")
    await store.clear()
    assert await store.count() == 0
    assert list(await store.get_messages()) == []


@pytest.mark.asyncio
async def test_in_memory_store_append_after_clear() -> None:
    """Appending after a clear should work as if the store is fresh."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore()
    await store.append("first")
    await store.clear()
    await store.append("second")
    assert await store.count() == 1
    assert list(await store.get_messages()) == ["second"]


@pytest.mark.asyncio
async def test_in_memory_store_get_messages_returns_snapshot() -> None:
    """get_messages() should return a copy; mutations must not affect internal state."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore()
    await store.append("a")
    snapshot = list(await store.get_messages())
    snapshot.append("extra")
    # Internal state is unchanged.
    assert await store.count() == 1


@pytest.mark.asyncio
async def test_in_memory_store_generic_type() -> None:
    """InMemoryMessageStore should work with arbitrary types, not just strings."""

    class _Msg:
        def __init__(self, value: int) -> None:
            self.value = value

    store: InMemoryMessageStore[_Msg] = InMemoryMessageStore()
    await store.append(_Msg(1))
    await store.append(_Msg(2))
    msgs = list(await store.get_messages())
    assert len(msgs) == 2
    assert msgs[0].value == 1
    assert msgs[1].value == 2


# ---------------------------------------------------------------------------
# InMemoryMessageStore – TTL behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_store_no_ttl_does_not_expire() -> None:
    """Without a TTL the store should retain messages indefinitely."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore()
    await store.append("persistent")
    # Sleep a small amount to confirm nothing is quietly being cleared.
    await asyncio.sleep(0.05)
    assert await store.count() == 1


@pytest.mark.asyncio
async def test_in_memory_store_ttl_expires_on_get_messages() -> None:
    """After the TTL elapses, get_messages() should return an empty sequence."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(milliseconds=50))
    await store.append("soon-gone")
    assert await store.count() == 1
    # Wait for expiry.
    await asyncio.sleep(0.1)
    messages = list(await store.get_messages())
    assert messages == []


@pytest.mark.asyncio
async def test_in_memory_store_ttl_expires_on_count() -> None:
    """After the TTL elapses, count() should return 0."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(milliseconds=50))
    await store.append("soon-gone")
    await asyncio.sleep(0.1)
    assert await store.count() == 0


@pytest.mark.asyncio
async def test_in_memory_store_ttl_restarts_after_expiry_append() -> None:
    """Appending after TTL expiry should restart the window with the new message."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(milliseconds=50))
    await store.append("first-window")
    await asyncio.sleep(0.1)
    # After expiry, appending should start a fresh window.
    await store.append("second-window")
    assert await store.count() == 1
    assert list(await store.get_messages()) == ["second-window"]


@pytest.mark.asyncio
async def test_in_memory_store_ttl_not_expired_yet() -> None:
    """Messages should still be present before the TTL has elapsed."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(seconds=60))
    await store.append("still-alive")
    assert await store.count() == 1
    assert list(await store.get_messages()) == ["still-alive"]


@pytest.mark.asyncio
async def test_in_memory_store_clear_resets_ttl_clock() -> None:
    """Calling clear() should reset the TTL clock so the next append starts fresh."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(seconds=60))
    await store.append("msg")
    await store.clear()
    # Internal _started_at must be None after clear.
    assert store._started_at is None
    await store.append("new-msg")
    assert await store.count() == 1


@pytest.mark.asyncio
async def test_in_memory_store_ttl_multiple_appends_same_window() -> None:
    """All messages appended within a TTL window should be returned together."""
    store: InMemoryMessageStore[str] = InMemoryMessageStore(ttl=timedelta(seconds=60))
    await store.append("a")
    await store.append("b")
    await store.append("c")
    messages = list(await store.get_messages())
    assert messages == ["a", "b", "c"]
    assert await store.count() == 3


# ---------------------------------------------------------------------------
# Import smoke test
# ---------------------------------------------------------------------------


def test_exports_from_teams_package() -> None:
    """MessageStore and InMemoryMessageStore must be importable from autogen_agentchat.teams."""
    from autogen_agentchat.teams import InMemoryMessageStore as IMS
    from autogen_agentchat.teams import MessageStore as MS

    assert MS is MessageStore
    assert IMS is InMemoryMessageStore
