"""Tests for PerplexityChatCompletionClient."""

from __future__ import annotations

import pytest

from autogen_ext.models.perplexity import (
    PERPLEXITY_BASE_URL,
    PerplexityChatCompletionClient,
)
from autogen_ext.models.perplexity._perplexity_client import (
    PPLX_INTEGRATION_HEADER,
    PPLX_INTEGRATION_HEADER_VALUE,
)


def _assert_pplx_integration_header(client: PerplexityChatCompletionClient) -> None:
    assert client._raw_config["default_headers"][PPLX_INTEGRATION_HEADER] == PPLX_INTEGRATION_HEADER_VALUE
    assert client._client.default_headers[PPLX_INTEGRATION_HEADER] == PPLX_INTEGRATION_HEADER_VALUE


def test_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("PPLX_API_KEY", raising=False)

    with pytest.raises(ValueError, match="PERPLEXITY_API_KEY"):
        PerplexityChatCompletionClient(model="sonar")


def test_picks_up_perplexity_api_key_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "env-key-1")
    monkeypatch.delenv("PPLX_API_KEY", raising=False)

    client = PerplexityChatCompletionClient(model="sonar")

    assert client._raw_config["api_key"] == "env-key-1"
    assert client._raw_config["base_url"] == PERPLEXITY_BASE_URL
    _assert_pplx_integration_header(client)


def test_falls_back_to_pplx_api_key_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("PPLX_API_KEY", "alias-key")

    client = PerplexityChatCompletionClient(model="sonar-pro")

    assert client._raw_config["api_key"] == "alias-key"
    _assert_pplx_integration_header(client)


def test_explicit_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "env-key")

    client = PerplexityChatCompletionClient(model="sonar", api_key="explicit-key")

    assert client._raw_config["api_key"] == "explicit-key"
    _assert_pplx_integration_header(client)


def test_custom_base_url_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "k")

    client = PerplexityChatCompletionClient(
        model="sonar",
        base_url="https://gateway.example.com/v1",
        default_headers={"X-Custom": "custom-value"},
    )

    assert client._raw_config["base_url"] == "https://gateway.example.com/v1"
    assert client._raw_config["default_headers"]["X-Custom"] == "custom-value"
    _assert_pplx_integration_header(client)


def test_default_model_info_is_populated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "k")

    client = PerplexityChatCompletionClient(model="sonar")

    info = client.model_info
    assert info["function_calling"] is True
    assert info["json_output"] is True
    assert info["vision"] is False
    _assert_pplx_integration_header(client)
