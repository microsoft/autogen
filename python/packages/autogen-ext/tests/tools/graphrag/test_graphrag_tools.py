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
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.data_model.types import TextEmbedder
from graphrag.vector_stores.base import BaseVectorStore, VectorStoreDocument, VectorStoreSearchResult


class MockModelOutput:
    """Mock ModelOutput implementation."""

    def __init__(self, content: str = "Mock response") -> None:
        self._content = content

    @property
    def content(self) -> str:
        return self._content

    @property
    def full_response(self) -> dict[str, Any] | None:
        return {"content": self._content}


class MockModelResponse:
    """Mock ModelResponse implementation."""

    def __init__(self, content: str = "Mock response") -> None:
        self._output = MockModelOutput(content)
        self._history: list[Any] = []

    @property
    def output(self) -> MockModelOutput:
        return self._output

    @property
    def parsed_response(self) -> Any | None:
        return None

    @property
    def history(self) -> list[Any]:
        return self._history


class MockChatModel:  # type: ignore
    """Mock ChatModel implementation for testing."""

    def __init__(self) -> None:
        # Create a proper LanguageModelConfig instance
        self.config: LanguageModelConfig = LanguageModelConfig(
            model="gpt-3.5-turbo", type="openai_chat", api_key="mock-key"
        )

    async def achat(
        self,
        prompt: str,
        history: list[Any] | None = None,
        **kwargs: Any,
    ) -> MockModelResponse:
        return MockModelResponse("Mock response")

    async def achat_stream(
        self,
        prompt: str,
        history: list[Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        yield "Mock response"

    def chat(
        self,
        prompt: str,
        history: list[Any] | None = None,
        **kwargs: Any,
    ) -> MockModelResponse:
        return MockModelResponse("Mock response")

    def chat_stream(
        self,
        prompt: str,
        history: list[Any] | None = None,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        yield "Mock response"


class MockEmbeddingModel:  # type: ignore
    """Mock EmbeddingModel implementation for testing."""

    def __init__(self) -> None:
        # Create a proper LanguageModelConfig instance
        self.config: LanguageModelConfig = LanguageModelConfig(
            model="text-embedding-ada-002", type="openai_embedding", api_key="mock-key"
        )

    async def aembed_batch(self, text_list: list[str], **kwargs: Any) -> list[list[float]]:
        return [[0.1] * 10 for _ in text_list]

    async def aembed(self, text: str, **kwargs: Any) -> list[float]:
        return [0.1] * 10

    def embed_batch(self, text_list: list[str], **kwargs: Any) -> list[list[float]]:
        return [[0.1] * 10 for _ in text_list]

    def embed(self, text: str, **kwargs: Any) -> list[float]:
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Create a temporary directory to simulate the data config
    with tempfile.TemporaryDirectory() as tempdir:
        # Save fixtures to parquet files
        community_table = os.path.join(tempdir, "communities.parquet")
        entity_table = os.path.join(tempdir, "entities.parquet")
        community_report_table = os.path.join(tempdir, "community_reports.parquet")
        entity_embedding_table = os.path.join(tempdir, "entities.parquet")

        community_df_fixture.to_parquet(community_table)  # type: ignore
        entity_df_fixture.to_parquet(entity_table)  # type: ignore
        report_df_fixture.to_parquet(community_report_table)  # type: ignore
        entity_embedding_fixture.to_parquet(entity_embedding_table)  # type: ignore

        # Initialize the data config with the temporary directory
        data_config = GlobalDataConfig(
            input_dir=tempdir,
            community_table="communities",
            entity_table="entities",
            community_report_table="community_reports",
            entity_embedding_table="entities",
        )

        # Initialize the GlobalSearchTool with mock data
        token_encoder = tiktoken.encoding_for_model("gpt-4o")
        model = MockChatModel()

        global_search_tool = GlobalSearchTool(token_encoder=token_encoder, model=model, data_config=data_config)

        with caplog.at_level("INFO"):
            # Example of running the tool and checking the result
            query = "What is the overall sentiment of the community reports?"
            cancellation_token = CancellationToken()
            result = await global_search_tool.run_json(args={"query": query}, cancellation_token=cancellation_token)
            assert isinstance(result, GlobalSearchToolReturn)
            assert isinstance(result.answer, str)

            # Check if the log contains the expected message
            assert result.answer in caplog.text


@pytest.mark.asyncio
async def test_local_search_tool(
    entity_df_fixture: pd.DataFrame,
    relationship_df_fixture: pd.DataFrame,
    text_unit_df_fixture: pd.DataFrame,
    entity_embedding_fixture: pd.DataFrame,
    community_df_fixture: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Create a temporary directory to simulate the data config
    with tempfile.TemporaryDirectory() as tempdir:
        # Save fixtures to parquet files
        entity_table = os.path.join(tempdir, "entities.parquet")
        relationship_table = os.path.join(tempdir, "relationships.parquet")
        text_unit_table = os.path.join(tempdir, "text_units.parquet")
        entity_embedding_table = os.path.join(tempdir, "entities.parquet")
        community_table = os.path.join(tempdir, "communities.parquet")

        entity_df_fixture.to_parquet(entity_table)  # type: ignore
        relationship_df_fixture.to_parquet(relationship_table)  # type: ignore
        text_unit_df_fixture.to_parquet(text_unit_table)  # type: ignore
        entity_embedding_fixture.to_parquet(entity_embedding_table)  # type: ignore
        community_df_fixture.to_parquet(community_table)  # type: ignore

        # Initialize the data config with the temporary directory
        data_config = LocalDataConfig(
            input_dir=tempdir,
            entity_table="entities",
            relationship_table="relationships",
            text_unit_table="text_units",
            entity_embedding_table="entities",
        )

        # Initialize the LocalSearchTool with mock data
        token_encoder = tiktoken.encoding_for_model("gpt-4o")
        model = MockChatModel()
        embedder = MockEmbeddingModel()

        # Mock the vector store
        def mock_vector_store_factory(*args: Any, **kwargs: dict[str, Any]) -> MockVectorStore:
            store = MockVectorStore()
            store.document_collection = store  # Make the store act as its own collection
            return store

        # Patch the LanceDBVectorStore class
        monkeypatch.setattr("autogen_ext.tools.graphrag._local_search.LanceDBVectorStore", mock_vector_store_factory)  # type: ignore

        local_search_tool = LocalSearchTool(
            token_encoder=token_encoder, model=model, embedder=embedder, data_config=data_config
        )

        with caplog.at_level("INFO"):
            # Example of running the tool and checking the result
            query = "What are the relationships between Dr. Becher and the station-master?"
            cancellation_token = CancellationToken()
            result = await local_search_tool.run_json(args={"query": query}, cancellation_token=cancellation_token)
            assert isinstance(result, LocalSearchToolReturn)
            assert isinstance(result.answer, str)

            # Check if the log contains the expected message
            assert result.answer in caplog.text
