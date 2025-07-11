from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import UserMessage
from autogen_ext.memory.redis import RedisMemory, RedisMemoryConfig
from pydantic import ValidationError
from redisvl.exceptions import RedisSearchError


@pytest.fixture
def semantic_config() -> RedisMemoryConfig:
    """Create base configuration using semantic memory."""
    return RedisMemoryConfig(top_k=5, distance_threshold=0.5, model_name="sentence-transformers/all-mpnet-base-v2")


@pytest_asyncio.fixture
async def semantic_memory(semantic_config: RedisMemoryConfig) -> AsyncGenerator[RedisMemory]:
    memory = RedisMemory(semantic_config)
    yield memory
    await memory.close()


## UNIT TESTS ##
def test_memory_config() -> None:
    default_config = RedisMemoryConfig()
    assert default_config.redis_url == "redis://localhost:6379"
    assert default_config.index_name == "chat_history"
    assert default_config.prefix == "memory"
    assert default_config.distance_metric == "cosine"
    assert default_config.algorithm == "flat"
    assert default_config.top_k == 10
    assert default_config.distance_threshold == 0.7
    assert default_config.model_name == "sentence-transformers/all-mpnet-base-v2"

    # test we can specify each of these values
    url = "rediss://localhost:7010"
    name = "custom name"
    prefix = "custom prefix"
    metric = "ip"
    algorithm = "hnsw"
    k = 5
    distance = 0.25
    model = "redis/langcache-embed-v1"

    custom_config = RedisMemoryConfig(
        redis_url=url,
        index_name=name,
        prefix=prefix,
        distance_metric=metric,  # type: ignore[arg-type]
        algorithm=algorithm,  # type: ignore[arg-type]
        top_k=k,
        distance_threshold=distance,
        model_name=model,
    )
    assert custom_config.redis_url == url
    assert custom_config.index_name == name
    assert custom_config.prefix == prefix
    assert custom_config.distance_metric == metric
    assert custom_config.algorithm == algorithm
    assert custom_config.top_k == k
    assert custom_config.distance_threshold == distance
    assert custom_config.model_name == model

    # test that Literal values are validated correctly
    with pytest.raises(ValidationError):
        _ = RedisMemoryConfig(distance_metric="approximate")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        _ = RedisMemoryConfig(algorithm="pythagoras")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_semantic_memory() -> None:
    config = RedisMemoryConfig(index_name="semantic_agent")
    memory = RedisMemory(config=config)

    assert memory.message_history is not None
    await memory.close()


@pytest.mark.asyncio
async def test_update_context(semantic_memory: RedisMemory) -> None:
    """Test updating model context with retrieved memories."""
    await semantic_memory.clear()

    # Add content to memory
    await semantic_memory.add(
        MemoryContent(
            content="Canada is the second largest country in the world.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "geography"},
        )
    )

    # Create a model context with a message
    context = BufferedChatCompletionContext(buffer_size=5)
    await context.add_message(UserMessage(content="Tell me about Canada", source="user"))

    # Update context with memory
    result = await semantic_memory.update_context(context)

    # Verify results
    assert len(result.memories.results) > 0
    assert any("Canada" in str(r.content) for r in result.memories.results)

    # Verify context was updated
    messages = await context.get_messages()
    assert len(messages) > 1  # Should have the original message plus the memory content

    await semantic_memory.clear()

    await semantic_memory.add(
        MemoryContent(
            content="Napoleon was Emporor of France from 18 May 1804 to 6 April 1814.",
            mime_type=MemoryMimeType.TEXT,
            metadata={},
        )
    )
    await semantic_memory.add(
        MemoryContent(
            content="Napoleon was also Emporor during his second reign from 20 March 1815 to 22 June 1815.",
            mime_type=MemoryMimeType.TEXT,
            metadata={},
        )
    )

    context = BufferedChatCompletionContext(
        buffer_size=5,
        initial_messages=[
            UserMessage(content="Can you tell me about the reign of Emperor Napoleon?", source="user"),
        ],
    )

    updated_context = await semantic_memory.update_context(context)
    assert updated_context is not None
    assert updated_context.memories is not None
    assert updated_context.memories.results is not None
    assert len(updated_context.memories.results) == 2
    assert (
        updated_context.memories.results[0].content
        == "Napoleon was Emporor of France from 18 May 1804 to 6 April 1814."
    )
    assert (
        updated_context.memories.results[1].content
        == "Napoleon was also Emporor during his second reign from 20 March 1815 to 22 June 1815."
    )


@pytest.mark.asyncio
async def test_add_and_query(semantic_memory: RedisMemory) -> None:
    content_1 = MemoryContent(
        content="I enjoy fruits like apples, oranges, and bananas.", mime_type=MemoryMimeType.TEXT, metadata={}
    )
    await semantic_memory.add(content_1)

    # find matches with a similar query
    memories = await semantic_memory.query("Fruits that I like.")
    assert len(memories.results) == 1

    # don't return anything for dissimilar queries
    no_memories = await semantic_memory.query("The king of England")
    assert len(no_memories.results) == 0

    # match multiple relevant memories
    content_2 = MemoryContent(
        content="I also like mangos and pineapples.",
        mime_type=MemoryMimeType.TEXT,
        metadata={"description": "additional info"},
    )
    await semantic_memory.add(content_2)

    memories = await semantic_memory.query("Fruits that I like.")
    assert len(memories.results) == 2
    assert memories.results[0].metadata == {}
    assert memories.results[1].metadata == {"description": "additional info"}


@pytest.mark.asyncio
async def test_clear(semantic_memory: RedisMemory) -> None:
    content = MemoryContent(content="I enjoy fruits like apples, oranges, and bananas.", mime_type=MemoryMimeType.TEXT)
    await semantic_memory.add(content)

    # find matches with a similar query
    memories = await semantic_memory.query("Fruits that I like.")
    assert len(memories.results) == 1

    await semantic_memory.clear()
    # don't return anything for dissimilar queries
    no_memories = await semantic_memory.query("Fruits that I like.")
    assert len(no_memories.results) == 0


@pytest.mark.asyncio
async def test_close(semantic_config: RedisMemoryConfig) -> None:
    semantic_memory = RedisMemory(semantic_config)
    content = MemoryContent(content="This sentence should be deleted.", mime_type=MemoryMimeType.TEXT)
    await semantic_memory.add(content)

    await semantic_memory.close()

    with pytest.raises(RedisSearchError):
        _ = await semantic_memory.query("This query should fail.")


## INTEGRATION TESTS ##
@pytest.mark.asyncio
async def test_basic_workflow(semantic_config: RedisMemoryConfig) -> None:
    """Test basic memory operations with semantic memory."""
    memory = RedisMemory(config=semantic_config)
    await memory.clear()

    await memory.add(
        MemoryContent(
            content="Virginia Tech is the best engineering university in the state.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"topic": "higher education", "department": "engineering"},
        )
    )

    results = await memory.query("Which engineering university should I attend?")
    assert len(results.results) == 1
    assert any("engineering" in str(r.content) for r in results.results)
    assert all(isinstance(r.metadata, dict) for r in results.results if r.metadata)

    await memory.close()


@pytest.mark.asyncio
async def test_content_types(semantic_memory: RedisMemory) -> None:
    """Test different content types with semantic memory."""
    await semantic_memory.clear()

    # Test text content
    text_content = MemoryContent(content="Simple text content for testing", mime_type=MemoryMimeType.TEXT)
    await semantic_memory.add(text_content)

    # Query for text content
    results = await semantic_memory.query("simple text content")
    assert len(results.results) > 0
    assert any("Simple text content" in str(r.content) for r in results.results)

    # Test JSON content
    json_data = {"key": "value", "number": 42}
    json_content = MemoryContent(content=json_data, mime_type=MemoryMimeType.JSON)
    with pytest.raises(NotImplementedError):
        await semantic_memory.add(json_content)
