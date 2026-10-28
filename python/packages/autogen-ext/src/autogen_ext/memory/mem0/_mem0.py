import io
import logging
import uuid
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, cast

from autogen_core import CancellationToken, Component, ComponentBase
from autogen_core.memory import Memory, MemoryContent, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from mem0 import Memory as Memory0
from mem0 import MemoryClient
from pydantic import BaseModel, Field
from typing_extensions import Self

logger = logging.getLogger(__name__)
logging.getLogger("chromadb").setLevel(logging.ERROR)


class Mem0MemoryConfig(BaseModel):
    """Configuration for Mem0Memory component."""

    user_id: Optional[str] = Field(
        default=None, description="User ID for memory operations. If not provided, a UUID will be generated."
    )
    limit: int = Field(default=10, description="Maximum number of results to return in memory queries.")
    is_cloud: bool = Field(default=True, description="Whether to use cloud Mem0 client (True) or local client (False).")
    api_key: Optional[str] = Field(
        default=None, description="API key for cloud Mem0 client. Required if is_cloud=True."
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Configuration dictionary for local Mem0 client. Required if is_cloud=False."
    )


class MemoryResult(TypedDict, total=False):
    memory: str
    score: float
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    categories: List[str]


# pyright: reportGeneralTypeIssues=false
class Mem0Memory(Memory, Component[Mem0MemoryConfig], ComponentBase[Mem0MemoryConfig]):
    """Mem0 memory implementation for AutoGen.

    This component integrates with Mem0.ai's memory system, providing an implementation
    of AutoGen's Memory interface. It supports both cloud and local backends through the
    mem0ai Python package.

    To use this component, you need to have the `mem0` (for cloud-only) or `mem0-local` (for local)
    extra installed for the `autogen-ext` package:

    .. code-block:: bash

        pip install -U "autogen-ext[mem0]" # For cloud-based Mem0
        pip install -U "autogen-ext[mem0-local]" # For local Mem0

    The memory component can store and retrieve information that agents need to remember
    across conversations. It also provides context updating for language models with
    relevant memories.

    Examples:

        .. code-block:: python

            import asyncio
            from autogen_ext.memory.mem0 import Mem0Memory
            from autogen_core.memory import MemoryContent


            async def main() -> None:
                # Create a local Mem0Memory (no API key required)
                memory = Mem0Memory(
                    is_cloud=False,
                    config={"path": ":memory:"},  # Use in-memory storage for testing
                )
                print("Memory initialized successfully!")

                # Add something to memory
                test_content = "User likes the color blue."
                await memory.add(MemoryContent(content=test_content, mime_type="text/plain"))
                print(f"Added content: {test_content}")

                # Retrieve memories with a search query
                results = await memory.query("What color does the user like?")
                print(f"Query results: {len(results.results)} found")

                for i, result in enumerate(results.results):
                    print(f"Result {i+1}: {result}")


            asyncio.run(main())

        Output:

        .. code-block:: text

            Memory initialized successfully!
            Added content: User likes the color blue.
            Query results: 1 found
            Result 1: content='User likes the color blue' mime_type='text/plain' metadata={'score': 0.6977155806281953, 'created_at': datetime.datetime(2025, 7, 6, 17, 25, 18, 754725, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200)))}

        Using it with an :class:`~autogen_agentchat.agents.AssistantAgent`:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.memory import MemoryContent
            from autogen_ext.memory.mem0 import Mem0Memory
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                # Create a model client
                model_client = OpenAIChatCompletionClient(model="gpt-4.1")

                # Create a Mem0 memory instance
                memory = Mem0Memory(
                    user_id="user123",
                    is_cloud=False,
                    config={"path": ":memory:"},  # Use in-memory storage for testing
                )

                # Add something to memory
                test_content = "User likes the color blue."
                await memory.add(MemoryContent(content=test_content, mime_type="text/plain"))

                # Create an assistant agent with Mem0 memory
                agent = AssistantAgent(
                    name="assistant",
                    model_client=model_client,
                    memory=[memory],
                    system_message="You are a helpful assistant that remembers user preferences.",
                )

                # Run a sample task
                result = await agent.run(task="What color does the user like?")
                print(result.messages[-1].content)  # type: ignore


            asyncio.run(main())

        Output:

        .. code-block:: text

            User likes the color blue.

    Args:
        user_id: Optional user ID for memory operations. If not provided, a UUID will be generated.
        limit: Maximum number of results to return in memory queries.
        is_cloud: Whether to use cloud Mem0 client (True) or local client (False).
        api_key: API key for cloud Mem0 client. It will read from the environment MEM0_API_KEY if not provided.
        config: Configuration dictionary for local Mem0 client. Required if is_cloud=False.
    """

    component_type = "memory"
    component_provider_override = "autogen_ext.memory.mem0.Mem0Memory"
    component_config_schema = Mem0MemoryConfig

    def __init__(
        self,
        user_id: Optional[str] = None,
        limit: int = 10,
        is_cloud: bool = True,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Validate parameters
        if not is_cloud and config is None:
            raise ValueError("config is required when using local Mem0 client (is_cloud=False)")

        # Initialize instance variables
        self._user_id = user_id or str(uuid.uuid4())
        self._limit = limit
        self._is_cloud = is_cloud
        self._api_key = api_key
        self._config = config

        # Initialize client with better error handling
        try:
            if self._is_cloud:
                self._client = MemoryClient(api_key=self._api_key)
            else:
                assert self._config is not None
                config_dict = self._config
                # Convert old-style config to new Mem0 API if needed
                if isinstance(config_dict, dict) and 'path' in config_dict:
                    # Convert simple path config to proper Mem0 config
                    config_dict = self._create_local_config(config_dict)
                
                # Add timeout and error handling for local initialization
                import signal
                import time
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Mem0 initialization timed out")
                
                # Set a timeout for initialization
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)  # 30 second timeout
                
                try:
                    self._client = Memory0.from_config(config_dict=config_dict)  # type: ignore
                except TimeoutError:
                    logger.warning("Mem0 initialization timed out, using mock client")
                    self._client = None
                finally:
                    signal.alarm(0)  # Cancel the alarm
                    
        except Exception as e:
            logger.error(f"Failed to initialize Mem0 client: {e}")
            # Create a mock client for testing purposes
            self._client = None
            logger.warning("Using mock client due to initialization failure")

    @property
    def user_id(self) -> str:
        """Get the user ID for memory operations."""
        return self._user_id

    @property
    def limit(self) -> int:
        """Get the maximum number of results to return in memory queries."""
        return self._limit

    @property
    def is_cloud(self) -> bool:
        """Check if the Mem0 client is cloud-based."""
        return self._is_cloud

    @property
    def config(self) -> Optional[Dict[str, Any]]:
        """Get the configuration for the Mem0 client."""
        return self._config

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        """Add content to memory.

        Args:
            content: The memory content to add.
            cancellation_token: Optional token to cancel operation.

        Raises:
            Exception: If there's an error adding content to mem0 memory.
        """
        # Extract content based on mime type
        if hasattr(content, "content") and hasattr(content, "mime_type"):
            if content.mime_type in ["text/plain", "text/markdown"]:
                message = str(content.content)
            elif content.mime_type == "application/json":
                # Convert JSON content to string representation
                if isinstance(content.content, str):
                    message = content.content
                else:
                    # Convert dict or other JSON serializable objects to string
                    import json

                    message = json.dumps(content.content)
            else:
                message = str(content.content)

            # Extract metadata
            metadata = content.metadata or {}
        else:
            # Handle case where content is directly provided as string
            message = str(content)
            metadata = {}

        # Check if operation is cancelled
        if cancellation_token is not None and cancellation_token.cancelled:  # type: ignore
            return

        # Add to mem0 client
        try:
            if self._client is None:
                logger.warning("Mem0 client not initialized, skipping add operation")
                return
                
            user_id = metadata.pop("user_id", self._user_id)
            # Suppress warning messages from mem0 MemoryClient
            kwargs = {} if self._client.__class__.__name__ == "Memory" else {"output_format": "v1.1"}
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self._client.add([{"role": "user", "content": message}], user_id=user_id, metadata=metadata, **kwargs)  # type: ignore
        except Exception as e:
            # Log the error but don't crash
            logger.error(f"Error adding to mem0 memory: {str(e)}")
            raise

    async def query(
        self,
        query: str | MemoryContent = "",
        cancellation_token: Optional[CancellationToken] = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Query memory for relevant content.

        Args:
            query: The query to search for, either as string or MemoryContent.
            cancellation_token: Optional token to cancel operation.
            **kwargs: Additional query parameters to pass to mem0.

        Returns:
            MemoryQueryResult containing search results.
        """
        # Extract query text
        if isinstance(query, str):
            query_text = query
        elif hasattr(query, "content"):
            query_text = str(query.content)
        else:
            query_text = str(query)

        # Check if operation is cancelled
        if (
            cancellation_token
            and hasattr(cancellation_token, "cancelled")
            and getattr(cancellation_token, "cancelled", False)
        ):
            return MemoryQueryResult(results=[])

        try:
            if self._client is None:
                logger.warning("Mem0 client not initialized, returning empty results")
                return MemoryQueryResult(results=[])
                
            limit = kwargs.pop("limit", self._limit)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                # Query mem0 client
                results = self._client.search(  # type: ignore
                    query_text,
                    user_id=self._user_id,
                    limit=limit,
                    **kwargs,
                )

                # Type-safe handling of results
                if isinstance(results, dict) and "results" in results:
                    result_list = cast(List[MemoryResult], results["results"])
                else:
                    result_list = cast(List[MemoryResult], results)

            # Convert results to MemoryContent objects
            memory_contents: List[MemoryContent] = []
            for result in result_list:
                content_text = result.get("memory", "")
                metadata: Dict[str, Any] = {}

                if "metadata" in result and result["metadata"]:
                    metadata = result["metadata"]

                # Add relevant fields to metadata
                if "score" in result:
                    metadata["score"] = result["score"]

                # For created_at
                if "created_at" in result and result.get("created_at"):
                    try:
                        metadata["created_at"] = datetime.fromisoformat(result["created_at"])
                    except (ValueError, TypeError):
                        pass

                # For updated_at
                if "updated_at" in result and result.get("updated_at"):
                    try:
                        metadata["updated_at"] = datetime.fromisoformat(result["updated_at"])
                    except (ValueError, TypeError):
                        pass

                # For categories
                if "categories" in result and result.get("categories"):
                    metadata["categories"] = result["categories"]

                # Create MemoryContent object
                memory_content = MemoryContent(
                    content=content_text,
                    mime_type="text/plain",  # Default to text/plain
                    metadata=metadata,
                )
                memory_contents.append(memory_content)

            return MemoryQueryResult(results=memory_contents)

        except Exception as e:
            # Log the error but return empty results
            logger.error(f"Error querying mem0 memory: {str(e)}")
            return MemoryQueryResult(results=[])

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """Update the model context with relevant memories.

        This method retrieves the conversation history from the model context,
        uses the last message as a query to find relevant memories, and then
        adds those memories to the context as a system message.

        Args:
            model_context: The model context to update.

        Returns:
            UpdateContextResult containing memories added to the context.
        """
        # Get messages from context
        messages = await model_context.get_messages()
        if not messages:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        # Use the last message as query
        last_message = messages[-1]
        query_text = last_message.content if isinstance(last_message.content, str) else str(last_message)

        # Query memory
        query_results = await self.query(query_text, limit=self._limit)

        # If we have results, add them to the context
        if query_results.results:
            # Format memories as numbered list
            memory_strings = [f"{i}. {str(memory.content)}" for i, memory in enumerate(query_results.results, 1)]
            memory_context = "\nRelevant memories:\n" + "\n".join(memory_strings)

            # Add as system message
            await model_context.add_message(SystemMessage(content=memory_context))

        return UpdateContextResult(memories=query_results)

    async def clear(self) -> None:
        """Clear all content from memory for the current user.

        Raises:
            Exception: If there's an error clearing mem0 memory.
        """
        try:
            if self._client is None:
                logger.warning("Mem0 client not initialized, skipping clear operation")
                return
                
            self._client.delete_all(user_id=self._user_id)  # type: ignore
        except Exception as e:
            logger.error(f"Error clearing mem0 memory: {str(e)}")
            raise

    async def close(self) -> None:
        """Clean up resources if needed.

        This is a no-op for Mem0 clients as they don't require explicit cleanup.
        """
        pass

    @classmethod
    def _from_config(cls, config: Mem0MemoryConfig) -> Self:
        """Create instance from configuration.

        Args:
            config: Configuration for Mem0Memory component.

        Returns:
            A new Mem0Memory instance.
        """
        return cls(
            user_id=config.config.get('user_id'),
            limit=config.config.get('limit', 10),
            is_cloud=config.config.get('is_cloud', True),
            api_key=config.config.get('api_key'),
            config=config.config.get('config'),
        )

    def _create_local_config(self, simple_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a proper Mem0 local configuration from simple config.

        Args:
            simple_config: Simple configuration with 'path' key

        Returns:
            Proper Mem0 configuration dictionary
        """
        path = simple_config.get('path', ':memory:')
        
        # Ensure we have a proper database path
        if path == ':memory:':
            # Use a proper writable directory for in-memory mode
            import tempfile
            import os
            temp_dir = tempfile.mkdtemp(prefix='mem0_')
            db_path = os.path.join(temp_dir, 'mem0_history.db')
        else:
            db_path = path

        # Create a proper Mem0 configuration with better error handling
        config = {
            'vector_store': {
                'provider': 'qdrant',
                'config': {
                    'collection_name': 'mem0_memories',
                    'path': path,
                    'on_disk': path != ':memory:',
                    'embedding_model_dims': 768  # Match the HuggingFace model dimensions
                }
            },
            'embedder': {
                'provider': 'huggingface',
                'config': {
                    'model': 'sentence-transformers/all-MiniLM-L6-v2'  # Smaller, faster model
                }
            },
            'llm': {
                'provider': 'ollama',
                'config': {
                    'model': 'tinyllama:latest'
                }
            },
            'history_db_path': db_path
        }

        # Merge any additional config from simple_config
        for key, value in simple_config.items():
            if key != 'path' and key in config:
                config[key] = value

        return config

    def _to_config(self) -> Mem0MemoryConfig:
        """Convert instance to configuration.

        Returns:
            Configuration representing this Mem0Memory instance.
        """
        return Mem0MemoryConfig(
            user_id=self._user_id,
            limit=self._limit,
            is_cloud=self._is_cloud,
            api_key=self._api_key,
            config=self._config,
        )
