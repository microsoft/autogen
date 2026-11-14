import base64
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from .._cancellation_token import CancellationToken
from .._component_config import ComponentBase
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

_BYTES_DATA_URI_PREFIX = "data:application/octet-stream;base64,"


def _convert_bytes_to_data_uri(data: bytes) -> str:
    """Encode ``bytes`` as a base64 data URI so JSON serialization is lossless."""
    return _BYTES_DATA_URI_PREFIX + base64.b64encode(data).decode("ascii")


class MemoryContent(BaseModel):
    """A memory content item."""

    content: ContentType
    """The content of the memory item. It can be a string, bytes, dict, or :class:`~autogen_core.Image`."""

    mime_type: MemoryMimeType | str
    """The MIME type of the memory content."""

    metadata: Dict[str, Any] | None = None
    """Metadata associated with the memory item."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("mime_type")
    def serialize_mime_type(self, mime_type: MemoryMimeType | str) -> str:
        """Serialize the MIME type to a string."""
        if isinstance(mime_type, MemoryMimeType):
            return mime_type.value
        return mime_type

    @field_serializer("content", when_used="json")
    def serialize_content(self, content: ContentType) -> Any:
        """Serialize ``bytes`` content as a base64 data URI so JSON mode is lossless.

        Without this, pydantic's JSON mode UTF-8 decodes ``bytes`` into ``str``
        (silently changing the type, or raising ``UnicodeDecodeError`` for
        non-UTF-8 data). Other content types are returned unchanged and are
        serialized by pydantic as usual.
        """
        if isinstance(content, bytes):
            return _convert_bytes_to_data_uri(content)
        return content

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: Any) -> Any:
        """Restore ``bytes`` content that was serialized as a base64 data URI."""
        if isinstance(value, str) and value.startswith(_BYTES_DATA_URI_PREFIX):
            return base64.b64decode(value[len(_BYTES_DATA_URI_PREFIX) :])
        return value


class MemoryQueryResult(BaseModel):
    """Result of a memory :meth:`~autogen_core.memory.Memory.query` operation."""

    results: List[MemoryContent]


class UpdateContextResult(BaseModel):
    """Result of a memory :meth:`~autogen_core.memory.Memory.update_context` operation."""

    memories: MemoryQueryResult


class Memory(ABC, ComponentBase[BaseModel]):
    """Protocol defining the interface for memory implementations.

    A memory is the storage for data that can be used to enrich or modify the model context.

    A memory implementation can use any storage mechanism, such as a list, a database, or a file system.
    It can also use any retrieval mechanism, such as vector search or text search.
    It is up to the implementation to decide how to store and retrieve data.

    It is also a memory implementation's responsibility to update the model context
    with relevant memory content based on the current model context and querying the memory store.

    See :class:`~autogen_core.memory.ListMemory` for an example implementation.
    """

    component_type = "memory"

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """
        Add a new content to memory.

        Args:
            content: The memory content to add
            cancellation_token: Optional token to cancel operation
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all entries from memory."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up any resources used by the memory implementation."""
        ...
