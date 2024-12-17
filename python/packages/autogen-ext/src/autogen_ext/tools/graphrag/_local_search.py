# mypy: disable-error-code="no-any-unimported,misc"
import pandas as pd
import tiktoken
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field

from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_text_units,
)
from graphrag.query.llm.base import BaseLLM, BaseTextEmbedding
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore

from ._config import LocalContextConfig, SearchConfig
from ._config import LocalDataConfig as DataConfig

_default_context_config = LocalContextConfig()
_default_search_config = SearchConfig()


class LocalSearchToolArgs(BaseModel):
    query: str = Field(..., description="The user query to perform local search on.")


class LocalSearchToolReturn(BaseModel):
    answer: str = Field(..., description="The answer to the user query.")


class LocalSearchTool(BaseTool[LocalSearchToolArgs, LocalSearchToolReturn]):
    def __init__(
        self,
        token_encoder: tiktoken.Encoding,
        llm: BaseLLM,
        embedder: BaseTextEmbedding,
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
        # Use the adapter
        self._llm = llm
        self._embedder = embedder

        # Load parquet files
        entity_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_table}.parquet")  # type: ignore
        entity_embedding_df: pd.DataFrame = pd.read_parquet(  # type: ignore
            f"{data_config.input_dir}/{data_config.entity_embedding_table}.parquet"
        )
        relationship_df: pd.DataFrame = pd.read_parquet(  # type: ignore
            f"{data_config.input_dir}/{data_config.relationship_table}.parquet"
        )
        text_unit_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.text_unit_table}.parquet")  # type: ignore

        # Read data using indexer adapters
        entities = read_indexer_entities(entity_df, entity_embedding_df, data_config.community_level)
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
            llm=self._llm,
            context_builder=context_builder,
            token_encoder=token_encoder,
            llm_params=llm_params,
            context_builder_params=context_builder_params,
            response_type=search_config.response_type,
        )

    async def run(self, args: LocalSearchToolArgs, cancellation_token: CancellationToken) -> LocalSearchToolReturn:
        result = await self._search_engine.asearch(args.query)  # type: ignore
        assert isinstance(result.response, str), "Expected response to be a string"
        return LocalSearchToolReturn(answer=result.response)
