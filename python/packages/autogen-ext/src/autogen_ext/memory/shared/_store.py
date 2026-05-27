from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from autogen_core import CancellationToken, Component
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from typing_extensions import Self

from ._config import MemoryScope, SharedMemoryConfig

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    group_id TEXT,
    agent_id TEXT,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    version INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    fact_hash TEXT NOT NULL,
    ttl_expires_at TEXT,
    deleted INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content,
    content=facts,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    INSERT INTO facts_fts(rowid, content) VALUES (new.rowid, new.content);
END;
"""


def _fact_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WriteReceipt:
    __slots__ = ("fact_id", "scope", "agent_id", "timestamp", "fact_hash", "version")

    def __init__(self, fact_id: str, scope: str, agent_id: str, timestamp: str, fact_hash: str, version: int):
        self.fact_id = fact_id
        self.scope = scope
        self.agent_id = agent_id
        self.timestamp = timestamp
        self.fact_hash = fact_hash
        self.version = version

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "scope": self.scope,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "fact_hash": self.fact_hash,
            "version": self.version,
        }


class SharedMemoryStore(Memory, Component[SharedMemoryConfig]):
    """Cross-agent shared memory store with scoped FTS recall.

    Stores facts in SQLite with FTS5 full-text search, scoped to agent/group/global.
    Facts are recalled as small capsules via tool-result position, not prefix-loaded.

    No external dependencies — uses Python's built-in sqlite3 module.

    Args:
        config: Configuration for the shared memory store.
        agent_id: Identity of the agent using this store instance.
    """

    component_type = "memory"
    component_config_schema = SharedMemoryConfig
    component_provider_override = "autogen_ext.memory.shared.SharedMemoryStore"

    def __init__(self, config: SharedMemoryConfig | None = None, agent_id: str = "default") -> None:
        self._config = config or SharedMemoryConfig()
        self._agent_id = agent_id
        self._conn: sqlite3.Connection | None = None

    def _ensure_initialized(self) -> None:
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(self._config.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA_SQL)

    def _check_write_auth(self, scope: MemoryScope) -> None:
        policy = self._config.write_policies.get(scope.value)
        if policy is None:
            raise PermissionError(f"No write policy defined for scope '{scope.value}'")
        if "*" in policy.allowed_agents:
            return
        if self._agent_id not in policy.allowed_agents:
            raise PermissionError(
                f"Agent '{self._agent_id}' is not authorized to write to '{scope.value}' scope"
            )

    def _scope_filter(self, scope: str | None) -> str:
        parts = ["deleted = 0"]
        now = _now_iso()
        parts.append(f"(ttl_expires_at IS NULL OR ttl_expires_at > '{now}')")

        if scope is None or scope == "all":
            pass
        elif scope == MemoryScope.AGENT.value:
            parts.append(f"scope = 'agent' AND agent_id = '{self._agent_id}'")
        elif scope == MemoryScope.GROUP.value:
            gid = self._config.group_id or "default"
            parts.append(f"scope = 'group' AND group_id = '{gid}'")
        elif scope == MemoryScope.GLOBAL.value:
            parts.append("scope = 'global'")
        else:
            parts.append(f"scope = '{scope}'")

        return " AND ".join(parts)

    def remember(
        self,
        fact: str,
        scope: MemoryScope = MemoryScope.GROUP,
        confidence: float = 1.0,
        ttl_days: int | None = None,
    ) -> WriteReceipt:
        """Write a fact to the store. Returns a receipt with provenance."""
        self._ensure_initialized()
        assert self._conn is not None

        self._check_write_auth(scope)

        fact_id = str(uuid.uuid4())
        now = _now_iso()
        h = _fact_hash(fact)
        ttl_exp = None
        if ttl_days is not None:
            ttl_exp = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()

        group_id = self._config.group_id if scope == MemoryScope.GROUP else None
        agent_id_val = self._agent_id if scope == MemoryScope.AGENT else None

        self._conn.execute(
            """INSERT INTO facts
               (fact_id, scope, group_id, agent_id, content, confidence,
                version, created_by, created_at, updated_at, fact_hash, ttl_expires_at, deleted)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, 0)""",
            (fact_id, scope.value, group_id, agent_id_val, fact, confidence,
             self._agent_id, now, now, h, ttl_exp),
        )
        self._conn.commit()

        return WriteReceipt(
            fact_id=fact_id, scope=scope.value, agent_id=self._agent_id,
            timestamp=now, fact_hash=h, version=1,
        )

    def search(
        self,
        query_text: str,
        scope: str | None = None,
        top_k: int | None = None,
    ) -> List[dict[str, Any]]:
        """Search facts via FTS5. Returns capsules with provenance metadata."""
        self._ensure_initialized()
        assert self._conn is not None

        k = top_k or self._config.default_top_k
        where = self._scope_filter(scope)
        max_bytes = self._config.max_capsule_bytes

        sql = f"""
            SELECT f.fact_id, f.scope, f.group_id, f.agent_id, f.content,
                   f.confidence, f.version, f.created_by, f.created_at,
                   f.updated_at, f.fact_hash
            FROM facts f
            JOIN facts_fts fts ON f.rowid = fts.rowid
            WHERE fts.facts_fts MATCH ?
              AND {where}
            ORDER BY fts.rank
            LIMIT ?
        """

        # FTS5 query: add prefix matching for each term
        fts_query = " OR ".join(f'"{w}"*' for w in query_text.split() if w.strip())
        if not fts_query:
            return []

        try:
            rows = self._conn.execute(sql, (fts_query, k)).fetchall()
        except sqlite3.OperationalError:
            return []

        results = []
        for row in rows:
            content = row["content"]
            if len(content.encode()) > max_bytes:
                content = content.encode()[:max_bytes].decode(errors="ignore") + "..."

            results.append({
                "fact_id": row["fact_id"],
                "content": content,
                "scope": row["scope"],
                "memory_scope_used": row["scope"],
                "created_by": row["created_by"],
                "confidence": row["confidence"],
                "created_at": row["created_at"],
                "fact_hash": row["fact_hash"],
                "version": row["version"],
            })

        return results

    def forget(self, fact_id: str) -> bool:
        """Soft-delete a fact. Tombstone preserved for audit."""
        self._ensure_initialized()
        assert self._conn is not None

        cur = self._conn.execute(
            "UPDATE facts SET deleted = 1, updated_at = ? WHERE fact_id = ? AND deleted = 0",
            (_now_iso(), fact_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    # --- Memory protocol implementation ---

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        messages = await model_context.get_messages()
        if not messages:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        last_msg = messages[-1]
        query_text = last_msg.content if isinstance(last_msg.content, str) else str(last_msg)

        results = self.search(query_text)
        memory_contents: List[MemoryContent] = []

        if results:
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(
                    f"{i}. [{r['scope']}|by:{r['created_by']}|conf:{r['confidence']}] {r['content']}"
                )
                memory_contents.append(MemoryContent(
                    content=r["content"],
                    mime_type=MemoryMimeType.TEXT,
                    metadata=r,
                ))

            ctx = "\nShared memory (claim provenance shown — verify before acting on):\n" + "\n".join(lines)
            await model_context.add_message(SystemMessage(content=ctx))

        return UpdateContextResult(memories=MemoryQueryResult(results=memory_contents))

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        query_text = query if isinstance(query, str) else str(query.content)
        scope = kwargs.get("scope")
        top_k = kwargs.get("top_k")

        results = self.search(query_text, scope=scope, top_k=top_k)
        return MemoryQueryResult(results=[
            MemoryContent(content=r["content"], mime_type=MemoryMimeType.TEXT, metadata=r)
            for r in results
        ])

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        text = content.content if isinstance(content.content, str) else str(content.content)
        scope_str = (content.metadata or {}).get("scope", "group")
        confidence = (content.metadata or {}).get("confidence", 1.0)
        ttl_days = (content.metadata or {}).get("ttl_days")

        try:
            scope = MemoryScope(scope_str)
        except ValueError:
            scope = MemoryScope.GROUP

        self.remember(fact=text, scope=scope, confidence=confidence, ttl_days=ttl_days)

    async def clear(self) -> None:
        self._ensure_initialized()
        assert self._conn is not None
        self._conn.execute("UPDATE facts SET deleted = 1, updated_at = ?", (_now_iso(),))
        self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @classmethod
    def _from_config(cls, config: SharedMemoryConfig) -> Self:
        return cls(config=config)

    def _to_config(self) -> SharedMemoryConfig:
        return self._config
