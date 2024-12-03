from difflib import SequenceMatcher
from typing import Any, List, Union

from autogen_core.base import CancellationToken
from autogen_core.components import Image
from pydantic import Field

from ._base_memory import BaseMemoryConfig, Memory, MemoryEntry, MemoryQueryResult


class ListMemoryConfig(BaseMemoryConfig):
    """Configuration for list-based memory implementation."""

    similarity_threshold: float = Field(
        default=0.0, description="Minimum similarity score for text matching", ge=0.0, le=1.0
    )


class ListMemory(Memory):
    """Simple list-based memory using text similarity matching."""

    def __init__(self, name: str | None = None, config: ListMemoryConfig | None = None) -> None:
        """Initialize list memory.

        Args:
            name: Name of the memory instance
            config: Optional configuration, uses defaults if not provided
        """
        self._name = name or "default_list_memory"
        self._config = config or ListMemoryConfig()
        self._entries: List[MemoryEntry] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> ListMemoryConfig:
        return self._config

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score using SequenceMatcher.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0 and 1
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _extract_text(self, content: Union[str, List[Union[str, Image]]]) -> str:
        """Extract searchable text from content.

        Args:
            content: Content to extract text from

        Returns:
            Extracted text string

        Raises:
            ValueError: If no text content can be extracted
        """
        if isinstance(content, str):
            return content

        text_parts = [item for item in content if isinstance(item, str)]
        if not text_parts:
            raise ValueError("Content must contain at least one text element")

        return " ".join(text_parts)

    async def query(
        self,
        query: Union[str, Image, List[Union[str, Image]]],
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """Query memory entries based on text similarity.

        Args:
            query: Query text or content
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional query parameters (unused)

        Returns:
            List of memory entries with similarity scores

        Raises:
            ValueError: If query contains unsupported content types
        """
        if isinstance(query, (str, Image)):
            query_content = [query]
        else:
            query_content = query

        try:
            query_text = self._extract_text(query_content)
        except ValueError:
            raise ValueError("Query must contain text content")

        results: List[MemoryQueryResult] = []

        for entry in self._entries:
            try:
                content_text = self._extract_text(entry.content)
            except ValueError:
                continue

            score = self._calculate_similarity(query_text, content_text)

            if score >= self._config.similarity_threshold and (
                self._config.score_threshold is None or score >= self._config.score_threshold
            ):
                results.append(MemoryQueryResult(entry=entry, score=score))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[: self._config.k]

    async def add(self, entry: MemoryEntry, cancellation_token: CancellationToken | None = None) -> None:
        """Add a new entry to memory.

        Args:
            entry: Memory entry to add
            cancellation_token: Optional token to cancel operation
        """
        self._entries.append(entry)

    async def clear(self) -> None:
        """Clear all entries from memory."""
        self._entries = []
