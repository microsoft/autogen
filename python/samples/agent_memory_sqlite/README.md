# Standalone SQLite Shared Memory Provider

A standalone, thread-safe SQLite shared memory provider for multi-agent systems, featuring:
- **Hierarchical Scopes:** Lexical scoping across `{agent, group, global}` tiers with SQL window ranking.
- **Bi-Temporal Lifecycle:** Soft-invalidation via `valid_from` and `valid_to` timestamps, preserving complete audit provenance.
- **Atomic Supersede:** Optimistic conditional replacement ensuring only active in-force records are superseded.
- **Trusted Context Binding:** `BoundSessionMemory` tool wrapper ensuring models cannot forge caller scope or authority tier.
- **Concurrency Rigor:** WAL mode and bounded barrier synchronization with setup error handling.

## Running Tests

From this directory:

```bash
pytest -v test_sqlite_shared_memory.py
```
