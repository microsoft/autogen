import os
import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import SystemMessage, UserMessage
from autogen_ext.memory.mem0 import Mem0Memory, Mem0MemoryConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Skip tests if required environment variables are not set
mem0_api_key = os.environ.get("MEM0_API_KEY")
requires_mem0_api = pytest.mark.skipif(mem0_api_key is None, reason="MEM0_API_KEY environment variable not set")

# Skip tests if mem0ai is not installed
mem0 = pytest.importorskip("mem0")

# Define local configuration at the top of the module
FULL_LOCAL_CONFIG: Dict[str, Any] = {
    "history_db_path": ":memory:",  # Use in-memory DB for tests
    "graph_store": {
        "provider": "mock_graph",
        "config": {"url": "mock://localhost:7687", "username": "mock", "password": "mock_password"},
    },
    "embedder": {
        "provider": "mock_embedder",
        "config": {
            "model": "mock-embedding-model",
            "embedding_dims": 1024,
            "api_key": "mock-api-key",
        },
    },
    "vector_store": {"provider": "mock_vector", "config": {"path": ":memory:", "collection_name": "test_memories"}},
    "llm": {
        "provider": "mock_llm",
        "config": {
            "model": "mock-chat-model",
            "api_key": "mock-api-key",
        },
    },
}


@pytest.fixture
def full_local_config() -> Dict[str, Any]:
    """Return the local configuration for testing."""
    return FULL_LOCAL_CONFIG


@pytest.fixture
def cloud_config() -> Mem0MemoryConfig:
    """Create cloud configuration with real API key."""
    api_key = os.environ.get("MEM0_API_KEY")
    return Mem0MemoryConfig(user_id="test-user", limit=3, is_cloud=True, api_key=api_key)


@pytest.fixture
def local_config() -> Mem0MemoryConfig:
    """Create local configuration for testing."""
    return Mem0MemoryConfig(user_id="test-user", limit=3, is_cloud=False, config={"path": ":memory:"})


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.Memory0")
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
            "metadata": {"category": "city", "country": "France"},
        }
    ]

    memory = Mem0Memory(
        user_id=local_config.user_id,
        limit=local_config.limit,
        is_cloud=local_config.is_cloud,
        api_key=local_config.api_key,
        config=local_config.config,
    )

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

    # Extract content from the list of dict structure: [{'content': '...', 'role': 'user'}]
    actual_content = call_args[0][0]['content']
    assert actual_content == "Paris is known for the Eiffel Tower and amazing cuisine."

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
    res_metadata = results.results[0].metadata
    assert res_metadata is not None and res_metadata.get("score") == 0.95
    assert res_metadata is not None and res_metadata.get("country") == "France"

    # Test clear (only do this once)
    await memory.clear()
    mock_mem0.delete_all.assert_called_once_with(user_id="test-user")

    # Cleanup
    await memory.close()


@requires_mem0_api
@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0.MemoryClient")  # Patch MemoryClient instead of Memory0
async def test_basic_workflow_with_cloud(mock_memory_client_class: MagicMock, cloud_config: Mem0MemoryConfig) -> None:
    """Test basic memory operations with cloud client (mocked instead of real API)."""
    # Setup mock
    mock_client = MagicMock()
    mock_memory_client_class.return_value = mock_client

    # Mock search results
    mock_client.search.return_value = [
        {
            "memory": "Test memory content for cloud",
            "score": 0.98,
            "metadata": {"test": True, "source": "cloud"},
        }
    ]

    memory = Mem0Memory(
        user_id=cloud_config.user_id,
        limit=cloud_config.limit,
        is_cloud=cloud_config.is_cloud,
        api_key=cloud_config.api_key,
        config=cloud_config.config,
    )

    # Generate a unique test content string
    test_content = f"Test memory content {uuid.uuid4()}"

    # Add content to memory
    await memory.add(
        MemoryContent(
            content=test_content,
            mime_type=MemoryMimeType.TEXT,
            metadata={"test": True, "timestamp": datetime.now().isoformat()},
        )
    )

    # Verify add was called correctly
    mock_client.add.assert_called_once()
    call_args = mock_client.add.call_args

    # Extract content from list of dict structure: [{'content': '...', 'role': 'user'}]
    actual_content = call_args[0][0][0]['content']  # call_args[0][0] gets the first positional arg (the list)
    assert test_content in actual_content

    assert call_args[1]["user_id"] == cloud_config.user_id
    assert call_args[1]["metadata"]["test"] is True

    # Query memory
    results = await memory.query(test_content)

    # Verify search was called correctly
    mock_client.search.assert_called_once()
    search_args = mock_client.search.call_args
    assert test_content in search_args[0][0]
    assert search_args[1]["user_id"] == cloud_config.user_id

    # Verify results
    assert len(results.results) == 1
    assert "Test memory content for cloud" in str(results.results[0].content)
    assert results.results[0].metadata is not None
    assert results.results[0].metadata.get("score") == 0.98

    # Test clear
    await memory.clear()
    mock_client.delete_all.assert_called_once_with(user_id=cloud_config.user_id)

    # Cleanup
    await memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.Memory0")
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
            "metadata": {"test_category": "test", "test_priority": 1, "test_weight": 0.5, "test_verified": True},
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-02T12:00:00",
            "categories": ["test", "example"],
        }
    ]

    memory = Mem0Memory(
        user_id=local_config.user_id,
        limit=local_config.limit,
        is_cloud=local_config.is_cloud,
        api_key=local_config.api_key,
        config=local_config.config,
    )

    # Add content with metadata
    test_content = "Test content with specific metadata"
    content = MemoryContent(
        content=test_content,
        mime_type=MemoryMimeType.TEXT,
        metadata={"test_category": "test", "test_priority": 1, "test_weight": 0.5, "test_verified": True},
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
    assert result.metadata is not None and result.metadata.get("test_category") == "test"
    assert result.metadata is not None and result.metadata.get("test_priority") == 1
    assert result.metadata is not None and isinstance(result.metadata.get("test_weight"), float)
    assert result.metadata is not None and result.metadata.get("test_verified") is True
    assert result.metadata is not None and "created_at" in result.metadata
    assert result.metadata is not None and "updated_at" in result.metadata
    assert result.metadata is not None and result.metadata.get("categories") == ["test", "example"]

    # Cleanup
    await memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.Memory0")
async def test_update_context(mock_mem0_class: MagicMock, local_config: Mem0MemoryConfig) -> None:
    """Test updating model context with retrieved memories."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Setup mock search results
    mock_mem0.search.return_value = [
        {"memory": "Jupiter is the largest planet in our solar system.", "score": 0.9},
        {"memory": "Jupiter has many moons, including Ganymede, Europa, and Io.", "score": 0.8},
    ]

    memory = Mem0Memory(
        user_id=local_config.user_id,
        limit=local_config.limit,
        is_cloud=local_config.is_cloud,
        api_key=local_config.api_key,
        config=local_config.config,
    )

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


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.MemoryClient")  # Patch for cloud mode
async def test_component_serialization(mock_memory_client_class: MagicMock) -> None:
    """Test serialization and deserialization of the component."""
    # Setup mock
    mock_client = MagicMock()
    mock_memory_client_class.return_value = mock_client

    # Create configuration
    user_id = str(uuid.uuid4())
    config = Mem0MemoryConfig(
        user_id=user_id,
        limit=5,
        is_cloud=True,
    )

    # Create memory instance
    memory = Mem0Memory(
        user_id=config.user_id,
        limit=config.limit,
        is_cloud=config.is_cloud,
        api_key=config.api_key,
        config=config.config,
    )

    # Dump config
    memory_config = memory.dump_component()

    # Verify dumped config
    assert memory_config.config["user_id"] == user_id
    assert memory_config.config["limit"] == 5
    assert memory_config.config["is_cloud"] is True

    # Load from config
    loaded_memory = Mem0Memory(
        user_id=config.user_id,
        limit=config.limit,
        is_cloud=config.is_cloud,
        api_key=config.api_key,
        config=config.config,
    )

    # Verify loaded instance
    assert isinstance(loaded_memory, Mem0Memory)
    assert loaded_memory.user_id == user_id
    assert loaded_memory.limit == 5
    assert loaded_memory.is_cloud is True
    assert loaded_memory.config is None

    # Cleanup
    await memory.close()
    await loaded_memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.Memory0")
async def test_result_format_handling(mock_mem0_class: MagicMock, local_config: Mem0MemoryConfig) -> None:
    """Test handling of different result formats."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Test dictionary format with "results" key
    mock_mem0.search.return_value = {
        "results": [
            {"memory": "Dictionary format result 1", "score": 0.9},
            {"memory": "Dictionary format result 2", "score": 0.8},
        ]
    }

    memory = Mem0Memory(
        user_id=local_config.user_id,
        limit=local_config.limit,
        is_cloud=local_config.is_cloud,
        api_key=local_config.api_key,
        config=local_config.config,
    )

    # Query with dictionary format
    results_dict = await memory.query("test query")

    # Verify results were extracted correctly
    assert len(results_dict.results) == 2
    assert "Dictionary format result 1" in str(results_dict.results[0].content)

    # Test list format
    mock_mem0.search.return_value = [
        {"memory": "List format result 1", "score": 0.9},
        {"memory": "List format result 2", "score": 0.8},
    ]

    # Query with list format
    results_list = await memory.query("test query")

    # Verify results were processed correctly
    assert len(results_list.results) == 2
    assert "List format result 1" in str(results_list.results[0].content)

    # Cleanup
    await memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.Memory0")
async def test_init_with_local_config(mock_mem0_class: MagicMock, full_local_config: Dict[str, Any]) -> None:
    """Test initializing memory with local configuration."""
    # Setup mock
    mock_mem0 = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0

    # Initialize memory with local config
    memory = Mem0Memory(user_id="test-local-config-user", limit=10, is_cloud=False, config=full_local_config)

    # Verify configuration was passed correctly
    mock_mem0_class.from_config.assert_called_once()

    # Verify memory instance properties (use type: ignore or add public properties)
    assert memory._user_id == "test-local-config-user"  # type: ignore
    assert memory._limit == 10  # type: ignore
    assert memory._is_cloud is False  # type: ignore
    assert memory._config == full_local_config  # type: ignore

    # Test serialization with local config
    memory_config = memory.dump_component()

    # Verify serialized config
    assert memory_config.config["user_id"] == "test-local-config-user"
    assert memory_config.config["is_cloud"] is False

    # Cleanup
    await memory.close()


@pytest.mark.asyncio
@patch("autogen_ext.memory.mem0._mem0.Memory0")  # Patches the underlying mem0.Memory class
async def test_local_config_with_memory_operations(
        mock_mem0_class: MagicMock,
        full_local_config: Dict[str, Any],  # full_local_config fixture provides the mock config
) -> None:
    """Test memory operations with local configuration."""
    # Setup mock for the instance that will be created by Mem0Memory
    mock_mem0_instance = MagicMock()
    mock_mem0_class.from_config.return_value = mock_mem0_instance

    # Mock search results from the mem0 instance
    mock_mem0_instance.search.return_value = [
        {
            "memory": "Test local config memory content",
            "score": 0.92,
            "metadata": {"config_type": "local", "test_case": "advanced"},
        }
    ]

    # Initialize Mem0Memory with is_cloud=False and the full_local_config
    memory = Mem0Memory(user_id="test-local-config-user", limit=10, is_cloud=False, config=full_local_config)

    # Verify that mem0.Memory.from_config was called with the provided config
    mock_mem0_class.from_config.assert_called_once_with(config_dict=full_local_config)

    # Add memory content
    test_content_str = "Testing local configuration memory operations"
    await memory.add(
        MemoryContent(
            content=test_content_str,
            mime_type=MemoryMimeType.TEXT,
            metadata={"config_type": "local", "test_case": "advanced"},
        )
    )

    # Verify add was called on the mock_mem0_instance
    mock_mem0_instance.add.assert_called_once()

    # Query memory
    results = await memory.query("local configuration test")

    # Verify search was called on the mock_mem0_instance
    mock_mem0_instance.search.assert_called_once_with(
        "local configuration test", user_id="test-local-config-user", limit=10
    )

    # Verify results
    assert len(results.results) == 1
    assert "Test local config memory content" in str(results.results[0].content)
    res_metadata = results.results[0].metadata
    assert res_metadata is not None and res_metadata.get("score") == 0.92
    assert res_metadata is not None and res_metadata.get("config_type") == "local"

    # Test serialization with local config
    memory_config = memory.dump_component()

    # Verify serialized config
    assert memory_config.config["user_id"] == "test-local-config-user"
    assert memory_config.config["is_cloud"] is False
    assert "config" in memory_config.config
    assert memory_config.config["config"]["history_db_path"] == ":memory:"

    # Test clear
    await memory.clear()
    mock_mem0_instance.delete_all.assert_called_once_with(user_id="test-local-config-user")

    # Cleanup
    await memory.close()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])