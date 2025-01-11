from datetime import datetime

import pytest
from autogen_core import CancellationToken
from autogen_core.memory import (
    ListMemory,
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.model_context import BufferedChatCompletionContext, ChatCompletionContext


def test_memory_protocol_attributes() -> None:
    """Test that Memory protocol has all required attributes."""
    # No changes needed here
    assert hasattr(Memory, "name")
    assert hasattr(Memory, "update_context")
    assert hasattr(Memory, "query")
    assert hasattr(Memory, "add")
    assert hasattr(Memory, "clear")
    assert hasattr(Memory, "close")


def test_memory_protocol_runtime_checkable() -> None:
    """Test that Memory protocol is properly runtime-checkable."""

    class ValidMemory:
        @property
        def name(self) -> str:
            return "test"

        async def update_context(self, context: ChatCompletionContext) -> UpdateContextResult:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        async def query(
            self, query: MemoryContent, cancellation_token: CancellationToken | None = None
        ) -> MemoryQueryResult:
            return MemoryQueryResult(results=[])

        async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
            pass

        async def clear(self) -> None:
            pass

        async def close(self) -> None:
            pass

    class InvalidMemory:
        pass

    assert isinstance(ValidMemory(), Memory)
    assert not isinstance(InvalidMemory(), Memory)


@pytest.mark.asyncio
async def test_list_memory_empty() -> None:
    """Test ListMemory behavior when empty."""
    memory = ListMemory(name="test_memory")
    context = BufferedChatCompletionContext(buffer_size=3)

    results = await memory.update_context(context)
    context_messages = await context.get_messages()
    assert len(results.memories.results) == 0
    assert len(context_messages) == 0

    query_results = await memory.query(MemoryContent(content="test", mime_type=MemoryMimeType.TEXT))
    assert len(query_results.results) == 0


@pytest.mark.asyncio
async def test_list_memory_add_and_query() -> None:
    """Test adding and querying memory contents."""
    memory = ListMemory()

    content1 = MemoryContent(content="test1", mime_type=MemoryMimeType.TEXT, timestamp=datetime.now())
    content2 = MemoryContent(content={"key": "value"}, mime_type=MemoryMimeType.JSON, timestamp=datetime.now())

    await memory.add(content1)
    await memory.add(content2)

    results = await memory.query(MemoryContent(content="query", mime_type=MemoryMimeType.TEXT))
    assert len(results.results) == 2
    assert results.results[0].content == "test1"
    assert results.results[1].content == {"key": "value"}


@pytest.mark.asyncio
async def test_list_memory_max_memories() -> None:
    """Test max_memories limit is enforced."""
    memory = ListMemory()

    for i in range(5):
        await memory.add(MemoryContent(content=f"test{i}", mime_type=MemoryMimeType.TEXT))

    results = await memory.query(MemoryContent(content="query", mime_type=MemoryMimeType.TEXT))
    assert len(results.results) == 5


@pytest.mark.asyncio
async def test_list_memory_update_context() -> None:
    """Test context updating with memory contents."""
    memory = ListMemory()
    context = BufferedChatCompletionContext(buffer_size=3)

    await memory.add(MemoryContent(content="test1", mime_type=MemoryMimeType.TEXT))
    await memory.add(MemoryContent(content="test2", mime_type=MemoryMimeType.TEXT))

    results = await memory.update_context(context)
    context_messages = await context.get_messages()
    assert len(results.memories.results) == 2
    assert len(context_messages) == 1
    assert "test1" in context_messages[0].content
    assert "test2" in context_messages[0].content


@pytest.mark.asyncio
async def test_list_memory_clear() -> None:
    """Test clearing memory contents."""
    memory = ListMemory()
    await memory.add(MemoryContent(content="test", mime_type=MemoryMimeType.TEXT))
    await memory.clear()

    results = await memory.query(MemoryContent(content="query", mime_type=MemoryMimeType.TEXT))
    assert len(results.results) == 0


@pytest.mark.asyncio
async def test_list_memory_content_types() -> None:
    """Test support for different content types."""
    memory = ListMemory()
    text_content = MemoryContent(content="text", mime_type=MemoryMimeType.TEXT)
    json_content = MemoryContent(content={"key": "value"}, mime_type=MemoryMimeType.JSON)
    binary_content = MemoryContent(content=b"binary", mime_type=MemoryMimeType.BINARY)

    await memory.add(text_content)
    await memory.add(json_content)
    await memory.add(binary_content)

    results = await memory.query(text_content)
    assert len(results.results) == 3
    assert isinstance(results.results[0].content, str)
    assert isinstance(results.results[1].content, dict)
    assert isinstance(results.results[2].content, bytes)
