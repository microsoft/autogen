from difflib import SequenceMatcher
from typing import Any, List

from autogen_core import CancellationToken, Image
from pydantic import Field

from ._base_memory import BaseMemoryConfig, ContentItem, Memory, MemoryEntry, MemoryQueryResult, MimeType
from autogen_core.model_context import (
    ChatCompletionContext
)
from autogen_core.models import (
    SystemMessage,
)


class ListMemoryConfig(BaseMemoryConfig):
    """Configuration for list-based memory implementation."""

    similarity_threshold: float = Field(
        default=0.0, description="Minimum similarity score for text matching", ge=0.0, le=1.0
    )


class ListMemory(Memory):
    """Simple list-based memory using text similarity matching."""

    def __init__(self, name: str | None = None, config: ListMemoryConfig | None = None) -> None:
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
        """Calculate text similarity score using SequenceMatcher."""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _extract_text(self, content_item: ContentItem) -> str:
        """Extract searchable text from ContentItem.

        Args:
            content_item: ContentItem to extract text from

        Returns:
            Extracted text string

        Raises:
            ValueError: If no text content can be extracted
        """
        content = content_item.content

        if content_item.mime_type in [MimeType.TEXT, MimeType.MARKDOWN]:
            return str(content)
        elif content_item.mime_type == MimeType.JSON:
            if isinstance(content, dict):
                return str(content)
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(
                f"Unsupported content type: {content_item.mime_type}")

    async def transform(
        self,
        model_context: ChatCompletionContext,
    ) -> ChatCompletionContext:
        """Transform the model context using relevant memory content."""
        messages = await model_context.get_messages()
        if not messages:
            return model_context

        last_message = messages[-1]
        query_text = getattr(last_message, "content", str(last_message))
        query = ContentItem(content=query_text, mime_type=MimeType.TEXT)

        results = []
        query_results = await self.query(query)
        for i, result in enumerate(query_results, 1):
            results.append(f"{i}. {result.entry.content}")

        if results:
            memory_context = "Results from memory query to consider include:\n" + \
                "\n".join(results)
            await model_context.add_message(SystemMessage(content=memory_context))

        return model_context

    async def query(
        self,
        query: ContentItem,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """Query memory entries based on text similarity."""
        try:
            query_text = self._extract_text(query)
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

    async def add(
        self,
        entry: MemoryEntry,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        """Add a new entry to memory."""
        self._entries.append(entry)

    async def clear(self) -> None:
        """Clear all entries from memory."""
        self._entries = []

    async def cleanup(self) -> None:
        """Clean up any resources used by the memory implementation."""
        # No resources to clean up in this implementation
        pass
