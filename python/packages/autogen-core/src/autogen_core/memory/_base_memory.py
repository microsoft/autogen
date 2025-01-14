from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Protocol, Union, runtime_checkable

from pydantic import BaseModel, ConfigDict

from .._cancellation_token import CancellationToken
from .._image import Image
from ..model_context import ChatCompletionContext


class MemoryMimeType(Enum):
    """Supported MIME types for memory content."""

    TEXT = "text/plain"
    JSON = "application/json"
    MARKDOWN = "text/markdown"
    IMAGE = "image/*"
    BINARY = "application/octet-stream"


ContentType = Union[str, bytes, Dict[str, Any], Image]


class MemoryContent(BaseModel):
    content: ContentType
    mime_type: MemoryMimeType | str
    metadata: Dict[str, Any] | None = None
    timestamp: datetime | None = None
    source: str | None = None
    score: float | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryQueryResult(BaseModel):
    results: List[MemoryContent]


class UpdateContextResult(BaseModel):
    memories: MemoryQueryResult


@runtime_checkable
class Memory(Protocol):
    """Protocol defining the interface for memory implementations."""

    @property
    def name(self) -> str | None:
        """The name of this memory implementation."""
        ...

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """
        Update the provided model context using relevant memory content.

        Args:
            model_context: The context to update.

        Returns:
            UpdateContextResult containing relevant memories
        """
        ...

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """
        Query the memory store and return relevant entries.

        Args:
            query: Query content item
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional implementation-specific parameters

        Returns:
            MemoryQueryResult containing memory entries with relevance scores
        """
        ...

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """
        Add a new content to memory.

        Args:
            content: The memory content to add
            cancellation_token: Optional token to cancel operation
        """
        ...

    async def clear(self) -> None:
        """Clear all entries from memory."""
        ...

    async def close(self) -> None:
        """Clean up any resources used by the memory implementation."""
        ...
