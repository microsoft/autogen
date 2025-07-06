# mypy: disable-error-code="no-any-unimported,misc"
from pathlib import Path

import graphrag.config.defaults as defs
import pandas as pd
import tiktoken
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from graphrag.config.load_config import load_config
from graphrag.language_model.manager import ModelManager
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_text_units,
)
from graphrag.language_model.protocol import ChatModel, EmbeddingModel
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from pydantic import BaseModel, Field

from ._config import LocalContextConfig, SearchConfig
from ._config import LocalDataConfig as DataConfig

_default_context_config = LocalContextConfig()
_default_search_config = SearchConfig()


class LocalSearchToolArgs(BaseModel):
    query: str = Field(..., description="The user query to perform local search on.")


class LocalSearchToolReturn(BaseModel):
    answer: str = Field(..., description="The answer to the user query.")


class LocalSearchTool(BaseTool[LocalSearchToolArgs, LocalSearchToolReturn]):
    """Enables running GraphRAG local search queries as an AutoGen tool.

    This tool allows you to perform semantic search over a corpus of documents using the GraphRAG framework.
    The search combines local document context with semantic embeddings to find relevant information.

    .. note::
        This tool requires the :code:`graphrag` extra for the :code:`autogen-ext` package.
        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[graphrag]"

        Before using this tool, you must complete the GraphRAG setup and indexing process:

        1. Follow the GraphRAG documentation to initialize your project and settings
        2. Configure and tune your prompts for the specific use case
        3. Run the indexing process to generate the required data files
        4. Ensure you have the settings.yaml file from the setup process

        Please refer to the [GraphRAG documentation](https://microsoft.github.io/graphrag/)
        for detailed instructions on completing these prerequisite steps.

    Example usage with AssistantAgent:

    .. code-block:: python

        import asyncio
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_agentchat.ui import Console
        from autogen_ext.tools.graphrag import LocalSearchTool
        from autogen_agentchat.agents import AssistantAgent


        async def main():
            # Initialize the OpenAI client
            openai_client = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key="<api-key>",
            )

            # Set up local search tool
            local_tool = LocalSearchTool.from_settings(root_dir=Path("./"), config_filepath=Path("./settings.yaml"))

            # Create assistant agent with the local search tool
            assistant_agent = AssistantAgent(
                name="search_assistant",
                tools=[local_tool],
                model_client=openai_client,
                system_message=(
                    "You are a tool selector AI assistant using the GraphRAG framework. "
                    "Your primary task is to determine the appropriate search tool to call based on the user's query. "
                    "For specific, detailed information about particular entities or relationships, call the 'local_search' function."
                ),
            )

            # Run a sample query
            query = "What does the station-master say about Dr. Becher?"
            await Console(assistant_agent.run_stream(task=query))


        if __name__ == "__main__":
            asyncio.run(main())


    Args:
        token_encoder (tiktoken.Encoding): The tokenizer used for text encoding
        model: The chat model to use for search (GraphRAG ChatModel)
        embedder: The text embedding model to use (GraphRAG EmbeddingModel)
        data_config (DataConfig): Configuration for data source locations and settings
        context_config (LocalContextConfig, optional): Configuration for context building. Defaults to default config.
        search_config (SearchConfig, optional): Configuration for search operations. Defaults to default config.
    """

    def __init__(
        self,
        token_encoder: tiktoken.Encoding,
        model: ChatModel,  # ChatModel from GraphRAG
        embedder: EmbeddingModel,  # EmbeddingModel from GraphRAG
        data_config: DataConfig,
        context_config: LocalContextConfig = _default_context_config,
        search_config: SearchConfig = _default_search_config,
    ):
        super().__init__(
            args_type=LocalSearchToolArgs,
            return_type=LocalSearchToolReturn,
            name="local_search_tool",
            description="Perform a local search with given parameters using graphrag.",
        )
        # Use the provided models
        self._model = model
        self._embedder = embedder

        # Load parquet files
        entity_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_table}.parquet")  # type: ignore
        relationship_df: pd.DataFrame = pd.read_parquet(  # type: ignore
            f"{data_config.input_dir}/{data_config.relationship_table}.parquet"
        )
        text_unit_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.text_unit_table}.parquet")  # type: ignore
        community_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.community_table}.parquet")  # type: ignore

        # Read data using indexer adapters
        entities = read_indexer_entities(entity_df, community_df, data_config.community_level)
        relationships = read_indexer_relationships(relationship_df)
        text_units = read_indexer_text_units(text_unit_df)
        # Set up vector store for entity embeddings
        description_embedding_store = LanceDBVectorStore(
            collection_name="default-entity-description",
        )
        description_embedding_store.connect(db_uri=f"{data_config.input_dir}/lancedb")

        # Set up context builder
        context_builder = LocalSearchMixedContext(
            entities=entities,
            entity_text_embeddings=description_embedding_store,
            text_embedder=self._embedder,
            text_units=text_units,
            relationships=relationships,
            token_encoder=token_encoder,
        )

        context_builder_params = {
            "text_unit_prop": context_config.text_unit_prop,
            "community_prop": context_config.community_prop,
            "include_entity_rank": context_config.include_entity_rank,
            "rank_description": context_config.rank_description,
            "include_relationship_weight": context_config.include_relationship_weight,
            "relationship_ranking_attribute": context_config.relationship_ranking_attribute,
            "max_tokens": context_config.max_data_tokens,
        }

        llm_params = {
            "max_tokens": search_config.max_tokens,
            "temperature": search_config.temperature,
        }

        self._search_engine = LocalSearch(
            model=self._model,
            context_builder=context_builder,
            token_encoder=token_encoder,
            model_params=llm_params,
            context_builder_params=context_builder_params,
            response_type=search_config.response_type,
        )

    async def run(self, args: LocalSearchToolArgs, cancellation_token: CancellationToken) -> LocalSearchToolReturn:
        search_result = await self._search_engine.search(args.query)
        assert isinstance(search_result.response, str), "Expected response to be a string"
        return LocalSearchToolReturn(answer=search_result.response)

    @classmethod
    def from_settings(cls, root_dir: Path, config_filepath: Path | None = None) -> "LocalSearchTool":
        """Create a LocalSearchTool instance from GraphRAG settings file.

        Args:
            root_dir: Path to the GraphRAG root directory
            config_filepath: Path to the GraphRAG settings file (optional)

        Returns:
            An initialized LocalSearchTool instance
        """
        # Load GraphRAG config
        config = load_config(root_dir=root_dir, config_filepath=config_filepath)

        # Get the language model configurations
        chat_model_config = config.get_language_model_config(defs.DEFAULT_CHAT_MODEL_ID)
        embedding_model_config = config.get_language_model_config(defs.DEFAULT_EMBEDDING_MODEL_ID)

        # Initialize token encoder based on the model being used
        try:
            token_encoder = tiktoken.encoding_for_model(chat_model_config.model)
        except KeyError:
            # Fallback to cl100k_base if model is not recognized by tiktoken
            token_encoder = tiktoken.get_encoding("cl100k_base")

        # Create the models using ModelManager
        model = ModelManager().get_or_create_chat_model(
            name="local_search_model",
            model_type=chat_model_config.type,
            config=chat_model_config,
        )

        embedder = ModelManager().get_or_create_embedding_model(
            name="local_search_embedder",
            model_type=embedding_model_config.type,
            config=embedding_model_config,
        )

        # Create data config from storage paths
        data_config = DataConfig(
            input_dir=str(Path(config.output.base_dir)),
        )

        return cls(
            token_encoder=token_encoder,
            model=model,
            embedder=embedder,
            data_config=data_config,
            context_config=_default_context_config,
            search_config=_default_search_config,
        )
