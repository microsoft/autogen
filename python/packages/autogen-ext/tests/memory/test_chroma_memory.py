import pytest
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import UserMessage
from chromadb.api import ClientAPI

from autogen_ext.memory.chromadb import ChromaMemory, ChromaMemoryConfig, ChromaMemoryContent


@pytest.fixture
def base_config():
    """Create base configuration without score threshold."""
    return ChromaMemoryConfig(
        collection_name="test_collection",
        allow_reset=True,
        k=3
    )


@pytest.fixture
def strict_config():
    """Create configuration with strict score threshold."""
    return ChromaMemoryConfig(
        collection_name="test_collection",
        allow_reset=True,
        k=3,
        score_threshold=0.8  # High threshold for strict matching
    )


@pytest.fixture
def lenient_config():
    """Create configuration with lenient score threshold."""
    return ChromaMemoryConfig(
        collection_name="test_collection",
        allow_reset=True,
        k=3,
        score_threshold=0.0  # No threshold for maximum retrieval
    )


@pytest.mark.asyncio
async def test_basic_workflow(base_config):
    """Test basic memory operations with default threshold."""
    memory = ChromaMemory(name="test_memory", config=base_config)
    await memory.clear()

    await memory.add(
        MemoryContent(
            content="Paris is known for the Eiffel Tower and amazing cuisine.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "city", "country": "France"}
        )
    )

    results = await memory.query("Tell me about Paris")
    assert len(results.results) > 0
    assert any("Paris" in str(r.content) for r in results.results)
    assert all(isinstance(r, ChromaMemoryContent) for r in results.results)
    assert all(isinstance(r.score, float) for r in results.results)

    await memory.close()


@pytest.mark.asyncio
async def test_content_types(lenient_config):
    """Test different content types with lenient matching."""
    memory = ChromaMemory(name="test_memory", config=lenient_config)
    await memory.clear()

    # Test text content
    text_content = MemoryContent(
        content="Simple text content for testing",
        mime_type=MemoryMimeType.TEXT
    )
    await memory.add(text_content)

    # Test JSON content
    json_data = {"key": "value", "number": 42}
    json_content = MemoryContent(
        content=json_data,
        mime_type=MemoryMimeType.JSON
    )
    await memory.add(json_content)

    # Query for text content
    results = await memory.query("simple text content")
    assert len(results.results) > 0
    assert any("Simple text content" in str(r.content) for r in results.results)

    # Query for JSON content
    results = await memory.query("value")
    result_contents = [str(r.content).lower() for r in results.results]
    assert any("value" in content for content in result_contents)

    await memory.close()


@pytest.mark.asyncio
async def test_strict_matching(strict_config):
    """Test matching behavior with high score threshold."""
    memory = ChromaMemory(name="test_memory", config=strict_config)
    await memory.clear()

    await memory.add(
        MemoryContent(
            content="Specific technical details about quantum computing",
            mime_type=MemoryMimeType.TEXT
        )
    )

    # Exact query should match
    exact_results = await memory.query("quantum computing details")
    assert len(exact_results.results) > 0
    assert all(r.score >= strict_config.score_threshold for r in exact_results.results)

    # Unrelated query should not match due to high threshold
    unrelated_results = await memory.query("recipe for cake")
    assert len(unrelated_results.results) == 0

    await memory.close()


@pytest.mark.asyncio
async def test_metadata_handling(base_config):
    """Test metadata handling with default threshold."""
    memory = ChromaMemory(name="test_memory", config=base_config)
    await memory.clear()

    test_content = "Test content with specific metadata"
    content = MemoryContent(
        content=test_content,
        mime_type=MemoryMimeType.TEXT,
        metadata={
            "test_category": "test",
            "test_priority": 1,
            "test_weight": 0.5,
            "test_verified": True
        }
    )
    await memory.add(content)

    results = await memory.query(test_content)
    assert len(results.results) > 0
    result = results.results[0]
    
    assert result.metadata.get("test_category") == "test"
    assert result.metadata.get("test_priority") == 1
    assert isinstance(result.metadata.get("test_weight"), float)
    assert result.metadata.get("test_verified") is True

    await memory.close()


@pytest.mark.asyncio
async def test_error_handling(base_config):
    """Test error cases with default threshold."""
    memory = ChromaMemory(name="test_memory", config=base_config)
    await memory.clear()

    with pytest.raises(ValueError, match="Unsupported content type"):
        await memory.add(
            MemoryContent(
                content=b"binary data",
                mime_type=MemoryMimeType.BINARY
            )
        )

    with pytest.raises(ValueError, match="JSON content must be a dict"):
        await memory.add(
            MemoryContent(
                content="not a dict",
                mime_type=MemoryMimeType.JSON
            )
        )

    await memory.close()


@pytest.mark.asyncio
async def test_initialization(base_config):
    """Test initialization with default threshold."""
    memory = ChromaMemory(name="test_memory", config=base_config)
    memory._ensure_initialized()
    
    assert isinstance(memory._client, ClientAPI)
    assert memory._collection is not None
    assert memory._collection.name == "test_collection"

    await memory.reset()
    assert memory._collection is None

    memory._ensure_initialized()
    assert memory._collection is not None

    await memory.close()