import asyncio
import json
import os
import tempfile

import pytest

from autogen_ext.memory.shared import (
    MemoryScope,
    SharedMemoryConfig,
    SharedMemoryStore,
    WritePolicyEntry,
    make_memory_tools,
)
from autogen_core.memory import MemoryContent, MemoryMimeType


@pytest.fixture
def store():
    s = SharedMemoryStore(
        config=SharedMemoryConfig(
            db_path=":memory:",
            write_policies={
                "agent": WritePolicyEntry(allowed_agents=["*"]),
                "group": WritePolicyEntry(allowed_agents=["*"]),
                "global": WritePolicyEntry(allowed_agents=["admin_agent"]),
            },
            group_id="test-group",
        ),
        agent_id="agent_A",
    )
    yield s
    if s._conn is not None:
        s._conn.close()
        s._conn = None


class TestRememberAndSearch:
    def test_remember_returns_receipt(self, store: SharedMemoryStore):
        receipt = store.remember("project uses Pydantic v2 only", scope=MemoryScope.GROUP)
        assert receipt.fact_id
        assert receipt.scope == "group"
        assert receipt.agent_id == "agent_A"
        assert receipt.fact_hash
        assert receipt.version == 1

    def test_search_finds_stored_fact(self, store: SharedMemoryStore):
        store.remember("user prefers formal language", scope=MemoryScope.GROUP)
        results = store.search("formal language")
        assert len(results) == 1
        assert "formal language" in results[0]["content"]
        assert results[0]["memory_scope_used"] == "group"
        assert results[0]["created_by"] == "agent_A"

    def test_search_returns_provenance(self, store: SharedMemoryStore):
        store.remember("no PII in logs", scope=MemoryScope.GROUP, confidence=0.9)
        results = store.search("PII logs")
        assert len(results) == 1
        r = results[0]
        assert r["confidence"] == 0.9
        assert r["created_by"] == "agent_A"
        assert r["fact_hash"]
        assert r["version"] == 1

    def test_search_empty_returns_empty(self, store: SharedMemoryStore):
        results = store.search("nonexistent topic")
        assert results == []


class TestScopeFiltering:
    def test_agent_scope_isolation(self, store: SharedMemoryStore):
        store.remember("agent A note", scope=MemoryScope.AGENT)

        store_b = SharedMemoryStore(
            config=store._config,
            agent_id="agent_B",
        )
        store_b._conn = store._conn

        results_a = store.search("agent note", scope="agent")
        results_b = store_b.search("agent note", scope="agent")
        assert len(results_a) == 1
        assert len(results_b) == 0

    def test_group_scope_shared(self, store: SharedMemoryStore):
        store.remember("shared group fact", scope=MemoryScope.GROUP)

        store_b = SharedMemoryStore(
            config=store._config,
            agent_id="agent_B",
        )
        store_b._conn = store._conn

        results = store_b.search("shared group", scope="group")
        assert len(results) == 1

    def test_all_scope_returns_everything(self, store: SharedMemoryStore):
        store.remember("agent only fact", scope=MemoryScope.AGENT)
        store.remember("group shared fact", scope=MemoryScope.GROUP)
        results = store.search("fact", scope="all")
        assert len(results) == 2


class TestWriteAuthorization:
    def test_global_write_denied_for_unauthorized(self, store: SharedMemoryStore):
        with pytest.raises(PermissionError, match="not authorized"):
            store.remember("global fact", scope=MemoryScope.GLOBAL)

    def test_global_write_allowed_for_authorized(self):
        admin_store = SharedMemoryStore(
            config=SharedMemoryConfig(
                db_path=":memory:",
                write_policies={
                    "agent": WritePolicyEntry(allowed_agents=["*"]),
                    "group": WritePolicyEntry(allowed_agents=["*"]),
                    "global": WritePolicyEntry(allowed_agents=["admin_agent"]),
                },
            ),
            agent_id="admin_agent",
        )
        receipt = admin_store.remember("global policy rule", scope=MemoryScope.GLOBAL)
        assert receipt.scope == "global"


class TestForget:
    def test_forget_soft_deletes(self, store: SharedMemoryStore):
        receipt = store.remember("temporary fact", scope=MemoryScope.GROUP)
        assert store.forget(receipt.fact_id)
        results = store.search("temporary fact")
        assert len(results) == 0

    def test_forget_nonexistent_returns_false(self, store: SharedMemoryStore):
        assert not store.forget("nonexistent-uuid")

    def test_tombstone_preserved(self, store: SharedMemoryStore):
        receipt = store.remember("will be deleted", scope=MemoryScope.GROUP)
        store.forget(receipt.fact_id)
        store._ensure_initialized()
        row = store._conn.execute(
            "SELECT deleted FROM facts WHERE fact_id = ?", (receipt.fact_id,)
        ).fetchone()
        assert row["deleted"] == 1


class TestCapsuleSize:
    def test_large_content_truncated(self):
        s = SharedMemoryStore(
            config=SharedMemoryConfig(db_path=":memory:", max_capsule_bytes=50),
            agent_id="agent_A",
        )
        s.remember("a " * 100, scope=MemoryScope.GROUP)
        results = s.search("a")
        assert len(results) == 1
        assert len(results[0]["content"].encode()) <= 54  # 50 + "..."


class TestTTL:
    def test_expired_facts_not_returned(self, store: SharedMemoryStore):
        store.remember("expiring fact", scope=MemoryScope.GROUP, ttl_days=0)
        results = store.search("expiring fact")
        assert len(results) == 0


class TestMemoryProtocol:
    @pytest.mark.asyncio
    async def test_add_and_query(self, store: SharedMemoryStore):
        content = MemoryContent(
            content="user likes dark mode",
            mime_type=MemoryMimeType.TEXT,
            metadata={"scope": "group"},
        )
        await store.add(content)
        result = await store.query("dark mode")
        assert len(result.results) == 1
        assert "dark mode" in result.results[0].content

    @pytest.mark.asyncio
    async def test_clear_marks_all_deleted(self, store: SharedMemoryStore):
        store.remember("fact one", scope=MemoryScope.GROUP)
        store.remember("fact two", scope=MemoryScope.GROUP)
        await store.clear()
        results = store.search("fact")
        assert len(results) == 0


class TestTools:
    def test_make_memory_tools_returns_three(self, store: SharedMemoryStore):
        tools = make_memory_tools(store)
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == {"memory_search", "memory_remember", "memory_forget"}

    @pytest.mark.asyncio
    async def test_tool_search_round_trip(self, store: SharedMemoryStore):
        from autogen_core import CancellationToken

        tools = make_memory_tools(store)
        remember_tool = next(t for t in tools if t.name == "memory_remember")
        search_tool = next(t for t in tools if t.name == "memory_search")

        ct = CancellationToken()

        result = await remember_tool.run_json(
            {"fact": "deploy freezes on Thursdays", "scope": "group", "confidence": 0.95},
            ct,
        )
        receipt = json.loads(result)
        assert receipt["scope"] == "group"

        result = await search_tool.run_json(
            {"query": "deploy freeze", "scope": "all"},
            ct,
        )
        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert "Thursday" in parsed[0]["content"]

    @pytest.mark.asyncio
    async def test_tool_global_write_denied(self, store: SharedMemoryStore):
        from autogen_core import CancellationToken

        tools = make_memory_tools(store)
        remember_tool = next(t for t in tools if t.name == "memory_remember")
        ct = CancellationToken()

        result = await remember_tool.run_json(
            {"fact": "trying global write", "scope": "global"},
            ct,
        )
        assert "denied" in result.lower()


class TestPersistence:
    def test_file_backed_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            s1 = SharedMemoryStore(
                config=SharedMemoryConfig(db_path=db_path),
                agent_id="agent_A",
            )
            s1.remember("persistent fact", scope=MemoryScope.GROUP)
            asyncio.get_event_loop().run_until_complete(s1.close())

            s2 = SharedMemoryStore(
                config=SharedMemoryConfig(db_path=db_path),
                agent_id="agent_B",
            )
            results = s2.search("persistent fact")
            assert len(results) == 1
            assert results[0]["created_by"] == "agent_A"
            asyncio.get_event_loop().run_until_complete(s2.close())
        finally:
            os.unlink(db_path)
