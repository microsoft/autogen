import logging
import uuid
from typing import Any, List

from autogen_core import CancellationToken, Component, Image
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from chromadb import HttpClient, PersistentClient
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Document, Metadata
from typing_extensions import Self

from ._chroma_configs import (
    ChromaDBVectorMemoryConfig,
    CustomEmbeddingFunctionConfig,
    DefaultEmbeddingFunctionConfig,
    HttpChromaDBVectorMemoryConfig,
    OpenAIEmbeddingFunctionConfig,
    PersistentChromaDBVectorMemoryConfig,
    SentenceTransformerEmbeddingFunctionConfig,
)

logger = logging.getLogger(__name__)


try:
    from chromadb.api import ClientAPI
except ImportError as e:
    raise ImportError(
        "To use the ChromaDBVectorMemory the chromadb extra must be installed. Run `pip install autogen-ext[chromadb]`"
    ) from e


class ChromaDBVectorMemory(Memory, Component[ChromaDBVectorMemoryConfig]):
    """
    Store and retrieve memory using vector similarity search powered by ChromaDB.

    `ChromaDBVectorMemory` provides a vector-based memory implementation that uses ChromaDB for
    storing and retrieving content based on semantic similarity. It enhances agents with the ability
    to recall contextually relevant information during conversations by leveraging vector embeddings
    to find similar content.

    This implementation serves as a reference for more complex memory systems using vector embeddings.
    For advanced use cases requiring specialized formatting of retrieved content, users should extend
    this class and override the `update_context()` method.

    This implementation requires the ChromaDB extra to be installed. Install with:

    .. code-block:: bash

        pip install "autogen-ext[chromadb]"

    Args:
        config (ChromaDBVectorMemoryConfig | None): Configuration for the ChromaDB memory.
            If None, defaults to a PersistentChromaDBVectorMemoryConfig with default values.
            Two config types are supported:
            * PersistentChromaDBVectorMemoryConfig: For local storage
            * HttpChromaDBVectorMemoryConfig: For connecting to a remote ChromaDB server

    Example:

        .. code-block:: python

            import os
            import asyncio
            from pathlib import Path
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core.memory import MemoryContent, MemoryMimeType
            from autogen_ext.memory.chromadb import (
                ChromaDBVectorMemory,
                PersistentChromaDBVectorMemoryConfig,
                SentenceTransformerEmbeddingFunctionConfig,
                OpenAIEmbeddingFunctionConfig,
            )
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            def get_weather(city: str) -> str:
                return f"The weather in {city} is sunny with a high of 90°F and a low of 70°F."


            def fahrenheit_to_celsius(fahrenheit: float) -> float:
                return (fahrenheit - 32) * 5.0 / 9.0


            async def main() -> None:
                # Use default embedding function
                default_memory = ChromaDBVectorMemory(
                    config=PersistentChromaDBVectorMemoryConfig(
                        collection_name="user_preferences",
                        persistence_path=os.path.join(str(Path.home()), ".chromadb_autogen"),
                        k=3,  # Return top 3 results
                        score_threshold=0.5,  # Minimum similarity score
                    )
                )

                # Using a custom SentenceTransformer model
                custom_memory = ChromaDBVectorMemory(
                    config=PersistentChromaDBVectorMemoryConfig(
                        collection_name="multilingual_memory",
                        persistence_path=os.path.join(str(Path.home()), ".chromadb_autogen"),
                        embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
                            model_name="paraphrase-multilingual-mpnet-base-v2"
                        ),
                    )
                )

                # Using OpenAI embeddings
                openai_memory = ChromaDBVectorMemory(
                    config=PersistentChromaDBVectorMemoryConfig(
                        collection_name="openai_memory",
                        persistence_path=os.path.join(str(Path.home()), ".chromadb_autogen"),
                        embedding_function_config=OpenAIEmbeddingFunctionConfig(
                            api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-3-small"
                        ),
                    )
                )

                # Add user preferences to memory
                await openai_memory.add(
                    MemoryContent(
                        content="The user prefers weather temperatures in Celsius",
                        mime_type=MemoryMimeType.TEXT,
                        metadata={"category": "preferences", "type": "units"},
                    )
                )

                # Create assistant agent with ChromaDB memory
                assistant = AssistantAgent(
                    name="assistant",
                    model_client=OpenAIChatCompletionClient(
                        model="gpt-4.1",
                    ),
                    tools=[
                        get_weather,
                        fahrenheit_to_celsius,
                    ],
                    max_tool_iterations=10,
                    memory=[openai_memory],
                )

                # The memory will automatically retrieve relevant content during conversations
                await Console(assistant.run_stream(task="What's the temperature in New York?"))

                # Remember to close the memory when finished
                await default_memory.close()
                await custom_memory.close()
                await openai_memory.close()


            asyncio.run(main())

        Output:

        .. code-block:: text

            ---------- TextMessage (user) ----------
            What's the temperature in New York?
            ---------- MemoryQueryEvent (assistant) ----------
            [MemoryContent(content='The user prefers weather temperatures in Celsius', mime_type='MemoryMimeType.TEXT', metadata={'type': 'units', 'category': 'preferences', 'mime_type': 'MemoryMimeType.TEXT', 'score': 0.3133561611175537, 'id': 'fb00506c-acf4-4174-93d7-2a942593f3f7'}), MemoryContent(content='The user prefers weather temperatures in Celsius', mime_type='MemoryMimeType.TEXT', metadata={'mime_type': 'MemoryMimeType.TEXT', 'category': 'preferences', 'type': 'units', 'score': 0.3133561611175537, 'id': '34311689-b419-4e1a-8bc4-09143f356c66'})]
            ---------- ToolCallRequestEvent (assistant) ----------
            [FunctionCall(id='call_7TjsFd430J1aKwU5T2w8bvdh', arguments='{"city":"New York"}', name='get_weather')]
            ---------- ToolCallExecutionEvent (assistant) ----------
            [FunctionExecutionResult(content='The weather in New York is sunny with a high of 90°F and a low of 70°F.', name='get_weather', call_id='call_7TjsFd430J1aKwU5T2w8bvdh', is_error=False)]
            ---------- ToolCallRequestEvent (assistant) ----------
            [FunctionCall(id='call_RTjMHEZwDXtjurEYTjDlvq9c', arguments='{"fahrenheit": 90}', name='fahrenheit_to_celsius'), FunctionCall(id='call_3mMuCK1aqtzZPTqIHPoHKxtP', arguments='{"fahrenheit": 70}', name='fahrenheit_to_celsius')]
            ---------- ToolCallExecutionEvent (assistant) ----------
            [FunctionExecutionResult(content='32.22222222222222', name='fahrenheit_to_celsius', call_id='call_RTjMHEZwDXtjurEYTjDlvq9c', is_error=False), FunctionExecutionResult(content='21.11111111111111', name='fahrenheit_to_celsius', call_id='call_3mMuCK1aqtzZPTqIHPoHKxtP', is_error=False)]
            ---------- TextMessage (assistant) ----------
            The temperature in New York today is sunny with a high of about 32°C and a low of about 21°C.

    """

    component_config_schema = ChromaDBVectorMemoryConfig
    component_provider_override = "autogen_ext.memory.chromadb.ChromaDBVectorMemory"

    def __init__(self, config: ChromaDBVectorMemoryConfig | None = None) -> None:
        self._config = config or PersistentChromaDBVectorMemoryConfig()
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None

    @property
    def collection_name(self) -> str:
        """Get the name of the ChromaDB collection."""
        return self._config.collection_name

    def _create_embedding_function(self) -> Any:
        """Create an embedding function based on the configuration.

        Returns:
            A ChromaDB-compatible embedding function.

        Raises:
            ValueError: If the embedding function type is unsupported.
            ImportError: If required dependencies are not installed.
        """
        try:
            from chromadb.utils import embedding_functions
        except ImportError as e:
            raise ImportError(
                "ChromaDB embedding functions not available. Ensure chromadb is properly installed."
            ) from e

        config = self._config.embedding_function_config

        if isinstance(config, DefaultEmbeddingFunctionConfig):
            return embedding_functions.DefaultEmbeddingFunction()

        elif isinstance(config, SentenceTransformerEmbeddingFunctionConfig):
            try:
                return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.model_name)
            except Exception as e:
                raise ImportError(
                    f"Failed to create SentenceTransformer embedding function with model '{config.model_name}'. "
                    f"Ensure sentence-transformers is installed and the model is available. Error: {e}"
                ) from e

        elif isinstance(config, OpenAIEmbeddingFunctionConfig):
            try:
                return embedding_functions.OpenAIEmbeddingFunction(api_key=config.api_key, model_name=config.model_name)
            except Exception as e:
                raise ImportError(
                    f"Failed to create OpenAI embedding function with model '{config.model_name}'. "
                    f"Ensure openai is installed and API key is valid. Error: {e}"
                ) from e

        elif isinstance(config, CustomEmbeddingFunctionConfig):
            try:
                return config.function(**config.params)
            except Exception as e:
                raise ValueError(f"Failed to create custom embedding function. Error: {e}") from e

        else:
            raise ValueError(f"Unsupported embedding function config type: {type(config)}")

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client and collection are initialized."""
        if self._client is None:
            try:
                from chromadb.config import Settings

                settings = Settings(allow_reset=self._config.allow_reset)

                if isinstance(self._config, PersistentChromaDBVectorMemoryConfig):
                    self._client = PersistentClient(
                        path=self._config.persistence_path,
                        settings=settings,
                        tenant=self._config.tenant,
                        database=self._config.database,
                    )
                elif isinstance(self._config, HttpChromaDBVectorMemoryConfig):
                    self._client = HttpClient(
                        host=self._config.host,
                        port=self._config.port,
                        ssl=self._config.ssl,
                        headers=self._config.headers,
                        settings=settings,
                        tenant=self._config.tenant,
                        database=self._config.database,
                    )
                else:
                    raise ValueError(f"Unsupported config type: {type(self._config)}")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise

        if self._collection is None:
            try:
                # Create embedding function
                embedding_function = self._create_embedding_function()

                # Create or get collection with embedding function
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name,
                    metadata={"distance_metric": self._config.distance_metric},
                    embedding_function=embedding_function,
                )
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

    def _extract_text(self, content_item: str | MemoryContent) -> str:
        """Extract searchable text from content."""
        if isinstance(content_item, str):
            return content_item

        content = content_item.content
        mime_type = content_item.mime_type

        if mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            return str(content)
        elif mime_type == MemoryMimeType.JSON:
            if isinstance(content, dict):
                # Store original JSON string representation
                return str(content).lower()
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(f"Unsupported content type: {mime_type}")

    def _calculate_score(self, distance: float) -> float:
        """Convert ChromaDB distance to a similarity score."""
        if self._config.distance_metric == "cosine":
            return 1.0 - (distance / 2.0)
        return 1.0 / (1.0 + distance)

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        messages = await model_context.get_messages()
        if not messages:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        # Extract query from last message
        last_message = messages[-1]
        query_text = last_message.content if isinstance(last_message.content, str) else str(last_message)

        # Query memory and get results
        query_results = await self.query(query_text)

        if query_results.results:
            # Format results for context
            memory_strings = [f"{i}. {str(memory.content)}" for i, memory in enumerate(query_results.results, 1)]
            memory_context = "\nRelevant memory content:\n" + "\n".join(memory_strings)

            # Add to context
            await model_context.add_message(SystemMessage(content=memory_context))

        return UpdateContextResult(memories=query_results)

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text from content
            text = self._extract_text(content)

            # Use metadata directly from content
            metadata_dict = content.metadata or {}
            metadata_dict["mime_type"] = str(content.mime_type)

            # Add to ChromaDB
            self._collection.add(documents=[text], metadatas=[metadata_dict], ids=[str(uuid.uuid4())])

        except Exception as e:
            logger.error(f"Failed to add content to ChromaDB: {e}")
            raise

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text for query
            query_text = self._extract_text(query)

            # Query ChromaDB
            results = self._collection.query(
                query_texts=[query_text],
                n_results=self._config.k,
                include=["documents", "metadatas", "distances"],
                **kwargs,
            )

            # Convert results to MemoryContent list
            memory_results: List[MemoryContent] = []

            if (
                not results
                or not results.get("documents")
                or not results.get("metadatas")
                or not results.get("distances")
            ):
                return MemoryQueryResult(results=memory_results)

            documents: List[Document] = results["documents"][0] if results["documents"] else []
            metadatas: List[Metadata] = results["metadatas"][0] if results["metadatas"] else []
            distances: List[float] = results["distances"][0] if results["distances"] else []
            ids: List[str] = results["ids"][0] if results["ids"] else []

            for doc, metadata_dict, distance, doc_id in zip(documents, metadatas, distances, ids, strict=False):
                # Calculate score
                score = self._calculate_score(distance)
                metadata = dict(metadata_dict)
                metadata["score"] = score
                metadata["id"] = doc_id
                if self._config.score_threshold is not None and score < self._config.score_threshold:
                    continue

                # Extract mime_type from metadata
                mime_type = str(metadata_dict.get("mime_type", MemoryMimeType.TEXT.value))

                # Create MemoryContent
                content = MemoryContent(
                    content=doc,
                    mime_type=mime_type,
                    metadata=metadata,
                )
                memory_results.append(content)

            return MemoryQueryResult(results=memory_results)

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            raise

    async def clear(self) -> None:
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            results = self._collection.get()
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise

    async def close(self) -> None:
        """Clean up ChromaDB client and resources."""
        self._collection = None
        self._client = None

    async def reset(self) -> None:
        self._ensure_initialized()
        if not self._config.allow_reset:
            raise RuntimeError("Reset not allowed. Set allow_reset=True in config to enable.")

        if self._client is not None:
            try:
                self._client.reset()
            except Exception as e:
                logger.error(f"Error during ChromaDB reset: {e}")
            finally:
                self._collection = None

    def _to_config(self) -> ChromaDBVectorMemoryConfig:
        """Serialize the memory configuration."""

        return self._config

    @classmethod
    def _from_config(cls, config: ChromaDBVectorMemoryConfig) -> Self:
        """Deserialize the memory configuration."""

        return cls(config=config)
