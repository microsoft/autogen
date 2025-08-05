import logging
from typing import Any, List, Literal

from autogen_core import CancellationToken, Component
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from redis import Redis
    from redisvl.extensions.message_history import SemanticMessageHistory
    from redisvl.utils.utils import deserialize, serialize
except ImportError as e:
    raise ImportError("To use Redis Memory RedisVL must be installed. Run `pip install autogen-ext[redisvl]`") from e


class RedisMemoryConfig(BaseModel):
    """
    Configuration for Redis-based vector memory.

    This class defines the configuration options for using Redis as a vector memory store,
    supporting semantic memory. It allows customization of the Redis connection, index settings,
    similarity search parameters, and embedding model.
    """

    redis_url: str = Field(default="redis://localhost:6379", description="url of the Redis instance")
    index_name: str = Field(default="chat_history", description="Name of the Redis collection")
    prefix: str = Field(default="memory", description="prefix of the Redis collection")
    distance_metric: Literal["cosine", "ip", "l2"] = "cosine"
    algorithm: Literal["flat", "hnsw"] = "flat"
    top_k: int = Field(default=10, description="Number of results to return in queries")
    datatype: Literal["uint8", "int8", "float16", "float32", "float64", "bfloat16"] = "float32"
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

        This implementation requires the RedisVL extra to be installed. Install with:

        .. code-block:: bash

            pip install "autogen-ext[redisvl]"

        Additionally, you will need access to a Redis instance.
        To run a local instance of redis in docker:

        .. code-block:: bash

            docker run -d --name redis -p 6379:6379 redis:8

        To download and run Redis locally:

        .. code-block:: bash

            curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
            sudo apt-get update  > /dev/null 2>&1
            sudo apt-get install redis-server  > /dev/null 2>&1
            redis-server --daemonize yes

    Args:
        config (RedisMemoryConfig | None): Configuration for the Redis memory.
            If None, defaults to a RedisMemoryConfig with recommended settings.

    Example:

        .. code-block:: python

            from logging import WARNING, getLogger

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core.memory import MemoryContent, MemoryMimeType
            from autogen_ext.memory.redis import RedisMemory, RedisMemoryConfig
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            logger = getLogger()
            logger.setLevel(WARNING)


            # Define tool to use
            async def get_weather(city: str, units: str = "imperial") -> str:
                if units == "imperial":
                    return f"The weather in {city} is 73 °F and Sunny."
                elif units == "metric":
                    return f"The weather in {city} is 23 °C and Sunny."
                else:
                    return f"Sorry, I don't know the weather in {city}."


            async def main():
                # Initailize Redis memory
                redis_memory = RedisMemory(
                    config=RedisMemoryConfig(
                        redis_url="redis://localhost:6379",
                        index_name="chat_history",
                        prefix="memory",
                    )
                )

                # Add user preferences to memory
                await redis_memory.add(
                    MemoryContent(
                        content="The weather should be in metric units",
                        mime_type=MemoryMimeType.TEXT,
                        metadata={"category": "preferences", "type": "units"},
                    )
                )

                await redis_memory.add(
                    MemoryContent(
                        content="Meal recipe must be vegan",
                        mime_type=MemoryMimeType.TEXT,
                        metadata={"category": "preferences", "type": "dietary"},
                    )
                )

                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                )

                # Create assistant agent with ChromaDB memory
                assistant_agent = AssistantAgent(
                    name="assistant_agent",
                    model_client=model_client,
                    tools=[get_weather],
                    memory=[redis_memory],
                )

                stream = assistant_agent.run_stream(task="What is the weather in New York?")
                await Console(stream)

                await model_client.close()
                await redis_memory.close()


            asyncio.run(main())

        Output:

        .. code-block:: text

            ---------- TextMessage (user) ----------
            What is the weather in New York?
            ---------- MemoryQueryEvent (assistant_agent) ----------
            [MemoryContent(content='The weather should be in metric units', mime_type=<MemoryMimeType.TEXT: 'text/plain'>, metadata={'category': 'preferences', 'type': 'units'})]
            ---------- ToolCallRequestEvent (assistant_agent) ----------
            [FunctionCall(id='call_tyCPvPPAV4SHWhtfpM6UMemr', arguments='{"city":"New York","units":"metric"}', name='get_weather')]
            ---------- ToolCallExecutionEvent (assistant_agent) ----------
            [FunctionExecutionResult(content='The weather in New York is 23 °C and Sunny.', name='get_weather', call_id='call_tyCPvPPAV4SHWhtfpM6UMemr', is_error=False)]
            ---------- ToolCallSummaryMessage (assistant_agent) ----------
            The weather in New York is 23 °C and Sunny.

    """

    component_config_schema = RedisMemoryConfig
    component_provider_override = "autogen_ext.memory.redis_memory.RedisMemory"

    def __init__(self, config: RedisMemoryConfig | None = None) -> None:
        """Initialize RedisMemory."""
        self.config = config or RedisMemoryConfig()
        client = Redis.from_url(url=self.config.redis_url)  # type: ignore[reportUknownMemberType]

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
            from the content field of a MemoryContent object. This content is assumed to be text or
            JSON, and is passed to the vector embedding model specified in RedisMemoryConfig.

        Args:
            content (MemoryContent): The memory content to store within Redis.
            cancellation_token (CancellationToken): Token passed to cease operation. Not used.
        """
        if content.mime_type == MemoryMimeType.TEXT:
            memory_content = content.content
            mime_type = "text/plain"
        elif content.mime_type == MemoryMimeType.JSON:
            memory_content = serialize(content.content)
            mime_type = "application/json"
        else:
            raise NotImplementedError(
                f"Error: {content.mime_type} is not supported. Only MemoryMimeType.TEXT and MemoryMimeType.JSON are currently supported."
            )
        metadata = {"mime_type": mime_type}
        metadata.update(content.metadata if content.metadata else {})
        self.message_history.add_message(
            {"role": "user", "content": memory_content, "tool_call_id": serialize(metadata)}  # type: ignore[reportArgumentType]
        )

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Query memory content based on semantic vector similarity.

        .. note::

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
        # get the query string, or raise an error for unsupported MemoryContent types
        if isinstance(query, str):
            prompt = query
        elif isinstance(query, MemoryContent):
            if query.mime_type == MemoryMimeType.TEXT:
                prompt = str(query.content)
            elif query.mime_type == MemoryMimeType.JSON:
                prompt = serialize(query.content)
            else:
                raise NotImplementedError(
                    f"Error: {query.mime_type} is not supported. Only MemoryMimeType.TEXT and MemoryMimeType.JSON are currently supported."
                )
        else:
            raise TypeError("'query' must be either a string or MemoryContent")

        top_k = kwargs.pop("top_k", self.config.top_k)
        distance_threshold = kwargs.pop("distance_threshold", self.config.distance_threshold)

        results = self.message_history.get_relevant(
            prompt=prompt,  # type: ignore[reportArgumentType]
            top_k=top_k,
            distance_threshold=distance_threshold,
            raw=False,
        )

        memories: List[MemoryContent] = []
        for result in results:
            metadata = deserialize(result["tool_call_id"])  # type: ignore[reportArgumentType]
            mime_type = MemoryMimeType(metadata.pop("mime_type"))
            if mime_type == MemoryMimeType.TEXT:
                memory_content = result["content"]  # type: ignore[reportArgumentType]
            elif mime_type == MemoryMimeType.JSON:
                memory_content = deserialize(result["content"])  # type: ignore[reportArgumentType]
            else:
                raise NotImplementedError(
                    f"Error: {mime_type} is not supported. Only MemoryMimeType.TEXT and MemoryMimeType.JSON are currently supported."
                )
            memory = MemoryContent(
                content=memory_content,  # type: ignore[reportArgumentType]
                mime_type=mime_type,
                metadata=metadata,
            )
            memories.append(memory)  # type: ignore[reportUknownMemberType]

        return MemoryQueryResult(results=memories)  # type: ignore[reportUknownMemberType]

    async def clear(self) -> None:
        """Clear all entries from memory, preserving the RedisMemory resources."""
        self.message_history.clear()

    async def close(self) -> None:
        """Clears all entries from memory, and cleans up Redis client, index and resources."""
        self.message_history.delete()
