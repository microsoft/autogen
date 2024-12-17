# mypy: disable-error-code="no-any-unimported,misc"
import pandas as pd
import tiktoken
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field

from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_entities,
    read_indexer_reports,
)
from graphrag.query.llm.base import BaseLLM
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.query.structured_search.global_search.search import GlobalSearch

from ._config import GlobalContextConfig as ContextConfig
from ._config import GlobalDataConfig as DataConfig
from ._config import MapReduceConfig

_default_context_config = ContextConfig()
_default_mapreduce_config = MapReduceConfig()


class GlobalSearchToolArgs(BaseModel):
    query: str = Field(..., description="The user query to perform global search on.")


class GlobalSearchToolReturn(BaseModel):
    answer: str


class GlobalSearchTool(BaseTool[GlobalSearchToolArgs, GlobalSearchToolReturn]):
    def __init__(
        self,
        token_encoder: tiktoken.Encoding,
        llm: BaseLLM,
        data_config: DataConfig,
        context_config: ContextConfig = _default_context_config,
        mapreduce_config: MapReduceConfig = _default_mapreduce_config,
    ):
        super().__init__(
            args_type=GlobalSearchToolArgs,
            return_type=GlobalSearchToolReturn,
            name="global_search_tool",
            description="Perform a global search with given parameters using graphrag.",
        )
        # Use the provided LLM
        self._llm = llm

        # Load parquet files
        community_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.community_table}.parquet")  # type: ignore
        entity_df: pd.DataFrame = pd.read_parquet(f"{data_config.input_dir}/{data_config.entity_table}.parquet")  # type: ignore
        report_df: pd.DataFrame = pd.read_parquet(  # type: ignore
            f"{data_config.input_dir}/{data_config.community_report_table}.parquet"
        )
        entity_embedding_df: pd.DataFrame = pd.read_parquet(  # type: ignore
            f"{data_config.input_dir}/{data_config.entity_embedding_table}.parquet"
        )

        communities = read_indexer_communities(community_df, entity_df, report_df)
        reports = read_indexer_reports(report_df, entity_df, data_config.community_level)
        entities = read_indexer_entities(entity_df, entity_embedding_df, data_config.community_level)

        context_builder = GlobalCommunityContext(
            community_reports=reports,
            communities=communities,
            entities=entities,
            token_encoder=token_encoder,
        )

        context_builder_params = {
            "use_community_summary": context_config.use_community_summary,
            "shuffle_data": context_config.shuffle_data,
            "include_community_rank": context_config.include_community_rank,
            "min_community_rank": context_config.min_community_rank,
            "community_rank_name": context_config.community_rank_name,
            "include_community_weight": context_config.include_community_weight,
            "community_weight_name": context_config.community_weight_name,
            "normalize_community_weight": context_config.normalize_community_weight,
            "max_tokens": context_config.max_data_tokens,
            "context_name": "Reports",
        }

        map_llm_params = {
            "max_tokens": mapreduce_config.map_max_tokens,
            "temperature": mapreduce_config.map_temperature,
            "response_format": {"type": "json_object"},
        }

        reduce_llm_params = {
            "max_tokens": mapreduce_config.reduce_max_tokens,
            "temperature": mapreduce_config.reduce_temperature,
        }

        self._search_engine = GlobalSearch(
            llm=self._llm,
            context_builder=context_builder,
            token_encoder=token_encoder,
            max_data_tokens=context_config.max_data_tokens,
            map_llm_params=map_llm_params,
            reduce_llm_params=reduce_llm_params,
            allow_general_knowledge=mapreduce_config.allow_general_knowledge,
            json_mode=mapreduce_config.json_mode,
            context_builder_params=context_builder_params,
            concurrent_coroutines=32,
            response_type=mapreduce_config.response_type,
        )

    async def run(self, args: GlobalSearchToolArgs, cancellation_token: CancellationToken) -> GlobalSearchToolReturn:
        result = await self._search_engine.asearch(args.query)
        assert isinstance(result.response, str), "Expected response to be a string"
        return GlobalSearchToolReturn(answer=result.response)
