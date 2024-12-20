from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Protocol, Union, runtime_checkable

from autogen_core import CancellationToken, Image
from pydantic import BaseModel, ConfigDict, Field
from autogen_core.model_context import ChatCompletionContext


class MimeType(Enum):
    """Supported MIME types for memory content."""

    TEXT = "text/plain"
    JSON = "application/json"
    MARKDOWN = "text/markdown"
    IMAGE = "image/*"
    BINARY = "application/octet-stream"


ContentType = Union[str, bytes, dict, Image]


class MemoryContent(BaseModel):
    """A content item with type information."""

    content: ContentType
    mime_type: MimeType

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseMemoryConfig(BaseModel):
    """Base configuration for memory implementations."""

    k: int = Field(default=5, description="Number of results to return")
    score_threshold: float | None = Field(default=None, description="Minimum relevance score")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryEntry(BaseModel):
    """A memory entry containing content and metadata."""

    content: MemoryContent
    """The content item with type information."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Optional metadata associated with the memory entry."""

    timestamp: datetime = Field(default_factory=datetime.now)
    """When the memory was created."""

    source: str | None = None
    """Optional source identifier for the memory."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryQueryResult(BaseModel):
    """Result from a memory query including the entry and its relevance score."""

    entry: MemoryEntry
    """The memory entry."""

    score: float
    """Relevance score for this result. Higher means more relevant."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


@runtime_checkable
class Memory(Protocol):
    """Protocol defining the interface for memory implementations."""

    @property
    def name(self) -> str | None:
        """The name of this memory implementation."""
        ...

    @property
    def config(self) -> BaseMemoryConfig:
        """The configuration for this memory implementation."""
        ...

    async def transform(
        self,
        model_context: ChatCompletionContext,
    ) -> ChatCompletionContext:
        """
        Transform the model context using relevant memory content.

        Args:
            model_context: The context to transform

        Returns:
            The transformed context
        """
        ...

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: "CancellationToken | None" = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """
        Query the memory store and return relevant entries.

        Args:
            query: Query content item
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional implementation-specific parameters

        Returns:
            List of memory entries with relevance scores
        """
        ...

    async def add(self, entry: MemoryEntry, cancellation_token: "CancellationToken | None" = None) -> None:
        """
        Add a new entry to memory.

        Args:
            entry: The memory entry to add
            cancellation_token: Optional token to cancel operation
        """
        ...

    async def clear(self) -> None:
        """Clear all entries from memory."""
        ...

    async def cleanup(self) -> None:
        """Clean up any resources used by the memory implementation."""
        ...
