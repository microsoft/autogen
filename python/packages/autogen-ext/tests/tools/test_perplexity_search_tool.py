"""Tests for PerplexitySearchTool."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from autogen_core import CancellationToken

from autogen_ext.tools.perplexity import (
    PerplexitySearchResult,
    PerplexitySearchTool,
    PerplexitySearchToolArgs,
)


def _mock_transport(
    captured: dict[str, Any],
    *,
    response_payload: dict[str, Any] | None = None,
    status: int = 200,
) -> httpx.MockTransport:
    if response_payload is None:
        response_payload = {
            "id": "abc",
            "results": [
                {
                    "title": "Result A",
                    "url": "https://a.example.com",
                    "snippet": "snippet A",
                    "date": "2025-01-02",
                },
                {
                    "title": "Result B",
                    "url": "https://b.example.com",
                    "snippet": "snippet B",
                },
            ],
        }

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["json"] = request.read().decode("utf-8") if status == 200 else None
        return httpx.Response(status, json=response_payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_run_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("PPLX_API_KEY", raising=False)

    tool = PerplexitySearchTool()

    with pytest.raises(ValueError, match="PERPLEXITY_API_KEY"):
        await tool.run(PerplexitySearchToolArgs(query="hello"), CancellationToken())


@pytest.mark.asyncio
async def test_run_returns_structured_results(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    transport = _mock_transport(captured)

    real_async_client = httpx.AsyncClient

    def fake_async_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_async_client(transport=transport)

    monkeypatch.setattr("autogen_ext.tools.perplexity._perplexity_search_tool.httpx.AsyncClient", fake_async_client)

    tool = PerplexitySearchTool(api_key="k")
    response = await tool.run(
        PerplexitySearchToolArgs(query="quantum computing", max_results=2),
        CancellationToken(),
    )

    assert len(response.results) == 2
    assert all(isinstance(r, PerplexitySearchResult) for r in response.results)
    assert response.results[0].title == "Result A"
    assert response.results[0].url == "https://a.example.com"
    assert response.results[0].date == "2025-01-02"
    assert response.results[1].date is None


@pytest.mark.asyncio
async def test_run_sends_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    captured: dict[str, Any] = {}
    transport = _mock_transport(captured)

    real_async_client = httpx.AsyncClient

    def fake_async_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_async_client(transport=transport)

    monkeypatch.setattr("autogen_ext.tools.perplexity._perplexity_search_tool.httpx.AsyncClient", fake_async_client)

    tool = PerplexitySearchTool(api_key="my-key")
    await tool.run(
        PerplexitySearchToolArgs(
            query="elections 2025",
            max_results=4,
            search_domain_filter=["nytimes.com", "-pinterest.com"],
            search_recency_filter="week",
        ),
        CancellationToken(),
    )

    request = captured["request"]
    assert str(request.url) == "https://api.perplexity.ai/search"
    assert request.headers["Authorization"] == "Bearer my-key"
    body = json.loads(captured["json"])
    assert body["query"] == "elections 2025"
    assert body["max_results"] == 4
    assert body["search_domain_filter"] == ["nytimes.com", "-pinterest.com"]
    assert body["search_recency_filter"] == "week"


@pytest.mark.asyncio
async def test_run_picks_up_pplx_api_key_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("PPLX_API_KEY", "alias-only")

    captured: dict[str, Any] = {}
    transport = _mock_transport(captured, response_payload={"results": []})

    real_async_client = httpx.AsyncClient

    def fake_async_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_async_client(transport=transport)

    monkeypatch.setattr("autogen_ext.tools.perplexity._perplexity_search_tool.httpx.AsyncClient", fake_async_client)

    tool = PerplexitySearchTool()
    await tool.run(PerplexitySearchToolArgs(query="x"), CancellationToken())

    assert captured["request"].headers["Authorization"] == "Bearer alias-only"


@pytest.mark.asyncio
async def test_run_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    transport = _mock_transport(captured, response_payload={"error": "nope"}, status=401)

    real_async_client = httpx.AsyncClient

    def fake_async_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_async_client(transport=transport)

    monkeypatch.setattr("autogen_ext.tools.perplexity._perplexity_search_tool.httpx.AsyncClient", fake_async_client)

    tool = PerplexitySearchTool(api_key="k")

    with pytest.raises(httpx.HTTPStatusError):
        await tool.run(PerplexitySearchToolArgs(query="x"), CancellationToken())


def test_tool_metadata() -> None:
    tool = PerplexitySearchTool(api_key="k")
    assert tool.name == "perplexity_search"
    assert "Perplexity Search API" in tool.description
    assert "Sonar" not in tool.description


def test_to_and_from_config_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("PPLX_API_KEY", raising=False)

    tool = PerplexitySearchTool(api_key="round-trip-key", default_max_results=7, timeout=12.0)
    config = tool.dump_component()
    rebuilt = PerplexitySearchTool.load_component(config)

    assert rebuilt._api_key == "round-trip-key"
    assert rebuilt._default_max_results == 7
    assert rebuilt._timeout == 12.0
