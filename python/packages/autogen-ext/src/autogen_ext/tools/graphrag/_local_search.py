# tool_local_search.py

import json
from typing import Any

import pandas as pd
import tiktoken
from autogen_core import CancellationToken
from autogen_core.components.tools import BaseTool
from graphrag.model.entity import Entity
from graphrag.model.relationship import Relationship
from graphrag.model.text_unit import TextUnit
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_text_units,
)
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from pydantic import BaseModel, Field

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ._model_adapter import GraphragOpenAiModelAdapter


class DataConfig(BaseModel):
    input_dir: str
    entity_table: str = "create_final_nodes"
    entity_embedding_table: str = "create_final_entities"
    relationship_table: str = "create_final_edges"
    text_unit_table: str = "create_final_text_units"


class ContextConfig(BaseModel):
    text_unit_prop: float = 0.5
    community_prop: float = 0.25
    include_entity_rank: bool = True
    rank_description: str = "number of relationships"
    include_relationship_weight: bool = True
    relationship_ranking_attribute: str = "rank"
    max_data_tokens: int = 8000


class SearchConfig(BaseModel):
    max_tokens: int = 1500
    temperature: float = 0.0
    response_type: str = "multiple paragraphs"


_default_context_config = ContextConfig()
_default_search_config = SearchConfig()


class LocalSearchToolArgs(BaseModel):
    query: str = Field(..., description="The user query to perform local search on.")


class LocalSearchTool(BaseTool[LocalSearchToolArgs, str]):
    def __init__(
        self,
        openai_client: OpenAIChatCompletionClient,
        data_config: DataConfig,
        context_config: ContextConfig = _default_context_config,
        search_config: SearchConfig = _default_search_config,
    ):
        super().__init__(
            args_type=LocalSearchToolArgs,
            return_type=str,
            name="local_search_tool",
            description="Perform a local search with given parameters using graphrag.",
        )
        # Use the adapter
        self._llm_adapter = GraphragOpenAiModelAdapter(openai_client)

        # Set up token encoder
        model_name = self._llm_adapter._client._raw_config["model"]
        token_encoder = tiktoken.encoding_for_model(model_name)

        # Load parquet files
        entity_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_table}.parquet")
        entity_embedding_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_embedding_table}.parquet")
        relationship_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.relationship_table}.parquet")
        text_unit_df = pd.read_parquet(f"{data_config.input_dir}/{data_config.text_unit_table}.parquet")

        # Read data using indexer adapters
        entities = read_indexer_entities(entity_df, entity_embedding_df)
        relationships = read_indexer_relationships(relationship_df)
        text_units = read_indexer_text_units(text_unit_df)

        # Set up context builder
        context_builder = LocalSearchMixedContext(
            entities=entities,
            entity_text_embeddings=entity_embedding_df,
            text_embedder=self._llm_adapter,
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
