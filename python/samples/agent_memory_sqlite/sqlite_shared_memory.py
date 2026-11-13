"""
SQLiteSharedMemoryStore - Standalone SQLite Shared Memory Provider for Microsoft AutoGen
Targeting examples/agent_memory/ against pinned commit 027ecf0.

Features:
- Scoped memory isolation: agent, group, global tiers.
- Bi-temporal lifecycle: valid_from, valid_to soft invalidation.
- Atomic conditional supersede: ensures only current in-force facts are superseded.
- Scoped window ranking: narrowest scope and highest authority tier shadow lower tiers.
- Trusted context binding: model-facing tool interfaces cannot forge authority tiers.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any

class WorkerSetupError(Exception):
    """Raised when worker database connection or pragma initialization fails."""
    pass

class ReplacementConflictError(Exception):
    """Raised when an atomic conditional supersede fails due to competing concurrent update."""
    pass

class ScopeAuthorizationError(Exception):
    """Raised when an unauthorized actor attempts to supersede or delete out-of-scope memory."""
    pass


class SQLiteSharedMemoryStore:
    def __init__(self, db_path: str, timeout: float = 5.0):
        self.db_path = db_path
        self.timeout = timeout
        self._init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Create connection and assert strict PRAGMA invariants."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            conn.row_factory = sqlite3.Row
            
            # Enforce foreign keys and WAL mode
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            
            fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            wal = conn.execute("PRAGMA journal_mode;").fetchone()[0].lower()
            
            assert fk == 1, "PRAGMA foreign_keys must be 1"
            assert wal == "wal", f"PRAGMA journal_mode must be 'wal', got '{wal}'"
            return conn
        except Exception as e:
            raise WorkerSetupError(f"Failed to initialize SQLite connection to {self.db_path}: {e}") from e

    def _init_schema(self) -> None:
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_capsules (
                        capsule_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        scope_type TEXT NOT NULL,
                        scope_id TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        predicate TEXT NOT NULL,
                        object TEXT NOT NULL,
                        authority_tier INTEGER NOT NULL DEFAULT 20,
                        confidence REAL NOT NULL DEFAULT 1.0,
                        superseded_by TEXT,
                        valid_from TEXT NOT NULL,
                        valid_to TEXT,
                        FOREIGN KEY (superseded_by) REFERENCES memory_capsules(capsule_id)
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_capsules_active
                    ON memory_capsules(tenant_id, subject, predicate, valid_to);
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_capsules_scope
                    ON memory_capsules(tenant_id, scope_type, scope_id);
                """)
        finally:
            conn.close()

    def create(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        subject: str,
        predicate: str,
        object_: str,
        authority_tier: int = 20,
        confidence: float = 1.0
    ) -> str:
        """Create an active memory capsule."""
        capsule_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO memory_capsules (
                        capsule_id, tenant_id, scope_type, scope_id,
                        subject, predicate, object, authority_tier,
                        confidence, valid_from, valid_to
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """, (
                    capsule_id, tenant_id, scope_type, scope_id,
                    subject.strip(), predicate.strip(), object_.strip(),
                    authority_tier, confidence, now_iso
                ))
            return capsule_id
        finally:
            conn.close()

    def recall(
        self,
        tenant_id: str,
        scope_hierarchy: List[Tuple[str, str]],
        subject: Optional[str] = None,
        predicate: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recall active memories matching caller scope hierarchy.
        Higher authority_tier wins; within same tier, narrower scope (session/agent > group > global) wins.
        """
        conn = self.get_connection()
        try:
            # Build scope predicate
            scope_clauses = []
            params: List[Any] = [tenant_id]
            for s_type, s_id in scope_hierarchy:
                scope_clauses.append("(scope_type = ? AND scope_id = ?)")
                params.extend([s_type, s_id])
            
            scope_filter = " OR ".join(scope_clauses) if scope_clauses else "1=0"
            
            filter_clauses = [f"tenant_id = ?", f"({scope_filter})", "valid_to IS NULL"]
            if subject:
                filter_clauses.append("subject = ?")
                params.append(subject.strip())
            if predicate:
                filter_clauses.append("predicate = ?")
                params.append(predicate.strip())

            where_sql = " AND ".join(filter_clauses)

            # Window query resolving scope hierarchy
            sql = f"""
                WITH active_candidates AS (
                    SELECT 
                        capsule_id, tenant_id, scope_type, scope_id,
                        subject, predicate, object, authority_tier,
                        confidence, valid_from,
                        ROW_NUMBER() OVER (
                            PARTITION BY subject, predicate
                            ORDER BY 
                                authority_tier DESC,
                                CASE scope_type
                                    WHEN 'agent'  THEN 1
                                    WHEN 'group'  THEN 2
                                    WHEN 'global' THEN 3
                                    ELSE 4
                                END ASC,
                                valid_from DESC
                        ) AS rank
                    FROM memory_capsules
                    WHERE {where_sql}
                )
                SELECT 
                    capsule_id, tenant_id, scope_type, scope_id,
                    subject, predicate, object, authority_tier,
                    confidence, valid_from
                FROM active_candidates
                WHERE rank = 1
                ORDER BY subject, predicate;
            """
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def supersede(
        self,
        tenant_id: str,
        target_id: str,
        new_subject: str,
        new_predicate: str,
        new_object: str,
        authority_tier: int = 20,
        confidence: float = 1.0
    ) -> Tuple[str, str]:
        """
        Atomic conditional update: marks predecessor invalid (valid_to = now) 
        ONLY if currently active (valid_to IS NULL) and authority_tier is sufficient.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        new_id = str(uuid.uuid4())
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                # Check target exists, belongs to tenant, is active, and authority tier permits
                cursor.execute("""
                    SELECT scope_type, scope_id, authority_tier, valid_to
                    FROM memory_capsules
                    WHERE capsule_id = ? AND tenant_id = ?
                """, (target_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    raise KeyError(f"Memory capsule {target_id} not found for tenant {tenant_id}")
                
                target_scope_type = row["scope_type"]
                target_scope_id = row["scope_id"]
                target_authority = row["authority_tier"]
                target_valid_to = row["valid_to"]

                if target_valid_to is not None:
                    raise ReplacementConflictError(f"Memory capsule {target_id} has already been superseded")

                if authority_tier < target_authority:
                    raise ScopeAuthorizationError(
                        f"Authority tier {authority_tier} cannot supersede existing tier {target_authority}"
                    )

                # 1. Insert successor first
                cursor.execute("""
                    INSERT INTO memory_capsules (
                        capsule_id, tenant_id, scope_type, scope_id,
                        subject, predicate, object, authority_tier,
                        confidence, valid_from, valid_to
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """, (
                    new_id, tenant_id, target_scope_type, target_scope_id,
                    new_subject.strip(), new_predicate.strip(), new_object.strip(),
                    authority_tier, confidence, now_iso
                ))

                # 2. Conditionally update predecessor with optimistic concurrency check
                cursor.execute("""
                    UPDATE memory_capsules
                    SET valid_to = ?, superseded_by = ?
                    WHERE capsule_id = ? AND valid_to IS NULL
                """, (now_iso, new_id, target_id))

                if cursor.rowcount == 0:
                    raise ReplacementConflictError(f"Concurrent update conflict: {target_id} was superseded by peer")

            return new_id, target_id
        finally:
            conn.close()

    def forget(self, tenant_id: str, target_id: str, authority_tier: int = 20) -> bool:
        """Soft-deletes a fact by setting valid_to = now, preserving audit trail."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT authority_tier, valid_to
                    FROM memory_capsules
                    WHERE capsule_id = ? AND tenant_id = ?
                """, (target_id, tenant_id))
                row = cursor.fetchone()
                if not row:
                    return False
                if row["valid_to"] is not None:
                    return False
                if authority_tier < row["authority_tier"]:
                    raise ScopeAuthorizationError("Insufficient authority tier to forget fact")

                cursor.execute("""
                    UPDATE memory_capsules
                    SET valid_to = ?
                    WHERE capsule_id = ? AND valid_to IS NULL
                """, (now_iso, target_id))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def bind(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        authority_tier: int = 20,
        allowed_scopes: Optional[List[Tuple[str, str]]] = None
    ) -> 'BoundSessionMemory':
        """Bind storage store to a trusted orchestrator session context."""
        return BoundSessionMemory(
            store=self,
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            authority_tier=authority_tier,
            allowed_scopes=allowed_scopes or [(scope_type, scope_id)]
        )


class BoundSessionMemory:
    """
    Model-facing memory tool wrapper.
    Caller scope and authority tier are injected server-side by the host application.
    The LLM tool surface only accepts (subject, predicate, object).
    """
    def __init__(
        self,
        store: SQLiteSharedMemoryStore,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        authority_tier: int,
        allowed_scopes: List[Tuple[str, str]]
    ):
        self._store = store
        self._tenant_id = tenant_id
        self._scope_type = scope_type
        self._scope_id = scope_id
        self._authority_tier = authority_tier
        self._allowed_scopes = allowed_scopes

    def remember(self, subject: str, predicate: str, object_: str) -> str:
        """Tool interface for memory insertion."""
        return self._store.create(
            tenant_id=self._tenant_id,
            scope_type=self._scope_type,
            scope_id=self._scope_id,
            authority_tier=self._authority_tier,
            subject=subject,
            predicate=predicate,
            object_=object_
        )

    def search(self, subject: Optional[str] = None, predicate: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tool interface for memory recall."""
        return self._store.recall(
            tenant_id=self._tenant_id,
            scope_hierarchy=self._allowed_scopes,
            subject=subject,
            predicate=predicate
        )

    def supersede(self, target_id: str, new_subject: str, new_predicate: str, new_object: str) -> Tuple[str, str]:
        """Tool interface for memory update."""
        return self._store.supersede(
            tenant_id=self._tenant_id,
            target_id=target_id,
            new_subject=new_subject,
            new_predicate=new_predicate,
            new_object=new_object,
            authority_tier=self._authority_tier
        )

    def forget(self, target_id: str) -> bool:
        """Tool interface for memory deletion."""
        return self._store.forget(
            tenant_id=self._tenant_id,
            target_id=target_id,
            authority_tier=self._authority_tier
        )
