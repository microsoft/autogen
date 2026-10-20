# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Thread-safe Speculative Cache for pre-executed tool results.

This module provides a singleton cache that stores results from speculatively
executed tools. When the model formally requests a tool, the cache is checked
first to provide near-instantaneous results.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cached result with metadata."""

    tool_name: str
    args_hash: str
    result: Any
    created_at: float
    ttl: float
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() - self.created_at > self.ttl


class SpeculativeCache:
    """Thread-safe singleton cache for speculative tool execution results.

    This cache stores pre-executed tool results that were triggered by the
    ReasoningSniffer during the model's reasoning phase. When a tool is
    formally called, the cache is checked first.

    The cache uses argument hashing to match pre-warmed results with actual
    tool calls, allowing for partial matches when full arguments aren't known
    during speculation.

    Example:
        >>> cache = SpeculativeCache.get_instance()
        >>> cache.store("web_search", {"query": "python docs"}, "search results")
        >>> result = cache.get("web_search", {"query": "python docs"})
        >>> print(result)
        search results
    """

    _instance: Optional["SpeculativeCache"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "SpeculativeCache":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: Dict[str, CacheEntry] = {}
            cls._instance._stats = {
                "hits": 0,
                "misses": 0,
                "stores": 0,
                "evictions": 0,
            }
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SpeculativeCache":
        """Get the singleton cache instance."""
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Mainly for testing."""
        cls._instance = None

    @staticmethod
    def _hash_args(args: Dict[str, Any]) -> str:
        """Create a consistent hash for tool arguments.

        Args:
            args: Dictionary of tool arguments.

        Returns:
            A hex digest hash of the arguments.
        """
        # Sort keys for consistent ordering
        serialized = json.dumps(args, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    def store(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        ttl: float = 30.0,
    ) -> None:
        """Store a speculatively executed tool result.

        Args:
            tool_name: Name of the tool that was executed.
            args: Arguments used for execution.
            result: The result of the tool execution.
            ttl: Time-to-live in seconds (default: 30s).
        """
        args_hash = self._hash_args(args)
        cache_key = f"{tool_name}:{args_hash}"

        entry = CacheEntry(
            tool_name=tool_name,
            args_hash=args_hash,
            result=result,
            created_at=time.time(),
            ttl=ttl,
        )

        self._cache[cache_key] = entry
        self._stats["stores"] += 1

        logger.debug(
            f"SpeculativeCache: Stored {tool_name} (hash={args_hash[:8]}..., ttl={ttl}s)"
        )

    def get(self, tool_name: str, args: Dict[str, Any]) -> Optional[Any]:
        """Retrieve a cached result if available and not expired.

        Args:
            tool_name: Name of the tool being called.
            args: Arguments for the tool call.

        Returns:
            The cached result if found and valid, None otherwise.
        """
        args_hash = self._hash_args(args)
        cache_key = f"{tool_name}:{args_hash}"

        entry = self._cache.get(cache_key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired():
            # Clean up expired entry
            del self._cache[cache_key]
            self._stats["evictions"] += 1
            self._stats["misses"] += 1
            logger.debug(f"SpeculativeCache: Expired entry for {tool_name}")
            return None

        # Cache hit!
        entry.hit_count += 1
        self._stats["hits"] += 1
        logger.info(
            f"SpeculativeCache: HIT for {tool_name} (latency saved, hit #{entry.hit_count})"
        )
        return entry.result

    def get_fuzzy(self, tool_name: str, query_hint: str) -> Optional[Any]:
        """Attempt fuzzy matching for speculative results.

        This is used when the exact arguments aren't known but we have a
        query hint from the ReasoningSniffer.

        Args:
            tool_name: Name of the tool.
            query_hint: Partial query string detected during reasoning.

        Returns:
            The cached result if a fuzzy match is found, None otherwise.
        """
        query_hint_lower = query_hint.lower()

        for cache_key, entry in self._cache.items():
            if not cache_key.startswith(f"{tool_name}:"):
                continue

            if entry.is_expired():
                continue

            # Check if the query hint might match this entry
            # This is a heuristic - the args might contain the hint
            if hasattr(entry, "result") and isinstance(entry.result, str):
                if query_hint_lower in entry.result.lower():
                    entry.hit_count += 1
                    self._stats["hits"] += 1
                    logger.info(
                        f"SpeculativeCache: FUZZY HIT for {tool_name} "
                        f"(hint='{query_hint[:30]}...')"
                    )
                    return entry.result

        self._stats["misses"] += 1
        return None

    def invalidate(self, tool_name: str) -> int:
        """Invalidate all cached entries for a specific tool.

        Args:
            tool_name: Name of the tool to invalidate.

        Returns:
            Number of entries invalidated.
        """
        keys_to_remove = [key for key in self._cache if key.startswith(f"{tool_name}:")]

        for key in keys_to_remove:
            del self._cache[key]

        self._stats["evictions"] += len(keys_to_remove)
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats["evictions"] += count
        logger.info(f"SpeculativeCache: Cleared {count} entries")

    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            Number of entries removed.
        """
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]

        self._stats["evictions"] += len(expired_keys)
        return len(expired_keys)

    @property
    def stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, stores, and evictions counts.
        """
        return dict(self._stats)

    @property
    def hit_rate(self) -> float:
        """Calculate the cache hit rate.

        Returns:
            Hit rate as a float between 0.0 and 1.0.
        """
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return self._stats["hits"] / total

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)
