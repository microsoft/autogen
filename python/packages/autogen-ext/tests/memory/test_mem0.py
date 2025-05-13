import uuid
from unittest.mock import patch, MagicMock
import os
from dotenv import load_dotenv

import asyncio
import pytest
from datetime import datetime

from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import UserMessage, SystemMessage
from autogen_ext.memory.mem0 import Mem0Memory, Mem0MemoryConfig


# Load environment variables from .env file
load_dotenv()

# Skip tests if required environment variables are not set
mem0_api_key = os.environ.get("MEM0_API_KEY")
requires_mem0_api = pytest.mark.skipif(
    mem0_api_key is None,
    reason="MEM0_API_KEY environment variable not set"
)

# Skip tests if mem0ai is not installed
mem0 = pytest.importorskip("mem0")


@pytest.fixture
def cloud_config() -> Mem0MemoryConfig:
    """Create cloud configuration with real API key."""
    api_key = os.environ.get("MEM0_API_KEY")
    return Mem0MemoryConfig(
        user_id="test-user",
        limit=3,
        is_cloud=True,
        api_key=api_key
    )


@pytest.fixture
def local_config() -> Mem0MemoryConfig:
    """Create local configuration for testing."""
    return Mem0MemoryConfig(
        user_id="test-user",
        limit=3,
        is_cloud=False,
        config={"path": ":memory:"}
    )


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0.Memory0")
async def test_basic_workflow(mock_mem0_class: MagicMock, local_config: Mem0MemoryConfig) -> None:
    """Test basic memory operations."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Mock search results
    mock_mem0.search.return_value = [
        {
            "memory": "Paris is known for the Eiffel Tower and amazing cuisine.",
            "score": 0.95,
            "metadata": {"category": "city", "country": "France"}
        }
    ]

    memory = Mem0Memory._from_config(local_config)

    # Add content to memory
    await memory.add(
        MemoryContent(
            content="Paris is known for the Eiffel Tower and amazing cuisine.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "city", "country": "France"},
        )
    )

    # Verify add was called correctly
    mock_mem0.add.assert_called_once()
    call_args = mock_mem0.add.call_args[0]
    assert call_args[0] == "Paris is known for the Eiffel Tower and amazing cuisine."
    call_kwargs = mock_mem0.add.call_args[1]
    assert call_kwargs["metadata"] == {"category": "city", "country": "France"}

    # Query memory
    results = await memory.query("Tell me about Paris")

    # Verify search was called correctly
    mock_mem0.search.assert_called_once()
    search_args = mock_mem0.search.call_args
    assert search_args[0][0] == "Tell me about Paris"
    assert search_args[1]["user_id"] == "test-user"
    assert search_args[1]["limit"] == 3

    # Verify results
    assert len(results.results) == 1
    assert "Paris" in str(results.results[0].content)
    assert results.results[0].metadata.get("score") == 0.95
    assert results.results[0].metadata.get("country") == "France"

    # Test clear (only do this once)
    await memory.clear()
    mock_mem0.delete_all.assert_called_once_with(user_id="test-user")

    # Cleanup
    await memory.close()


@requires_mem0_api
@pytest.mark.asyncio
async def test_basic_workflow_with_cloud(cloud_config: Mem0MemoryConfig) -> None:
    """Test basic memory operations with real API."""
    memory = Mem0Memory._from_config(cloud_config)

    # Clean up before testing
    await memory.clear()

    # Test adding content
    test_content = f"Test memory content {uuid.uuid4()}"
    await memory.add(
        MemoryContent(
            content=test_content,
            mime_type=MemoryMimeType.TEXT,
            metadata={"test": True, "timestamp": datetime.now().isoformat()}
        )
    )

    # Wait a moment for indexing
    await asyncio.sleep(1)

    # Test querying
    results = await memory.query(test_content)

    # Verify results
    assert len(results.results) > 0
    assert test_content in str(results.results[0].content)

    # Clean up after testing
    await memory.clear()
    await memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0.Memory0")
async def test_metadata_handling(mock_mem0_class: MagicMock, local_config: Mem0MemoryConfig) -> None:
    """Test metadata handling."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Setup mock search results with rich metadata
    mock_mem0.search.return_value = [
        {
            "memory": "Test content with metadata",
            "score": 0.9,
            "metadata": {
                "test_category": "test",
                "test_priority": 1,
                "test_weight": 0.5,
                "test_verified": True
            },
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-02T12:00:00",
            "categories": ["test", "example"]
        }
    ]

    memory = Mem0Memory._from_config(local_config)

    # Add content with metadata
    test_content = "Test content with specific metadata"
    content = MemoryContent(
        content=test_content,
        mime_type=MemoryMimeType.TEXT,
        metadata={
            "test_category": "test",
            "test_priority": 1,
            "test_weight": 0.5,
            "test_verified": True
        },
    )
    await memory.add(content)

    # Verify metadata was passed correctly
    add_kwargs = mock_mem0.add.call_args[1]
    assert add_kwargs["metadata"]["test_category"] == "test"
    assert add_kwargs["metadata"]["test_priority"] == 1
    assert add_kwargs["metadata"]["test_weight"] == 0.5
    assert add_kwargs["metadata"]["test_verified"] is True

    # Query and check returned metadata
    results = await memory.query(test_content)
    assert len(results.results) == 1
    result = results.results[0]

    # Verify metadata in results
    assert result.metadata is not None
    assert result.metadata.get("test_category") == "test"
    assert result.metadata.get("test_priority") == 1
    assert isinstance(result.metadata.get("test_weight"), float)
    assert result.metadata.get("test_verified") is True
    assert "created_at" in result.metadata
    assert "updated_at" in result.metadata
    assert result.metadata.get("categories") == ["test", "example"]

    # Cleanup
    await memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0.Memory0")
async def test_update_context(mock_mem0_class: MagicMock, local_config: Mem0MemoryConfig) -> None:
    """Test updating model context with retrieved memories."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Setup mock search results
    mock_mem0.search.return_value = [
        {"memory": "Jupiter is the largest planet in our solar system.", "score": 0.9},
        {"memory": "Jupiter has many moons, including Ganymede, Europa, and Io.", "score": 0.8}
    ]

    memory = Mem0Memory._from_config(local_config)

    # Create a model context with a message
    context = BufferedChatCompletionContext(buffer_size=5)
    await context.add_message(UserMessage(content="Tell me about Jupiter", source="user"))

    # Update context with memory
    result = await memory.update_context(context)

    # Verify results
    assert len(result.memories.results) == 2
    assert "Jupiter" in str(result.memories.results[0].content)

    # Verify search was called with correct query
    mock_mem0.search.assert_called_once()
    search_args = mock_mem0.search.call_args
    assert "Jupiter" in search_args[0][0]

    # Verify context was updated with a system message
    messages = await context.get_messages()
    assert len(messages) == 2  # Original message + system message with memories

    # Verify system message content
    system_message = messages[1]
    assert isinstance(system_message, SystemMessage)
    assert "Jupiter is the largest planet" in system_message.content
    assert "Jupiter has many moons" in system_message.content

    # Cleanup
    await memory.close()


def test_component_serialization() -> None:
    """Test serialization and deserialization of the component."""
    # Create configuration
    user_id = str(uuid.uuid4())
    config = Mem0MemoryConfig(
        user_id=user_id,
        limit=5,
        is_cloud=True,
    )

    # Create memory instance
    memory = Mem0Memory._from_config(config)

    # Dump config
    memory_config = memory.dump_component()

    # Verify dumped config
    assert memory_config.config["user_id"] == user_id
    assert memory_config.config["limit"] == 5
    assert memory_config.config["is_cloud"] is True

    # Load from config
    loaded_memory = Mem0Memory.load_component(memory_config)

    # Verify loaded instance
    assert isinstance(loaded_memory, Mem0Memory)
    assert loaded_memory._user_id == user_id
    assert loaded_memory._limit == 5
    assert loaded_memory._is_cloud is True
    assert loaded_memory._config is None


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0.Memory0")
async def test_result_format_handling(mock_mem0_class: MagicMock, local_config: Mem0MemoryConfig) -> None:
    """Test handling of different result formats."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Test dictionary format with "results" key
    mock_mem0.search.return_value = {
        "results": [
            {"memory": "Dictionary format result 1", "score": 0.9},
            {"memory": "Dictionary format result 2", "score": 0.8}
        ]
    }

    memory = Mem0Memory._from_config(local_config)

    # Query with dictionary format
    results_dict = await memory.query("test query")

    # Verify results were extracted correctly
    assert len(results_dict.results) == 2
    assert "Dictionary format result 1" in str(results_dict.results[0].content)

    # Test list format
    mock_mem0.search.return_value = [
        {"memory": "List format result 1", "score": 0.9},
        {"memory": "List format result 2", "score": 0.8}
    ]

    # Query with list format
    results_list = await memory.query("test query")

    # Verify results were processed correctly
    assert len(results_list.results) == 2
    assert "List format result 1" in str(results_list.results[0].content)

    # Cleanup
    await memory.close()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
