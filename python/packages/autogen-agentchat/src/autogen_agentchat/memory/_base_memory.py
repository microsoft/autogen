from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Protocol, Union, runtime_checkable

from autogen_core import CancellationToken, Image
from pydantic import BaseModel, ConfigDict, Field
from autogen_core.model_context import ChatCompletionContext


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
    mime_type: MemoryMimeType
    metadata: Dict[str, Any] | None = None
    timestamp: datetime | None = None
    source: str | None = None
    score: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseMemoryConfig(BaseModel):
    """Base configuration for memory implementations."""

    k: int = Field(default=5, description="Number of results to return")
    score_threshold: float | None = Field(
        default=None, description="Minimum relevance score")

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
    ) -> List[MemoryContent]:
        """
        Transform the provided model context using relevant memory content.

        Args:
            model_context: The context to transform

        Returns:
            List of memory entries with relevance scores
        """
        ...

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: "CancellationToken | None" = None,
        **kwargs: Any,
    ) -> List[MemoryContent]:
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

    async def add(self, content: MemoryContent, cancellation_token: "CancellationToken | None" = None) -> None:
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

    async def cleanup(self) -> None:
        """Clean up any resources used by the memory implementation."""
        ...
