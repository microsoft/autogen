from difflib import SequenceMatcher
from typing import Any, List, Union, cast

from autogen_core.base import CancellationToken
from autogen_core.components import Image

from ._base_memory import BaseMemory, MemoryEntry, MemoryQueryResult


class ListMemory(BaseMemory):
    """A simple list-based memory implementation using text similarity matching."""

    def __init__(self, name: str) -> None:
        """Initialize list memory.

        Args:
            name: Name of the memory instance
        """
        super().__init__(name)

    async def add(
        self,
        entry: MemoryEntry,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        """Add a new entry to memory.

        Args:
            entry: Memory entry to add
            cancellation_token: Optional token to cancel operation
        """
        self._entries.append(entry)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score using SequenceMatcher.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0 and 1
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    async def query(
        self,
        query: Union[str, Image, List[Union[str, Image]]],
        *,
        k: int = 5,
        score_threshold: float | None = None,
        **kwargs: Any
    ) -> List[MemoryQueryResult]:
        """Query memory entries based on text similarity.

        Args:
            query: Query text or content
            k: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            **kwargs: Additional query parameters (unused in this implementation)

        Returns:
            List of memory entries with similarity scores

        Raises:
            ValueError: If query contains unsupported content types
        """
        # Handle different query types
        if isinstance(query, str):
            query_text = query
        elif isinstance(query, list):
            # Extract text from multimodal query
            text_parts = [item for item in query if isinstance(item, str)]
            if not text_parts:
                raise ValueError(
                    "Query must contain at least one text element")
            query_text = " ".join(text_parts)
        else:
            raise ValueError("Image-only queries not supported in ListMemory")

        # Calculate similarity scores for all entries
        results: List[MemoryQueryResult] = []

        for entry in self._entries:
            if isinstance(entry.content, str):
                content_text = entry.content
            elif isinstance(entry.content, list):
                # Extract text from multimodal content
                text_parts = [
                    item for item in entry.content if isinstance(item, str)]
                if not text_parts:
                    continue
                content_text = " ".join(text_parts)
            else:
                continue

            score = self._calculate_similarity(query_text, content_text)

            if score_threshold is None or score >= score_threshold:
                results.append(
                    MemoryQueryResult(
                        entry=entry,
                        score=score
                    )
                )

        # Sort by score and return top k results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
