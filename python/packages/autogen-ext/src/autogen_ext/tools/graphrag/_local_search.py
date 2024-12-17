import os

import pandas as pd
import tiktoken
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from autogen_ext.models.openai import OpenAIChatCompletionClient

# from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
from pydantic import BaseModel, Field

from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_text_units,
)
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore

from ._config import BaseSearchConfig, EmbeddingConfig, LocalContextConfig, LocalDataConfig
from ._model_adapter import GraphragOpenAiModelAdapter

_default_context_config = LocalContextConfig()
_default_search_config = BaseSearchConfig()


class LocalSearchToolArgs(BaseModel):
    query: str = Field(..., description="The user query to perform local search on.")


class LocalSearchTool(BaseTool[LocalSearchToolArgs, str]):
    def __init__(
        self,
        openai_client: OpenAIChatCompletionClient,
        data_config: LocalDataConfig,
        embedding_config: EmbeddingConfig,
        context_config: LocalContextConfig = _default_context_config,
        search_config: BaseSearchConfig = _default_search_config,
    ):
        super().__init__(
            args_type=LocalSearchToolArgs,
            return_type=str,
            name="local_search_tool",
            description="Perform a local search with given parameters using graphrag.",
        )
        # Use the adapter for LLM
        self._llm_adapter = GraphragOpenAiModelAdapter(openai_client)

        # Create text embedder using OpenAI client config
        self._text_embedder = OpenAIEmbedding(
            api_key=embedding_config.api_key,
            api_base=embedding_config.api_base,
            azure_ad_token_provider=embedding_config.azure_ad_token_provider,
            api_version=embedding_config.api_version,
            api_type=embedding_config.api_type,
            model=embedding_config.model,
            encoding_name=embedding_config.encoding_name,
            max_tokens=embedding_config.max_tokens,
            max_retries=embedding_config.max_retries,
            request_timeout=embedding_config.request_timeout,
        )

        # Set up token encoder
        model_name = self._llm_adapter._client._raw_config["model"]
        token_encoder = tiktoken.encoding_for_model(model_name)

        # Load parquet files
        entity_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_table}.parquet")
        entity_embedding_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_embedding_table}.parquet")
        relationship_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.relationship_table}.parquet")
        text_unit_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.text_unit_table}.parquet")

        # Read data using indexer adapters
        entities = read_indexer_entities(entity_df, entity_embedding_df, community_level=data_config.community_level)
        relationships = read_indexer_relationships(relationship_df)
        text_units = read_indexer_text_units(text_unit_df)
        # Set up vector store for entity embeddings
        description_embedding_store = LanceDBVectorStore(
            collection_name="default-entity-description",
        )
        description_embedding_store.connect(db_uri=os.path.join(data_config.input_dir, "lancedb"))
        # entity_embedding_table = table = description_embedding_store.db_connection.open_table('default-entity-description').to_pandas()
        # breakpoint()
        # entity_description_embeddings = store_entity_semantic_embeddings(
        #     entities=entities, vectorstore=description_embedding_store
        # )

        # Set up context builder
        context_builder = LocalSearchMixedContext(
            entities=entities,
            entity_text_embeddings=description_embedding_store,
            text_embedder=self._text_embedder,
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
            llm=self._llm_adapter,
            context_builder=context_builder,
            token_encoder=token_encoder,
            llm_params=llm_params,
            context_builder_params=context_builder_params,
            response_type=search_config.response_type,
        )

    async def run(self, args: LocalSearchToolArgs, cancellation_token: CancellationToken) -> str:
        result = await self._search_engine.asearch(args.query)
        return result.response
