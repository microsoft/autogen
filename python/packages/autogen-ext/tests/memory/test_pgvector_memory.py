"""Unit tests for PgvectorMemory.

The tests run against an in-process fake connection pool and a deterministic
bag-of-words embedder, so they exercise ingestion, semantic ranking, and
serialization without a live PostgreSQL database or any network calls. The
pgvector driver must be importable (the module requires it), but no real
database is used.
"""

import hashlib
import math
import re
from typing import Any, Dict, List, Tuple

import pytest
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import SystemMessage, UserMessage
from autogen_ext.memory.pgvector import PgvectorMemory, PgvectorMemoryConfig

_MODULE = "autogen_ext.memory.pgvector._pgvector_memory"

_DIM = 64


@pytest.fixture(autouse=True)
def _no_vector_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip pgvector type registration; the fake connection is not a real psycopg connection."""
    monkeypatch.setattr(f"{_MODULE}.register_vector_async", None, raising=False)


def _bag_of_words(texts: Any) -> List[List[float]]:
    vectors: List[List[float]] = []
    for text in texts:
        vector = [0.0] * _DIM
        for token in re.findall(r"\w+", str(text).lower()):
            vector[int(hashlib.md5(token.encode()).hexdigest(), 16) % _DIM] += 1.0
        vectors.append(vector)
    return vectors


def _cosine_distance(a: Any, b: Any) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


class _FakeCursor:
    def __init__(self, rows: List[Tuple[Any, ...]]) -> None:
        self._rows = rows

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        return self._rows


class _FakeConnection:
    def __init__(self, store: Dict[str, Tuple[Any, ...]], statements: List[str]) -> None:
        self._store = store
        self._statements = statements

    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def execute(self, query: Any, params: Tuple[Any, ...] | None = None) -> _FakeCursor:
        # Production code composes statements with psycopg.sql; render them to text here so the
        # fake can route on the leading keyword exactly as a real driver would execute them.
        text = query if isinstance(query, str) else query.as_string(None)
        self._statements.append(text)
        keyword = text.strip().split(None, 1)[0].upper()
        if keyword == "CREATE":
            return _FakeCursor([])
        if keyword == "INSERT":
            # params: id, content, mime_type, metadata, embedding
            assert params is not None
            self._store[params[0]] = params
            return _FakeCursor([])
        if keyword == "DELETE":
            self._store.clear()
            return _FakeCursor([])
        if keyword == "SELECT":
            # params: embedding, top_k
            assert params is not None
            query_vec, top_k = params
            scored: List[Tuple[Any, ...]] = []
            for row in self._store.values():
                distance = _cosine_distance(query_vec, row[4])
                # content, mime_type, metadata, distance
                scored.append((row[1], row[2], row[3], distance))
            scored.sort(key=lambda r: r[3])
            return _FakeCursor(scored[:top_k])
        return _FakeCursor([])


class _FakePool:
    def __init__(self) -> None:
        self.store: Dict[str, Tuple[Any, ...]] = {}
        self.statements: List[str] = []
        self.open_count = 0
        self.closed = False

    async def open(self) -> None:
        self.open_count += 1

    async def close(self) -> None:
        self.closed = True

    def connection(self) -> _FakeConnection:
        return _FakeConnection(self.store, self.statements)


def _make_memory(pool: _FakePool, **config_kwargs: Any) -> PgvectorMemory:
    config = PgvectorMemoryConfig(dsn="postgresql://ignored", embedding_dimension=_DIM, **config_kwargs)
    return PgvectorMemory(config, connection_pool=pool, embedding_function=_bag_of_words)


def _text(content: str, **metadata: Any) -> MemoryContent:
    return MemoryContent(content=content, mime_type=MemoryMimeType.TEXT, metadata=metadata or None)


@pytest.mark.asyncio
async def test_add_and_query_returns_semantically_closest() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)
    await memory.add(_text("How do I dispute a billing charge on my invoice?", category="billing"))
    await memory.add(_text("The weather forecast for tomorrow is sunny."))
    await memory.add(_text("Who won the basketball game last night?"))

    result = await memory.query("billing invoice dispute")

    assert result.results
    assert "billing" in str(result.results[0].content)
    assert result.results[0].metadata is not None
    assert result.results[0].metadata.get("category") == "billing"
    assert "score" in result.results[0].metadata


@pytest.mark.asyncio
async def test_empty_query_returns_no_results() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)
    await memory.add(_text("billing invoice"))

    result = await memory.query("   ")

    assert result.results == []


@pytest.mark.asyncio
async def test_distance_threshold_drops_unrelated() -> None:
    pool = _FakePool()
    memory = _make_memory(pool, distance_threshold=0.5)
    await memory.add(_text("billing invoice dispute charge"))
    await memory.add(_text("basketball score tonight"))

    result = await memory.query("billing invoice dispute charge")

    assert len(result.results) == 1
    assert "billing" in str(result.results[0].content)


@pytest.mark.asyncio
async def test_json_content_roundtrip() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)
    await memory.add(MemoryContent(content={"unit": "metric"}, mime_type=MemoryMimeType.JSON))

    result = await memory.query("metric unit preference")

    assert result.results
    top = result.results[0]
    assert top.mime_type == MemoryMimeType.JSON
    assert top.content == {"unit": "metric"}


@pytest.mark.asyncio
async def test_clear_removes_all_entries() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)
    await memory.add(_text("billing invoice"))
    assert len(pool.store) == 1

    await memory.clear()

    assert len(pool.store) == 0


@pytest.mark.asyncio
async def test_update_context_injects_system_message() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)
    await memory.add(_text("The weather should be in metric units"))

    context = BufferedChatCompletionContext(buffer_size=5)
    await context.add_message(UserMessage(content="what units for the weather?", source="user"))

    result = await memory.update_context(context)

    assert result.memories.results
    messages = await context.get_messages()
    assert any(isinstance(m, SystemMessage) for m in messages)


@pytest.mark.asyncio
async def test_owned_pool_opened_once_and_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakePool()

    def _factory(dsn: str, **kwargs: Any) -> _FakePool:
        return fake

    monkeypatch.setattr(f"{_MODULE}.AsyncConnectionPool", _factory)
    memory = PgvectorMemory(
        PgvectorMemoryConfig(dsn="postgresql://x", embedding_dimension=_DIM),
        embedding_function=_bag_of_words,
    )

    await memory.add(_text("billing invoice"))
    await memory.query("billing")

    assert fake.open_count == 1
    await memory.close()
    assert fake.closed is True


@pytest.mark.asyncio
async def test_injected_pool_not_opened_or_closed() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)

    await memory.add(_text("billing invoice"))
    await memory.close()

    assert pool.open_count == 0
    assert pool.closed is False


def test_component_config_roundtrip() -> None:
    memory = PgvectorMemory(PgvectorMemoryConfig(table_name="custom_mem", top_k=5))

    dumped = memory.dump_component()
    loaded = PgvectorMemory.load_component(dumped)

    assert isinstance(loaded, PgvectorMemory)
    assert loaded.config.table_name == "custom_mem"
    assert loaded.config.top_k == 5


@pytest.mark.asyncio
async def test_create_extension_runs_by_default() -> None:
    pool = _FakePool()
    memory = _make_memory(pool)
    await memory.add(_text("billing invoice"))
    assert any(s.strip().upper().startswith("CREATE EXTENSION") for s in pool.statements)


@pytest.mark.asyncio
async def test_create_extension_skipped_when_disabled() -> None:
    pool = _FakePool()
    memory = _make_memory(pool, create_extension=False)
    await memory.add(_text("billing invoice"))
    assert not any(s.strip().upper().startswith("CREATE EXTENSION") for s in pool.statements)
    # The table is still created; only the extension step is skipped.
    assert any("CREATE TABLE" in s.upper() for s in pool.statements)


@pytest.mark.asyncio
async def test_table_name_rendered_as_quoted_identifier() -> None:
    pool = _FakePool()
    memory = _make_memory(pool, table_name="my_mem")
    await memory.add(_text("billing invoice"))
    insert = next(s for s in pool.statements if s.strip().upper().startswith("INSERT"))
    # Composed with psycopg.sql.Identifier, so the table name is a quoted identifier, not interpolated text.
    assert '"my_mem"' in insert
