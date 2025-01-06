import logging
from difflib import SequenceMatcher
from typing import Any, List

from autogen_core import CancellationToken, Image
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import (
    SystemMessage,
)
from pydantic import Field

from .. import EVENT_LOGGER_NAME
from ._base_memory import BaseMemoryConfig, Memory, MemoryContent, MemoryMimeType

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class ListMemoryConfig(BaseMemoryConfig):
    """Configuration for list-based memory implementation."""

    similarity_threshold: float = Field(
        default=0.35, description="Minimum similarity score for text matching", ge=0.0, le=1.0
    )


class ListMemory(Memory):
    """Simple list-based memory using text similarity matching.

    This memory implementation stores contents in a list and retrieves them based on
    text similarity matching. It supports various content types and can transform
    model contexts by injecting relevant memory content.

    Example:
        ```python
        # Initialize memory with custom config
        memory = ListMemory(name="chat_history", config=ListMemoryConfig(similarity_threshold=0.7, k=3))

        # Add memory content
        content = MemoryContent(content="User prefers formal language", mime_type=MemoryMimeType.TEXT)
        await memory.add(content)

        # Transform a model context with memory
        context = await memory.transform(model_context)
        ```

    Attributes:
        name (str): Identifier for this memory instance
        config (ListMemoryConfig): Configuration controlling memory behavior
    """

    def __init__(self, name: str | None = None, config: ListMemoryConfig | None = None) -> None:
        self._name = name or "default_list_memory"
        self._config = config or ListMemoryConfig()
        self._contents: List[MemoryContent] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> ListMemoryConfig:
        return self._config

    async def transform(
        self,
        model_context: ChatCompletionContext,
    ) -> List[MemoryContent]:
        """Transform the model context by injecting relevant memory content.

        This method mutates the provided model_context by adding relevant memory content:

        1. Extracts the last message from the context
        2. Uses it to query memory for relevant content
        3. Formats matching content into a system message
        4. Mutates the context by adding the system message

        Args:
            model_context: The context to transform. Will be mutated if relevant
                memories exist.

        Returns:
            List[MemoryQueryResult]: A list of matching memory content with scores

        Example:
            ```python
            # Context will be mutated to include relevant memories
            context = await memory.transform(model_context)

            # Any subsequent model calls will see the injected memories
            messages = await context.get_messages()
            ```
        """
        messages = await model_context.get_messages()
        if not messages:
            return []

        # Extract query from last message
        last_message = messages[-1]
        query_text = last_message.content if isinstance(last_message.content, str) else str(last_message)
        query = MemoryContent(content=query_text, mime_type=MemoryMimeType.TEXT)

        # Query memory and format results
        results: List[str] = []
        query_results = await self.query(query)
        for i, result in enumerate(query_results, 1):
            if isinstance(result.content, str):
                results.append(f"{i}. {result.content}")
                event_logger.debug(f"Retrieved memory {i}. {result.content}, score: {result.score}")

        # Add memory results to context
        if results:
            memory_context = (
                "\n The following results were retrieved from memory for this task. You may choose to use them or not. :\n"
                + "\n".join(results)
                + "\n"
            )
            await model_context.add_message(SystemMessage(content=memory_context))

        return query_results

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryContent]:
        """Query memory content based on text similarity.

        Searches memory content using text similarity matching against the query.
        Only content exceeding the configured similarity threshold is returned,
        sorted by relevance score in descending order.

        Args:
            query: The content to match against memory content. Must contain
                text that can be compared against stored content.
            cancellation_token: Optional token to cancel long-running queries
            **kwargs: Additional parameters passed to the similarity calculation

        Returns:
            List[MemoryContent]: Matching content with similarity scores,
                sorted by score in descending order. Limited to config.k entries.

        Raises:
            ValueError: If query content cannot be converted to comparable text

        Example:
            ```python
            # Query memories similar to some text
            query = MemoryContent(content="What's the weather?", mime_type=MemoryMimeType.TEXT)
            results = await memory.query(query)

            # Check similarity scores
            for result in results:
                print(f"Score: {result.score}, Content: {result.content}")
            ```
        """
        try:
            query_text = self._extract_text(query)
        except ValueError as e:
            raise ValueError("Query must contain text content") from e

        results: List[MemoryContent] = []

        for content in self._contents:
            try:
                content_text = self._extract_text(content)
            except ValueError:
                continue

            score = self._calculate_similarity(query_text, content_text)

            if score >= self._config.similarity_threshold and (
                self._config.score_threshold is None or score >= self._config.score_threshold
            ):
                result_content = content.model_copy()
                result_content.score = score
                results.append(result_content)

        results.sort(key=lambda x: x.score if x.score is not None else float("-inf"), reverse=True)
        return results[: self._config.k]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score using SequenceMatcher.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            float: Similarity score between 0 and 1, where 1 means identical

        Note:
            Uses difflib's SequenceMatcher for basic text similarity.
            For production use cases, consider using more sophisticated
            similarity metrics or embeddings.
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _extract_text(self, content_item: MemoryContent) -> str:
        """Extract searchable text from MemoryContent.

        Converts various content types into text that can be used for
        similarity matching.

        Args:
            content_item: Content to extract text from

        Returns:
            str: Extracted text representation

        Raises:
            ValueError: If content cannot be converted to text

        Note:
            Currently supports TEXT, MARKDOWN, and JSON content types.
            Images and binary content cannot be converted to text.
        """
        content = content_item.content

        if content_item.mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            return str(content)
        elif content_item.mime_type == MemoryMimeType.JSON:
            if isinstance(content, dict):
                return str(content)
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(f"Unsupported content type: {content_item.mime_type}")

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """Add new content to memory.

        Args:
            content: Memory content to store
            cancellation_token: Optional token to cancel operation

        Note:
            Content is stored in chronological order. No deduplication is
            performed. For production use cases, consider implementing
            deduplication or content-based filtering.
        """
        self._contents.append(content)

    async def clear(self) -> None:
        """Clear all memory content."""
        self._contents = []

    async def cleanup(self) -> None:
        """Cleanup resources if needed."""
        pass
