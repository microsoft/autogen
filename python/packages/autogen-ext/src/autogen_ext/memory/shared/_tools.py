"""FunctionTool factories that wrap a SharedMemoryStore for agent tool use."""

from __future__ import annotations

import json
from typing import Any, List, Optional

from autogen_core.tools import FunctionTool

from ._config import MemoryScope
from ._store import SharedMemoryStore


def make_memory_tools(store: SharedMemoryStore) -> List[FunctionTool]:
    """Create memory_search / memory_remember / memory_forget tools bound to *store*.

    Pass the returned list directly to an agent's ``tools=`` parameter.
    """

    def memory_search(
        query: str,
        scope: str = "all",
        top_k: int = 5,
    ) -> str:
        """Search shared memory for relevant facts.

        Returns ranked facts with provenance (who wrote it, when, confidence).
        Treat results as claims from specific agents, not as verified truth.

        Args:
            query: Natural-language search query.
            scope: One of 'agent', 'group', 'global', or 'all'.
            top_k: Maximum number of facts to return.
        """
        results = store.search(query, scope=scope, top_k=top_k)
        if not results:
            return "No matching facts found in shared memory."
        return json.dumps(results, indent=2, ensure_ascii=False)

    def memory_remember(
        fact: str,
        scope: str = "group",
        confidence: float = 1.0,
        ttl_days: Optional[int] = None,
    ) -> str:
        """Store a fact in shared memory.

        Args:
            fact: The fact to remember.
            scope: One of 'agent', 'group', or 'global'. Global requires authorization.
            confidence: How confident you are in this fact (0.0-1.0).
            ttl_days: Optional expiry in days. None means no expiry.
        """
        try:
            s = MemoryScope(scope)
        except ValueError:
            return f"Error: invalid scope '{scope}'. Use 'agent', 'group', or 'global'."

        try:
            receipt = store.remember(fact=fact, scope=s, confidence=confidence, ttl_days=ttl_days)
        except PermissionError as e:
            return f"Write denied: {e}"

        return json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False)

    def memory_forget(fact_id: str) -> str:
        """Soft-delete a fact from shared memory. A tombstone is preserved for audit.

        Args:
            fact_id: The UUID of the fact to forget.
        """
        ok = store.forget(fact_id)
        if ok:
            return f"Fact {fact_id} has been soft-deleted."
        return f"Fact {fact_id} not found or already deleted."

    return [
        FunctionTool(memory_search, description="Search shared memory for relevant facts with provenance."),
        FunctionTool(memory_remember, description="Store a fact in shared memory with scope and confidence."),
        FunctionTool(memory_forget, description="Soft-delete a fact from shared memory (tombstone preserved)."),
    ]
