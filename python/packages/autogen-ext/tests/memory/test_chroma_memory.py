from pathlib import Path
from typing import Any

import pytest
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import UserMessage
from autogen_ext.memory.chromadb import (
    ChromaDBVectorMemory,
    CustomEmbeddingFunctionConfig,
    DefaultEmbeddingFunctionConfig,
    OpenAIEmbeddingFunctionConfig,
    PersistentChromaDBVectorMemoryConfig,
    SentenceTransformerEmbeddingFunctionConfig,
)


@pytest.fixture
def base_config(tmp_path: Path) -> PersistentChromaDBVectorMemoryConfig:
    """Create base configuration without score threshold."""
    return PersistentChromaDBVectorMemoryConfig(
        collection_name="test_collection", allow_reset=True, k=3, persistence_path=str(tmp_path / "chroma_db")
    )


@pytest.fixture
def strict_config(tmp_path: Path) -> PersistentChromaDBVectorMemoryConfig:
    """Create configuration with strict score threshold."""
    return PersistentChromaDBVectorMemoryConfig(
        collection_name="test_collection",
        allow_reset=True,
        k=3,
        score_threshold=0.8,  # High threshold for strict matching
        persistence_path=str(tmp_path / "chroma_db_strict"),
    )


@pytest.fixture
def lenient_config(tmp_path: Path) -> PersistentChromaDBVectorMemoryConfig:
    """Create configuration with lenient score threshold."""
    return PersistentChromaDBVectorMemoryConfig(
        collection_name="test_collection",
        allow_reset=True,
        k=3,
        score_threshold=0.0,  # No threshold for maximum retrieval
        persistence_path=str(tmp_path / "chroma_db_lenient"),
    )


@pytest.mark.asyncio
async def test_basic_workflow(base_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test basic memory operations with default threshold."""
    memory = ChromaDBVectorMemory(config=base_config)
    await memory.clear()

    await memory.add(
        MemoryContent(
            content="Paris is known for the Eiffel Tower and amazing cuisine.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "city", "country": "France"},
        )
    )

    results = await memory.query("Tell me about Paris")
    assert len(results.results) > 0
    assert any("Paris" in str(r.content) for r in results.results)
    assert all(isinstance(r.metadata.get("score"), float) for r in results.results if r.metadata)

    await memory.close()


@pytest.mark.asyncio
async def test_content_types(lenient_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test different content types with lenient matching."""
    memory = ChromaDBVectorMemory(config=lenient_config)
    await memory.clear()

    # Test text content
    text_content = MemoryContent(content="Simple text content for testing", mime_type=MemoryMimeType.TEXT)
    await memory.add(text_content)

    # Test JSON content
    json_data = {"key": "value", "number": 42}
    json_content = MemoryContent(content=json_data, mime_type=MemoryMimeType.JSON)
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
async def test_strict_matching(strict_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test matching behavior with high score threshold."""
    memory = ChromaDBVectorMemory(config=strict_config)
    await memory.clear()

    await memory.add(
        MemoryContent(content="Specific technical details about quantum computing", mime_type=MemoryMimeType.TEXT)
    )

    # Exact query should match
    exact_results = await memory.query("quantum computing details")
    assert len(exact_results.results) > 0
    assert all(
        result.metadata and result.metadata.get("score", 0) >= strict_config.score_threshold
        for result in exact_results.results
    )

    # Unrelated query should not match due to high threshold
    unrelated_results = await memory.query("recipe for cake")
    assert len(unrelated_results.results) == 0

    await memory.close()


@pytest.mark.asyncio
async def test_metadata_handling(base_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test metadata handling with default threshold."""
    memory = ChromaDBVectorMemory(config=base_config)
    await memory.clear()

    test_content = "Test content with specific metadata"
    content = MemoryContent(
        content=test_content,
        mime_type=MemoryMimeType.TEXT,
        metadata={"test_category": "test", "test_priority": 1, "test_weight": 0.5, "test_verified": True},
    )
    await memory.add(content)

    results = await memory.query(test_content)
    assert len(results.results) > 0
    result = results.results[0]

    assert result.metadata is not None
    assert result.metadata.get("test_category") == "test"
    assert result.metadata.get("test_priority") == 1
    assert isinstance(result.metadata.get("test_weight"), float)
    assert result.metadata.get("test_verified") is True

    await memory.close()


@pytest.mark.asyncio
async def test_error_handling(base_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test error cases with default threshold."""
    memory = ChromaDBVectorMemory(config=base_config)
    await memory.clear()

    with pytest.raises(ValueError, match="Unsupported content type"):
        await memory.add(MemoryContent(content=b"binary data", mime_type=MemoryMimeType.BINARY))

    with pytest.raises(ValueError, match="JSON content must be a dict"):
        await memory.add(MemoryContent(content="not a dict", mime_type=MemoryMimeType.JSON))

    await memory.close()


@pytest.mark.asyncio
async def test_initialization(base_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test initialization with default threshold."""
    memory = ChromaDBVectorMemory(config=base_config)

    # Test that the collection_name property returns the expected value
    # This implicitly tests that initialization succeeds
    assert memory.collection_name == "test_collection"

    # Add something to verify the collection is working
    test_content = MemoryContent(content="Test initialization content", mime_type=MemoryMimeType.TEXT)
    await memory.add(test_content)

    # Verify we can query the added content
    results = await memory.query("Test initialization")
    assert len(results.results) > 0

    # Use the public reset method
    await memory.reset()

    # Verify the reset worked by checking that the previous content is gone
    results_after_reset = await memory.query("Test initialization")
    assert len(results_after_reset.results) == 0

    # Add new content to verify re-initialization happened automatically
    new_content = MemoryContent(content="New test content after reset", mime_type=MemoryMimeType.TEXT)
    await memory.add(new_content)

    # Verify we can query the new content
    new_results = await memory.query("New test")
    assert len(new_results.results) > 0

    await memory.close()


@pytest.mark.asyncio
async def test_model_context_update(base_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test updating model context with retrieved memories."""
    memory = ChromaDBVectorMemory(config=base_config)
    await memory.clear()

    # Add content to memory
    await memory.add(
        MemoryContent(
            content="Jupiter is the largest planet in our solar system.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "astronomy"},
        )
    )

    # Create a model context with a message
    context = BufferedChatCompletionContext(buffer_size=5)
    await context.add_message(UserMessage(content="Tell me about Jupiter", source="user"))

    # Update context with memory
    result = await memory.update_context(context)

    # Verify results
    assert len(result.memories.results) > 0
    assert any("Jupiter" in str(r.content) for r in result.memories.results)

    # Verify context was updated
    messages = await context.get_messages()
    assert len(messages) > 1  # Should have the original message plus the memory content

    await memory.close()


@pytest.mark.asyncio
async def test_component_serialization(base_config: PersistentChromaDBVectorMemoryConfig) -> None:
    """Test serialization and deserialization of the component."""
    memory = ChromaDBVectorMemory(config=base_config)

    # Serialize
    memory_config = memory.dump_component()
    assert memory_config.config["collection_name"] == base_config.collection_name

    # Deserialize
    loaded_memory = ChromaDBVectorMemory.load_component(memory_config)

    assert isinstance(loaded_memory, ChromaDBVectorMemory)

    await memory.close()
    await loaded_memory.close()


# ============================================================================
# Embedding Function Configuration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_default_embedding_function(tmp_path: Path) -> None:
    """Test ChromaDB memory with default embedding function."""
    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_default_embedding",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_default"),
        embedding_function_config=DefaultEmbeddingFunctionConfig(),
    )

    memory = ChromaDBVectorMemory(config=config)
    await memory.clear()

    # Add test content
    await memory.add(
        MemoryContent(
            content="Default embedding function test content",
            mime_type=MemoryMimeType.TEXT,
            metadata={"test": "default_embedding"},
        )
    )

    # Query and verify
    results = await memory.query("default embedding test")
    assert len(results.results) > 0
    assert any("Default embedding" in str(r.content) for r in results.results)

    await memory.close()


@pytest.mark.asyncio
async def test_sentence_transformer_embedding_function(tmp_path: Path) -> None:
    """Test ChromaDB memory with SentenceTransformer embedding function."""
    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_st_embedding",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_st"),
        embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
            model_name="all-MiniLM-L6-v2"  # Use default model for testing
        ),
    )

    memory = ChromaDBVectorMemory(config=config)
    await memory.clear()

    # Add test content
    await memory.add(
        MemoryContent(
            content="SentenceTransformer embedding function test content",
            mime_type=MemoryMimeType.TEXT,
            metadata={"test": "sentence_transformer"},
        )
    )

    # Query and verify
    results = await memory.query("SentenceTransformer embedding test")
    assert len(results.results) > 0
    assert any("SentenceTransformer" in str(r.content) for r in results.results)

    await memory.close()


@pytest.mark.asyncio
async def test_custom_embedding_function(tmp_path: Path) -> None:
    """Test ChromaDB memory with custom embedding function."""

    def create_mock_embedding_function() -> Any:
        """Create a mock embedding function for testing."""
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            # Return the default embedding function as our "custom" function for testing
            return DefaultEmbeddingFunction()
        except ImportError:
            pytest.skip("ChromaDB not available for custom embedding function test")
            return None  # This line will never be reached, but helps with type checking

    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_custom_embedding",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_custom"),
        embedding_function_config=CustomEmbeddingFunctionConfig(function=create_mock_embedding_function, params={}),
    )

    memory = ChromaDBVectorMemory(config=config)
    await memory.clear()

    # Add test content
    await memory.add(
        MemoryContent(
            content="Custom embedding function test content",
            mime_type=MemoryMimeType.TEXT,
            metadata={"test": "custom_embedding"},
        )
    )

    # Query and verify
    results = await memory.query("custom embedding test")
    assert len(results.results) > 0
    assert any("Custom embedding" in str(r.content) for r in results.results)

    await memory.close()


@pytest.mark.asyncio
async def test_embedding_function_error_handling(tmp_path: Path) -> None:
    """Test error handling for embedding function configurations."""

    def failing_embedding_function() -> None:
        """A function that raises an error."""
        raise ValueError("Test embedding function error")

    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_error_embedding",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_error"),
        embedding_function_config=CustomEmbeddingFunctionConfig(function=failing_embedding_function, params={}),
    )

    memory = ChromaDBVectorMemory(config=config)

    # Should raise an error when trying to initialize
    with pytest.raises(ValueError, match="Failed to create custom embedding function"):
        await memory.add(MemoryContent(content="This should fail", mime_type=MemoryMimeType.TEXT))

    await memory.close()


@pytest.mark.asyncio
async def test_sentence_transformer_error_handling(tmp_path: Path) -> None:
    """Test error handling for SentenceTransformer embedding function."""
    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_st_error",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_st_error"),
        embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
            model_name="nonexistent-model-that-should-fail"
        ),
    )

    memory = ChromaDBVectorMemory(config=config)

    # Should raise an ImportError when trying to use a nonexistent model
    with pytest.raises(ImportError, match="Failed to create SentenceTransformer embedding function"):
        await memory.add(MemoryContent(content="This should fail", mime_type=MemoryMimeType.TEXT))

    await memory.close()


@pytest.mark.asyncio
async def test_openai_error_handling(tmp_path: Path) -> None:
    """Test error handling for OpenAI embedding function."""
    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_openai_error",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_openai_error"),
        embedding_function_config=OpenAIEmbeddingFunctionConfig(
            api_key="invalid-key", model_name="nonexistent-model"
        ),
    )

    memory = ChromaDBVectorMemory(config=config)

    # Should raise an ImportError when trying to use invalid OpenAI config
    with pytest.raises(ImportError, match="Failed to create OpenAI embedding function"):
        await memory.add(MemoryContent(content="This should fail", mime_type=MemoryMimeType.TEXT))

    await memory.close()


@pytest.mark.asyncio
async def test_invalid_embedding_function_type(tmp_path: Path) -> None:
    """Test error handling for invalid embedding function type."""
    # Create a config with an invalid function_type by manually setting it
    config = PersistentChromaDBVectorMemoryConfig(
        collection_name="test_invalid_type",
        allow_reset=True,
        persistence_path=str(tmp_path / "chroma_db_invalid"),
        embedding_function_config=DefaultEmbeddingFunctionConfig(),
    )

    # Manually modify the function_type to an invalid value
    config.embedding_function_config.function_type = "invalid_type"  # type: ignore

    memory = ChromaDBVectorMemory(config=config)

    # Should raise a ValueError for unsupported function type
    with pytest.raises(ValueError, match="Unsupported embedding function type"):
        await memory.add(MemoryContent(content="This should fail", mime_type=MemoryMimeType.TEXT))

    await memory.close()


def test_embedding_function_config_validation() -> None:
    """Test validation of embedding function configurations."""

    # Test default config
    default_config = DefaultEmbeddingFunctionConfig()
    assert default_config.function_type == "default"

    # Test SentenceTransformer config
    st_config = SentenceTransformerEmbeddingFunctionConfig(model_name="test-model")
    assert st_config.function_type == "sentence_transformer"
    assert st_config.model_name == "test-model"

    # Test OpenAI config
    openai_config = OpenAIEmbeddingFunctionConfig(api_key="test-key", model_name="test-model")
    assert openai_config.function_type == "openai"
    assert openai_config.api_key == "test-key"
    assert openai_config.model_name == "test-model"

    # Test custom config
    def dummy_function() -> None:
        return None

    custom_config = CustomEmbeddingFunctionConfig(function=dummy_function, params={"test": "value"})
    assert custom_config.function_type == "custom"
    assert custom_config.function == dummy_function
    assert custom_config.params == {"test": "value"}
