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
from pydantic import BaseModel, Field
from typing_extensions import Self

try:
    from mem0 import Memory as Memory0
    from mem0 import MemoryClient
except ImportError as e:
    raise ImportError("`mem0ai` not installed. Please install it with `pip install mem0ai`") from e

logger = logging.getLogger(__name__)
logging.getLogger("chromadb").setLevel(logging.ERROR)


class Mem0MemoryConfig(BaseModel):
    """Configuration for Mem0Memory component.

    Attributes:
        user_id: Optional user ID for memory operations. If not provided, a UUID will be generated.
        limit: Maximum number of results to return in memory queries.
        is_cloud: Whether to use cloud Mem0 client (True) or local client (False).
        api_key: API key for cloud Mem0 client. Required if is_cloud=True.
        config: Configuration dictionary for local Mem0 client. Required if is_cloud=False.
    """

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

    The memory component can store and retrieve information that agents need to remember
    across conversations. It also provides context updating for language models with
    relevant memories.

    Examples:
        ```python
        # Create a cloud Mem0Memory
        memory = Mem0Memory(is_cloud=True)

        # Add something to memory
        await memory.add(MemoryContent(content="Important information to remember"))

        # Retrieve memories with a search query
        results = await memory.query("relevant information")
        ```
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
        """Initialize Mem0Memory.

        Args:
            user_id: Optional user ID for memory operations. If not provided, a UUID will be generated.
            limit: Maximum number of results to return in memory queries.
            is_cloud: Whether to use cloud Mem0 client (True) or local client (False).
            api_key: API key for cloud Mem0 client. It will read from the environment MEM0_API_KEY if not provided.
            config: Configuration dictionary for local Mem0 client. Required if is_cloud=False.

        Raises:
            ValueError: If is_cloud=True and api_key is None, or if is_cloud=False and config is None.
        """
        # Validate parameters
        if not is_cloud and config is None:
            raise ValueError("config is required when using local Mem0 client (is_cloud=False)")

        # Initialize instance variables
        self._user_id = user_id or str(uuid.uuid4())
        self._limit = limit
        self._is_cloud = is_cloud
        self._api_key = api_key
        self._config = config

        # Initialize client
        if self._is_cloud:
            self._client = MemoryClient(api_key=self._api_key)
        else:
            assert self._config is not None
            config_dict = self._config
            self._client = Memory0.from_config(config_dict=config_dict)  # type: ignore

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
            user_id = metadata.pop("user_id", self._user_id)
            # Suppress warning messages from mem0 MemoryClient
            kwargs = {} if self._client.__class__.__name__ == 'Memory' else {"output_format": "v1.1"}
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self._client.add(message, user_id=user_id, metadata=metadata, **kwargs)  # type: ignore
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
            user_id=config.user_id,
            limit=config.limit,
            is_cloud=config.is_cloud,
            api_key=config.api_key,
            config=config.config,
        )

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
