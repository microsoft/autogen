import os
import sqlite3
import threading
import pytest
from typing import List

from sqlite_shared_memory import (
    SQLiteSharedMemoryStore,
    BoundSessionMemory,
    WorkerSetupError,
    ReplacementConflictError,
    ScopeAuthorizationError
)

@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_memory.db")

@pytest.fixture
def store(db_path):
    return SQLiteSharedMemoryStore(db_path)


def test_sqlite_pragmas(store):
    """Assert that foreign keys are ON and journal mode is WAL."""
    conn = store.get_connection()
    try:
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        wal = conn.execute("PRAGMA journal_mode;").fetchone()[0].lower()
        assert fk == 1, "PRAGMA foreign_keys must be 1"
        assert wal == "wal", "PRAGMA journal_mode must be wal"
    finally:
        conn.close()


def test_create_and_recall_scoped(store):
    """Verify lexical scope hierarchy (agent > group > global within equal authority)."""
    tenant = "tenant_alpha"
    # Create global rule
    store.create(tenant, "global", "global_main", "project", "style", "black", authority_tier=20)
    # Create group rule
    store.create(tenant, "group", "group_backend", "project", "style", "ruff", authority_tier=20)
    # Create agent rule
    store.create(tenant, "agent", "agent_worker1", "project", "style", "flake8", authority_tier=20)

    # Agent recall with full hierarchy [agent, group, global]
    hierarchy = [("agent", "agent_worker1"), ("group", "group_backend"), ("global", "global_main")]
    memories = store.recall(tenant, hierarchy, subject="project", predicate="style")
    assert len(memories) == 1
    assert memories[0]["object"] == "flake8"
    assert memories[0]["scope_type"] == "agent"

    # Group recall with hierarchy [group, global]
    group_hierarchy = [("group", "group_backend"), ("global", "global_main")]
    group_memories = store.recall(tenant, group_hierarchy, subject="project", predicate="style")
    assert len(group_memories) == 1
    assert group_memories[0]["object"] == "ruff"
    assert group_memories[0]["scope_type"] == "group"


def test_authority_tier_override(store):
    """Assert that higher authority tier (Tier 100) strictly overrides lower tier (Tier 20) regardless of scope."""
    tenant = "tenant_alpha"
    # Agent tier 20 note
    store.create(tenant, "agent", "agent_1", "security", "auth", "allow_insecure", authority_tier=20)
    # Global tier 100 operator policy
    store.create(tenant, "global", "global_policy", "security", "auth", "strict_mfa", authority_tier=100)

    hierarchy = [("agent", "agent_1"), ("global", "global_policy")]
    memories = store.recall(tenant, hierarchy, subject="security", predicate="auth")
    assert len(memories) == 1
    assert memories[0]["object"] == "strict_mfa"
    assert memories[0]["authority_tier"] == 100


def test_atomic_supersede_precedence(store):
    """Verify that supersede marks predecessor invalid and recall returns the successor."""
    tenant = "tenant_alpha"
    orig_id = store.create(tenant, "agent", "agent_1", "db", "port", "5432", authority_tier=20)

    new_id, superseded_id = store.supersede(
        tenant, orig_id, "db", "port", "5433", authority_tier=20
    )
    assert superseded_id == orig_id
    assert new_id != orig_id

    # Check recall: old port must be excluded
    memories = store.recall(tenant, [("agent", "agent_1")], subject="db", predicate="port")
    assert len(memories) == 1
    assert memories[0]["capsule_id"] == new_id
    assert memories[0]["object"] == "5433"

    # Direct DB inspection: old row has valid_to set and references successor
    conn = store.get_connection()
    try:
        row = conn.execute("SELECT valid_to, superseded_by FROM memory_capsules WHERE capsule_id = ?", (orig_id,)).fetchone()
        assert row["valid_to"] is not None
        assert row["superseded_by"] == new_id
    finally:
        conn.close()


def test_forget_tombstone(store):
    """Verify that forget soft-deletes the record while keeping audit row in DB."""
    tenant = "tenant_alpha"
    cid = store.create(tenant, "agent", "agent_1", "user", "name", "Alice", authority_tier=20)

    success = store.forget(tenant, cid, authority_tier=20)
    assert success is True

    # Recall returns nothing
    memories = store.recall(tenant, [("agent", "agent_1")], subject="user", predicate="name")
    assert len(memories) == 0

    # Row is preserved in database with valid_to stamped
    conn = store.get_connection()
    try:
        row = conn.execute("SELECT valid_to FROM memory_capsules WHERE capsule_id = ?", (cid,)).fetchone()
        assert row["valid_to"] is not None
    finally:
        conn.close()


def test_trusted_context_binding_prevents_privilege_escalation(store):
    """Verify that BoundSessionMemory binds caller credentials server-side and model cannot forge authority."""
    tenant = "tenant_alpha"
    # Orchestrator binds agent session with authority 20
    agent_mem = store.bind(
        tenant_id=tenant,
        scope_type="agent",
        scope_id="worker_99",
        authority_tier=20,
        allowed_scopes=[("agent", "worker_99"), ("global", "global_main")]
    )

    # Agent records a fact
    cid = agent_mem.remember("api", "rate_limit", "100")
    recalled = agent_mem.search("api", "rate_limit")
    assert len(recalled) == 1
    assert recalled[0]["authority_tier"] == 20

    # Operator records global policy with tier 100
    store.create(tenant, "global", "global_main", "api", "rate_limit", "50", authority_tier=100)

    # Agent recall now returns operator policy
    recalled_after = agent_mem.search("api", "rate_limit")
    assert len(recalled_after) == 1
    assert recalled_after[0]["authority_tier"] == 100
    assert recalled_after[0]["object"] == "50"

    # Agent attempting to supersede operator policy fails with ScopeAuthorizationError
    operator_cid = recalled_after[0]["capsule_id"]
    with pytest.raises(ScopeAuthorizationError):
        agent_mem.supersede(operator_cid, "api", "rate_limit", "200")


def test_competing_replacement_concurrency(store):
    """10 workers concurrently compete to supersede the same capsule. Exactly 1 wins, 9 fail with ReplacementConflictError."""
    tenant = "tenant_alpha"
    orig_id = store.create(tenant, "group", "group_1", "config", "workers", "4", authority_tier=20)

    num_workers = 10
    barrier = threading.Barrier(num_workers)
    successes = []
    conflict_errors = []
    unexpected_errors = []
    threads = []

    def worker(worker_idx: int):
        try:
            try:
                barrier.wait(timeout=5.0)
            except threading.BrokenBarrierError:
                return

            new_id, _ = store.supersede(
                tenant, orig_id, "config", "workers", f"{10 + worker_idx}", authority_tier=20
            )
            successes.append(new_id)
        except ReplacementConflictError as e:
            conflict_errors.append(e)
        except Exception as e:
            unexpected_errors.append(e)

    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive(), "Worker thread hung in join"

    assert len(unexpected_errors) == 0, f"Unexpected errors found: {unexpected_errors}"
    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}"
    assert len(conflict_errors) == num_workers - 1, f"Expected {num_workers - 1} conflicts, got {len(conflict_errors)}"


def test_injected_connection_setup_failure_clean_teardown(tmp_path):
    """
    Injected setup failure must abort barrier immediately, clean up peers without hanging,
    and assert WorkerSetupError while strictly rejecting AttributeError or unexpected exceptions.
    """
    db_path = str(tmp_path / "setup_fail.db")
    store = SQLiteSharedMemoryStore(db_path)

    barrier = threading.Barrier(2)
    worker_errors: List[Exception] = []
    threads: List[threading.Thread] = []

    def worker_faulty():
        try:
            # Injected failure: worker fails initialization before barrier
            raise WorkerSetupError("Simulated connection setup failure")
            barrier.wait(timeout=2.0)
        except Exception as e:
            barrier.abort()
            worker_errors.append(e)

    def worker_healthy():
        try:
            conn = store.get_connection()
            try:
                barrier.wait(timeout=2.0)
            except threading.BrokenBarrierError:
                pass  # Clean exit on peer abort; NO AttributeError raised!
            finally:
                conn.close()
        except Exception as e:
            worker_errors.append(e)

    t1 = threading.Thread(target=worker_faulty)
    t2 = threading.Thread(target=worker_healthy)
    threads.extend([t1, t2])

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=3.0)
        assert not t.is_alive(), "Worker thread hung; join timed out"

    assert barrier.broken, "Barrier should be broken"
    # Strict validation: exactly 1 error, and it must be WorkerSetupError
    assert len(worker_errors) == 1
    assert isinstance(worker_errors[0], WorkerSetupError)
    # Reject AttributeError, TimeoutError, or conflict errors
    assert not any(isinstance(e, AttributeError) for e in worker_errors)
    assert not any(isinstance(e, ReplacementConflictError) for e in worker_errors)


def test_competing_replacement_worker_setup_failure_aborts_cleanly(store):
    """
    Exercises the barrier repair directly through the 10-worker competing-replacement path.
    One worker encounters an injected setup failure, aborts the barrier, and all 9 peer workers
    cleanly exit without hanging or raising unexpected exceptions.
    """
    tenant = "tenant_alpha"
    orig_id = store.create(tenant, "group", "group_1", "config", "pool_size", "8", authority_tier=20)

    num_workers = 10
    barrier = threading.Barrier(num_workers)
    successes = []
    worker_errors = []
    threads = []

    def competing_worker(idx: int):
        try:
            if idx == 0:
                # Injected setup failure in worker 0
                raise WorkerSetupError("Simulated worker connection failure in replacement pool")
                barrier.wait(timeout=3.0)
            else:
                # Healthy peer worker
                try:
                    barrier.wait(timeout=3.0)
                except threading.BrokenBarrierError:
                    return  # Clean exit on peer setup abort

                new_id, _ = store.supersede(
                    tenant, orig_id, "config", "pool_size", f"{100 + idx}", authority_tier=20
                )
                successes.append(new_id)
        except Exception as e:
            if idx == 0:
                barrier.abort()
            worker_errors.append(e)

    for i in range(num_workers):
        t = threading.Thread(target=competing_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=4.0)
        assert not t.is_alive(), f"Worker thread hung in join"

    assert barrier.broken, "Barrier must be broken following setup abort"
    assert len(successes) == 0, "No writes should occur when setup aborts the replacement pool"
    assert len(worker_errors) == 1, f"Expected exactly 1 worker error, got {len(worker_errors)}: {worker_errors}"
    assert isinstance(worker_errors[0], WorkerSetupError), f"Expected WorkerSetupError, got {type(worker_errors[0])}"
    assert not any(isinstance(e, (AttributeError, ReplacementConflictError)) for e in worker_errors)

