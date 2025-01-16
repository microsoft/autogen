# mypy: disable-error-code="no-any-unimported"
import os
import tempfile
from typing import Any, AsyncGenerator, Generator

import pandas as pd
import pytest
import tiktoken
from autogen_core import CancellationToken
from autogen_ext.tools.graphrag import GlobalSearchTool, GlobalSearchToolReturn, LocalSearchTool, LocalSearchToolReturn
from autogen_ext.tools.graphrag._config import GlobalDataConfig, LocalDataConfig
from graphrag.callbacks.llm_callbacks import BaseLLMCallback
from graphrag.model.types import TextEmbedder
from graphrag.query.llm.base import BaseLLM, BaseTextEmbedding
from graphrag.vector_stores.base import BaseVectorStore, VectorStoreDocument, VectorStoreSearchResult


class MockLLM(BaseLLM):  # type: ignore
    def generate(
        self,
        messages: str | list[Any],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        return "Mock response"

    def stream_generate(
        self, messages: str | list[Any], callbacks: list[BaseLLMCallback] | None = None, **kwargs: Any
    ) -> Generator[str, None, None]:
        yield "Mock response"

    async def agenerate(
        self,
        messages: str | list[Any],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        return "Mock response"

    async def astream_generate(  # type: ignore
        self, messages: str | list[Any], callbacks: list[BaseLLMCallback] | None = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        yield "Mock response"


class MockTextEmbedding(BaseTextEmbedding):  # type: ignore
    def embed(self, text: str, **kwargs: Any) -> list[float]:
        return [0.1] * 10

    async def aembed(self, text: str, **kwargs: Any) -> list[float]:
        return [0.1] * 10


class MockVectorStore(BaseVectorStore):  # type: ignore
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(collection_name="mock", **kwargs)
        self.documents: dict[str | int, VectorStoreDocument] = {}

    def connect(self, **kwargs: Any) -> None:
        pass

    def load_documents(self, documents: list[VectorStoreDocument], overwrite: bool = True) -> None:
        if overwrite:
            self.documents = {}
        for doc in documents:
            self.documents[doc.id] = doc

    def filter_by_id(self, include_ids: list[str] | list[int]) -> None:
        return None

    def similarity_search_by_vector(
        self, query_embedding: list[float], k: int = 10, **kwargs: Any
    ) -> list[VectorStoreSearchResult]:
        docs = list(self.documents.values())[:k]
        return [VectorStoreSearchResult(document=doc, score=0.9) for doc in docs]

    def similarity_search_by_text(
        self, text: str, text_embedder: TextEmbedder, k: int = 10, **kwargs: Any
    ) -> list[VectorStoreSearchResult]:
        return self.similarity_search_by_vector([0.1] * 10, k)

    def search_by_id(self, id: str) -> VectorStoreDocument:
        return self.documents.get(id, VectorStoreDocument(id=id, text=None, vector=None))


@pytest.mark.asyncio
async def test_global_search_tool(
    community_df_fixture: pd.DataFrame,
    entity_df_fixture: pd.DataFrame,
    report_df_fixture: pd.DataFrame,
    entity_embedding_fixture: pd.DataFrame,
) -> None:
    # Create a temporary directory to simulate the data config
    with tempfile.TemporaryDirectory() as tempdir:
        # Save fixtures to parquet files
        community_table = os.path.join(tempdir, "create_final_communities.parquet")
        entity_table = os.path.join(tempdir, "create_final_nodes.parquet")
        community_report_table = os.path.join(tempdir, "create_final_community_reports.parquet")
        entity_embedding_table = os.path.join(tempdir, "create_final_entities.parquet")

        community_df_fixture.to_parquet(community_table)  # type: ignore
        entity_df_fixture.to_parquet(entity_table)  # type: ignore
        report_df_fixture.to_parquet(community_report_table)  # type: ignore
        entity_embedding_fixture.to_parquet(entity_embedding_table)  # type: ignore

        # Initialize the data config with the temporary directory
        data_config = GlobalDataConfig(
            input_dir=tempdir,
            community_table="create_final_communities",
            entity_table="create_final_nodes",
            community_report_table="create_final_community_reports",
            entity_embedding_table="create_final_entities",
        )

        # Initialize the GlobalSearchTool with mock data
        token_encoder = tiktoken.encoding_for_model("gpt-4o")
        llm = MockLLM()

        global_search_tool = GlobalSearchTool(token_encoder=token_encoder, llm=llm, data_config=data_config)

        # Example of running the tool and checking the result
        query = "What is the overall sentiment of the community reports?"
        cancellation_token = CancellationToken()
        result = await global_search_tool.run_json(args={"query": query}, cancellation_token=cancellation_token)
        assert isinstance(result, GlobalSearchToolReturn)
        assert isinstance(result.answer, str)


@pytest.mark.asyncio
async def test_local_search_tool(
    entity_df_fixture: pd.DataFrame,
    relationship_df_fixture: pd.DataFrame,
    text_unit_df_fixture: pd.DataFrame,
    entity_embedding_fixture: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create a temporary directory to simulate the data config
    with tempfile.TemporaryDirectory() as tempdir:
        # Save fixtures to parquet files
        entity_table = os.path.join(tempdir, "create_final_nodes.parquet")
        relationship_table = os.path.join(tempdir, "create_final_relationships.parquet")
        text_unit_table = os.path.join(tempdir, "create_final_text_units.parquet")
        entity_embedding_table = os.path.join(tempdir, "create_final_entities.parquet")

        entity_df_fixture.to_parquet(entity_table)  # type: ignore
        relationship_df_fixture.to_parquet(relationship_table)  # type: ignore
        text_unit_df_fixture.to_parquet(text_unit_table)  # type: ignore
        entity_embedding_fixture.to_parquet(entity_embedding_table)  # type: ignore

        # Initialize the data config with the temporary directory
        data_config = LocalDataConfig(
            input_dir=tempdir,
            entity_table="create_final_nodes",
            relationship_table="create_final_relationships",
            text_unit_table="create_final_text_units",
            entity_embedding_table="create_final_entities",
        )

        # Initialize the LocalSearchTool with mock data
        token_encoder = tiktoken.encoding_for_model("gpt-4o")
        llm = MockLLM()
        embedder = MockTextEmbedding()

        # Mock the vector store
        def mock_vector_store_factory(*args: Any, **kwargs: dict[str, Any]) -> MockVectorStore:
            store = MockVectorStore()
            store.document_collection = store  # Make the store act as its own collection
            return store

        # Patch the LanceDBVectorStore class
        monkeypatch.setattr("autogen_ext.tools.graphrag._local_search.LanceDBVectorStore", mock_vector_store_factory)  # type: ignore

        local_search_tool = LocalSearchTool(
            token_encoder=token_encoder, llm=llm, embedder=embedder, data_config=data_config
        )

        # Example of running the tool and checking the result
        query = "What are the relationships between Dr. Becher and the station-master?"
        cancellation_token = CancellationToken()
        result = await local_search_tool.run_json(args={"query": query}, cancellation_token=cancellation_token)
        assert isinstance(result, LocalSearchToolReturn)
        assert isinstance(result.answer, str)
