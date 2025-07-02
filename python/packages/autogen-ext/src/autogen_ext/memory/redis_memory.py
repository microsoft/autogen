import logging
import uuid
from typing import Any, Dict, List, Literal

from autogen_core import CancellationToken, Component, Image
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from pydantic import BaseModel, Field
from typing_extensions import Self

logger = logging.getLogger(__name__)

try:
    from redis import Redis
    from redisvl.extensions.message_history import SemanticMessageHistory
    from redisvl.index import AsyncSearchIndex, SearchIndex
    from redisvl.query import RangeQuery
    from redisvl.query.filter import FilterExpression
    from redisvl.schema import IndexSchema
    from redisvl.utils.utils import current_timestamp, deserialize, serialize
    from redisvl.utils.vectorize.text.huggingface import HFTextVectorizer
except ImportError as e:
    raise ImportError("To use Redis Memory RedisVL must be installed. Run `pip install autogen-ext[redisvl]`") from e


class RedisMemoryConfig(BaseModel):
    """
    Configuration for Redis-based vector memory.

    This class defines the configuration options for using Redis as a vector memory store,
    supporting semantic memory. It allows customization of the Redis connection, index settings,
    similarity search parameters, and embedding model.

    Attributes:
        redis_url (str): URL of the Redis instance (default: "redis://localhost:6379").
        index_name (str): Name of the Redis collection or index (default: "chat_memory").
        prefix (str): Prefix for keys in the Redis collection (default: "memory").
        distance_metric (Literal["cosine", "ip", "l2"]): Distance metric for similarity search.
            cosine is default. "ip" is inner product. "l2" is euclidean distance.
        algorithm (Literal["flat", "hnsw"]): Vector search algorithm to use. flat is default. hnsw
            is an approximation using hierarchical navigable small world graph.
        top_k (int): Number of results to return in queries (default: 10).
        datatype (Literal["int8", "float16", "float32", "float64", "bfloat16"]): The data type to
            store the vector as (default: "float32").
        distance_threshold (float): Minimum similarity threshold for results (default: 0.7).
        model_name (str | None): Name of the embedding model to use for semantic memory
            (default: "sentence-transformers/all-mpnet-base-v2").
    """

    redis_url: str = Field(default="redis://localhost:6379", description="url of the Redis instance")
    index_name: str = Field(default="chat_history", description="Name of the Redis collection")
    prefix: str = Field(default="memory", description="prefix of the Redis collection")
    distance_metric: Literal["cosine", "ip", "l2"] = "cosine"
    algorithm: Literal["flat", "hnsw"] = "flat"
    top_k: int = Field(default=10, description="Number of results to return in queries")
    datatype: Literal["int8", "float16", "float32", "float64", "bfloat16"] = "float32"
    distance_threshold: float = Field(default=0.7, description="Minimum similarity score threshold")
    model_name: str | None = Field(
        default="sentence-transformers/all-mpnet-base-v2", description="Embedding model name"
    )


class RedisMemory(Memory, Component[RedisMemoryConfig]):
    """
    Store and retrieve memory using vector similarity search powered by RedisVL.

    `RedisMemory` provides a vector-based memory implementation that uses RedisVL for storing and
    retrieving content based on semantic similarity. It enhances agents with the ability to recall
    contextually relevant information during conversations by leveraging vector embeddings to find
    similar content.

    .. note::

        This implementation requires the RedisVL extra to be installed. Install with:
        `pip install autogen-ext[redisvl]`

    Args:
        config (RedisMemoryConfig | None): Configuration for the Redis memory.
            If None, defaults to a RedisMemoryConfig with recommended settings.
    """

    component_config_schema = RedisMemoryConfig
    component_provider_override = "autogen_ext.memory.redis_memory.RedisMemory"

    def __init__(self, config: RedisMemoryConfig | None = None) -> None:
        """Initialize RedisMemory."""
        self.config = config or RedisMemoryConfig()
        client = Redis.from_url(url=self.config.redis_url)

        self.message_history = SemanticMessageHistory(name=self.config.index_name, redis_client=client)

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """
        Update the model context with relevant memory content.

        This method retrieves memory content relevant to the last message in the context
        and adds it as a system message. This implementation uses the last message in the context
        as a query to find semantically similar memories and adds them all to the context as a
        single system message.

        Args:
            model_context (ChatCompletionContext): The model context to update with relevant
                memories.

        Returns:
            UpdateContextResult: Object containing the memories that were used to update the
                context.
        """
        messages = await model_context.get_messages()
        if messages:
            last_message = str(messages[-1].content)
        else:
            last_message = ""

        query_results = await self.query(last_message)

        stringified_messages = "\n\n".join([str(m.content) for m in query_results.results])

        await model_context.add_message(SystemMessage(content=stringified_messages))

        return UpdateContextResult(memories=query_results)

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """Add a memory content object to Redis.

        .. note::

        To perform semantic search over stored memories RedisMemory creates a vector embedding
        from the content field of a MemoryContent object. This content is assumed to be text, and
        is passed to the vector embedding model specified in RedisMemoryConfig.

        Args:
            content (MemoryContent): The memory content to store within Redis.
            cancellation_token (CancellationToken): Token passed to cease operation. Not used.
        """
        if content.mime_type != MemoryMimeType.TEXT:
            raise NotImplementedError(
                f"Error: {content.mime_type} is not supported. Only MemoryMimeType.TEXT is currently supported."
            )

        self.message_history.add_message(
            {"role": "user", "content": content.content, "tool_call_id": serialize(content.metadata)}
        )

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Query memory content based on semantic vector similarity.

        ..note::

        RedisMemory.query() supports additional keyword arguments to improve query performance.
        top_k (int): The maximum number of relevant memories to include. Defaults to 10.
        distance_threshold (float): The maximum distance in vector space to consider a memory
        semantically similar when performining cosine similarity search. Defaults to 0.7.

        Args:
            query (str | MemoryContent): query to perform vector similarity search with. If a
                string is passed, a vector embedding is created from it with the model specified
                in the RedisMemoryConfig. If a MemoryContent object is passed, the content field
                of this object is extracted and a vector embedding is created from it with the
                model specified in the RedisMemoryConfig.
            cancellation_token (CancellationToken): Token passed to cease operation. Not used.

        Returns:
            memoryQueryResult: Object containing memories relevant to the provided query.
        """
        query = query.content if isinstance(query, MemoryContent) else query

        top_k = kwargs.pop("top_k", self.config.top_k)
        distance_threshold = kwargs.pop("distance_threshold", self.config.distance_threshold)

        results = self.message_history.get_relevant(
            prompt=query,
            top_k=top_k,
            distance_threshold=distance_threshold,
        )

        memories = []
        for result in results:
            memory = MemoryContent(
                content=result["content"], mime_type=MemoryMimeType.TEXT, metadata=deserialize(result["tool_call_id"])
            )
            memories.append(memory)

        return MemoryQueryResult(results=memories)

    async def clear(self) -> None:
        """Clear all entries from memory, preserving the RedisMemory resources."""
        self.message_history.clear()

    async def close(self) -> None:
        """Clears all entries from memory, and cleans up Redis client, index and resources."""
        self.message_history.delete()
