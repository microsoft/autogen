## Summary

Implementation of the `SharedMemoryStore` proposed in #7748 — a cross-agent shared memory store with scoped FTS recall for `autogen-ext`.

- **SQLite + FTS5 backend**, zero external dependencies (uses Python's built-in `sqlite3`)
- **Three scopes**: `agent` (private), `group` (per-team), `global` (cross-runtime)
- **Tool-shaped capsule recall** via `memory_search` / `memory_remember` / `memory_forget` — facts land in tool-result position, not prefix-loaded
- **Provenance on every read**: `created_by`, `scope`, `confidence`, `timestamp`, `fact_hash` — so consuming agents can distinguish claims from verified facts
- **Write authorization**: per-scope policy; `global` writes restricted by default (addressing the memory-poisoning concerns from @msaleme and @redbotster in #7748)
- **Soft-delete with tombstones** for audit trail
- **Configurable max capsule size** to bound recall payload

### v1 scope (per discussion in #7748)

This PR covers the minimal v1 shape the community converged on:
- [x] Global + group + agent scopes with FTS-only search (no embeddings)
- [x] Write receipts with provenance metadata
- [x] Per-scope write authorization
- [x] Optimistic concurrency via version field
- [x] `FunctionTool` factories for easy agent integration
- [x] Implements the `Memory` protocol — works with `AssistantAgent(memory=[...])`
- [ ] `should_recall_memory` policy hook (deferred — needs runtime integration discussion)
- [ ] Embedding column (intentionally deferred; FTS-first per @scosemicolon's suggestion)

## Test plan

- [x] 20 tests passing covering:
  - Remember/search round-trip with provenance
  - Scope isolation (agent facts invisible to other agents)
  - Group scope sharing across agents
  - Global write authorization (denied for unauthorized, allowed for authorized)
  - Soft-delete with tombstone preservation
  - Capsule size truncation
  - TTL expiry
  - Memory protocol compliance (`add`, `query`, `clear`)
  - FunctionTool integration (search, remember, forget via `run_json`)
  - File-backed SQLite persistence across store instances
