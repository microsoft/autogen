from typing import Any, Dict, cast

import pytest
from autogen_ext.tools.azure._config import AzureAISearchConfig, QueryTypeLiteral
from azure.core.credentials import AzureKeyCredential
from pydantic import ValidationError

from tests.tools.azure.conftest import azure_sdk_available

skip_if_no_azure_sdk = pytest.mark.skipif(
    not azure_sdk_available, reason="Azure SDK components (azure-search-documents, azure-identity) not available"
)

# =====================================
# Basic Configuration Tests
# =====================================


def test_basic_config_creation() -> None:
    """Test that a basic valid configuration can be created."""
    config = AzureAISearchConfig(
        name="test_tool",
        endpoint="https://test-search.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    assert config.name == "test_tool"
    assert config.endpoint == "https://test-search.search.windows.net"
    assert config.index_name == "test-index"
    assert isinstance(config.credential, AzureKeyCredential)
    assert config.query_type == "simple"  # default value


def test_endpoint_validation() -> None:
    """Test that endpoint validation works correctly."""
    valid_endpoints = ["https://test.search.windows.net", "http://localhost:8080"]

    for endpoint in valid_endpoints:
        config = AzureAISearchConfig(
            name="test_tool",
            endpoint=endpoint,
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )
        assert config.endpoint == endpoint

    invalid_endpoints = [
        "test.search.windows.net",
        "ftp://test.search.windows.net",
        "",
    ]

    for endpoint in invalid_endpoints:
        with pytest.raises(ValidationError) as exc:
            AzureAISearchConfig(
                name="test_tool",
                endpoint=endpoint,
                index_name="test-index",
                credential=AzureKeyCredential("test-key"),
            )
        assert "endpoint must be a valid URL" in str(exc.value)


def test_top_validation() -> None:
    """Test validation of top parameter."""
    valid_tops = [1, 5, 10, 100]

    for top in valid_tops:
        config = AzureAISearchConfig(
            name="test_tool",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            top=top,
        )
        assert config.top == top

    invalid_tops = [0, -1, -10]

    for top in invalid_tops:
        with pytest.raises(ValidationError) as exc:
            AzureAISearchConfig(
                name="test_tool",
                endpoint="https://test.search.windows.net",
                index_name="test-index",
                credential=AzureKeyCredential("test-key"),
                top=top,
            )
        assert "top must be a positive integer" in str(exc.value)


# =====================================
# Query Type Tests
# =====================================


def test_query_type_normalization() -> None:
    """Test that query_type normalization works correctly."""
    standard_query_types = {
        "simple": "simple",
        "full": "full",
        "semantic": "semantic",
        "vector": "vector",
    }

    for input_type, expected_type in standard_query_types.items():
        config_args: Dict[str, Any] = {
            "name": "test_tool",
            "endpoint": "https://test.search.windows.net",
            "index_name": "test-index",
            "credential": AzureKeyCredential("test-key"),
            "query_type": cast(QueryTypeLiteral, input_type),
        }

        if input_type == "semantic":
            config_args["semantic_config_name"] = "my-semantic-config"
        elif input_type == "vector":
            config_args["vector_fields"] = ["content_vector"]

        config = AzureAISearchConfig(**config_args)
        assert config.query_type == expected_type

    with pytest.raises(ValidationError) as exc:
        AzureAISearchConfig(
            name="test_tool",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            query_type=cast(Any, "invalid_type"),
        )
    assert "Input should be" in str(exc.value)


def test_semantic_config_validation() -> None:
    """Test validation of semantic configuration."""
    config = AzureAISearchConfig(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        query_type=cast(QueryTypeLiteral, "semantic"),
        semantic_config_name="my-semantic-config",
    )
    assert config.query_type == "semantic"
    assert config.semantic_config_name == "my-semantic-config"

    with pytest.raises(ValidationError) as exc:
        AzureAISearchConfig(
            name="test_tool",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            query_type=cast(QueryTypeLiteral, "semantic"),
        )
    assert "semantic_config_name must be provided" in str(exc.value)


def test_vector_fields_validation() -> None:
    """Test validation of vector fields for vector search."""
    config = AzureAISearchConfig(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        query_type=cast(QueryTypeLiteral, "vector"),
        vector_fields=["content_vector"],
    )
    assert config.query_type == "vector"
    assert config.vector_fields == ["content_vector"]


# =====================================
# Embedding Configuration Tests
# =====================================


def test_azure_openai_endpoint_validation() -> None:
    """Test validation of Azure OpenAI endpoint for client-side embeddings."""
    config = AzureAISearchConfig(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        embedding_provider="azure_openai",
        embedding_model="text-embedding-ada-002",
        openai_endpoint="https://test.openai.azure.com",
    )
    assert config.embedding_provider == "azure_openai"
    assert config.embedding_model == "text-embedding-ada-002"
    assert config.openai_endpoint == "https://test.openai.azure.com"

    with pytest.raises(ValidationError) as exc:
        AzureAISearchConfig(
            name="test_tool",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            embedding_provider="azure_openai",
            embedding_model="text-embedding-ada-002",
        )
    assert "openai_endpoint must be provided for azure_openai" in str(exc.value)

    config = AzureAISearchConfig(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        embedding_provider="openai",
        embedding_model="text-embedding-ada-002",
    )
    assert config.embedding_provider == "openai"
    assert config.embedding_model == "text-embedding-ada-002"
    assert config.openai_endpoint is None


# =====================================
# Credential and Serialization Tests
# =====================================


def test_credential_validation() -> None:
    """Test credential validation scenarios."""
    config = AzureAISearchConfig(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )
    assert isinstance(config.credential, AzureKeyCredential)
    assert config.credential.key == "test-key"

    if azure_sdk_available:
        from azure.core.credentials import AccessToken
        from azure.core.credentials_async import AsyncTokenCredential

        class TestTokenCredential(AsyncTokenCredential):
            async def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
                return AccessToken("test-token", 12345)

            async def close(self) -> None:
                pass

            async def __aenter__(self) -> "TestTokenCredential":
                return self

            async def __aexit__(self, *args: Any) -> None:
                await self.close()

        config = AzureAISearchConfig(
            name="test",
            endpoint="https://endpoint",
            index_name="index",
            credential=TestTokenCredential(),
        )
        assert isinstance(config.credential, AsyncTokenCredential)


def test_model_dump_scenarios() -> None:
    """Test all model_dump scenarios to ensure full code coverage."""
    config = AzureAISearchConfig(
        name="test",
        endpoint="https://endpoint",
        index_name="index",
        credential=AzureKeyCredential("key"),
    )
    result = config.model_dump()
    assert isinstance(result["credential"], AzureKeyCredential)
    assert result["credential"].key == "key"

    if azure_sdk_available:
        from azure.core.credentials import AccessToken
        from azure.core.credentials_async import AsyncTokenCredential

        class TestTokenCredential(AsyncTokenCredential):
            async def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
                return AccessToken("test-token", 12345)

            async def close(self) -> None:
                pass

            async def __aenter__(self) -> "TestTokenCredential":
                return self

            async def __aexit__(self, *args: Any) -> None:
                await self.close()

        config = AzureAISearchConfig(
            name="test",
            endpoint="https://endpoint",
            index_name="index",
            credential=TestTokenCredential(),
        )
        result = config.model_dump()
        assert isinstance(result["credential"], AsyncTokenCredential)
    else:
        pytest.skip("Skipping TokenCredential test - Azure SDK not available")
