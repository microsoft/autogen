"""Tests for the Exa search tools."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.exa import (
    ExaAnswerTool,
    ExaFindSimilarTool,
    ExaGetContentsTool,
    ExaSearchTool,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    """Return a MagicMock that behaves like an Exa client."""
    return MagicMock(spec_set=["search", "find_similar", "get_contents", "answer"])


def _result(
    title: str = "Example",
    url: str = "https://example.com",
    score: float = 0.95,
    published_date: str | None = "2026-01-01",
    author: str | None = "Author",
    text: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        url=url,
        score=score,
        published_date=published_date,
        author=author,
        text=text,
    )


def _response(results: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(results=results)


# ---------------------------------------------------------------------------
# ExaSearchTool
# ---------------------------------------------------------------------------


class TestExaSearchTool:
    @pytest.mark.asyncio
    async def test_basic_search(self) -> None:
        mock = _mock_client()
        mock.search.return_value = _response([_result(title="Result 1", url="https://a.com")])

        tool = ExaSearchTool(client=mock)
        result = await tool.run_json({"query": "test"}, CancellationToken())

        assert result.query == "test"
        assert len(result.results) == 1
        assert result.results[0].title == "Result 1"
        assert result.results[0].url == "https://a.com"
        mock.search.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_search_with_all_params(self) -> None:
        mock = _mock_client()
        mock.search.return_value = _response([_result()])

        tool = ExaSearchTool(
            num_results=5,
            max_characters=500,
            search_type="neural",
            category="news",
            include_domains=["example.com"],
            exclude_domains=["excluded.com"],
            start_published_date="2026-01-01",
            end_published_date="2026-12-31",
            livecrawl="always",
            user_location="US",
            moderation=True,
            client=mock,
        )
        await tool.run_json({"query": "q"}, CancellationToken())

        mock.search.assert_called_once_with(
            "q",
            num_results=5,
            type="neural",
            category="news",
            include_domains=["example.com"],
            exclude_domains=["excluded.com"],
            start_published_date="2026-01-01",
            end_published_date="2026-12-31",
            livecrawl="always",
            user_location="US",
            moderation=True,
            contents={"text": {"max_characters": 500}},
        )

    @pytest.mark.asyncio
    async def test_search_with_text_content(self) -> None:
        mock = _mock_client()
        mock.search.return_value = _response([_result(text="full article text")])

        tool = ExaSearchTool(max_characters=800, client=mock)
        result = await tool.run_json({"query": "q"}, CancellationToken())

        assert result.results[0].text == "full article text"
        mock.search.assert_called_once_with("q", contents={"text": {"max_characters": 800}})

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        mock = _mock_client()
        mock.search.return_value = _response([])

        tool = ExaSearchTool(client=mock)
        result = await tool.run_json({"query": "nothing"}, CancellationToken())

        assert result.query == "nothing"
        assert result.results == []

    @pytest.mark.asyncio
    async def test_search_handles_none_title(self) -> None:
        mock = _mock_client()
        mock.search.return_value = _response([_result(title=None)])  # type: ignore[arg-type]

        tool = ExaSearchTool(client=mock)
        result = await tool.run_json({"query": "q"}, CancellationToken())

        assert result.results[0].title == ""

    def test_search_tool_schema(self) -> None:
        tool = ExaSearchTool(client=_mock_client())
        schema = tool.schema

        assert schema["name"] == "exa_search"
        assert "parameters" in schema
        assert "query" in schema["parameters"]["properties"]

    def test_search_tool_config_round_trip(self) -> None:
        tool = ExaSearchTool(
            num_results=10,
            search_type="fast",
            category="news",
            client=_mock_client(),
        )
        config = tool._to_config()

        assert config.num_results == 10
        assert config.search_type == "fast"
        assert config.category == "news"


# ---------------------------------------------------------------------------
# ExaFindSimilarTool
# ---------------------------------------------------------------------------


class TestExaFindSimilarTool:
    @pytest.mark.asyncio
    async def test_basic_find_similar(self) -> None:
        mock = _mock_client()
        mock.find_similar.return_value = _response(
            [
                _result(title="Similar 1", url="https://similar.com"),
            ]
        )

        tool = ExaFindSimilarTool(client=mock)
        result = await tool.run_json({"url": "https://source.com"}, CancellationToken())

        assert len(result.results) == 1
        assert result.results[0].title == "Similar 1"
        mock.find_similar.assert_called_once_with("https://source.com")

    @pytest.mark.asyncio
    async def test_find_similar_with_params(self) -> None:
        mock = _mock_client()
        mock.find_similar.return_value = _response([_result()])

        tool = ExaFindSimilarTool(
            num_results=3,
            include_domains=["a.com"],
            exclude_domains=["b.com"],
            exclude_source_domain=True,
            category="company",
            client=mock,
        )
        await tool.run_json({"url": "https://x.com"}, CancellationToken())

        mock.find_similar.assert_called_once_with(
            "https://x.com",
            num_results=3,
            include_domains=["a.com"],
            exclude_domains=["b.com"],
            exclude_source_domain=True,
            category="company",
        )

    def test_find_similar_tool_schema(self) -> None:
        tool = ExaFindSimilarTool(client=_mock_client())
        schema = tool.schema

        assert schema["name"] == "exa_find_similar"
        assert "url" in schema["parameters"]["properties"]


# ---------------------------------------------------------------------------
# ExaGetContentsTool
# ---------------------------------------------------------------------------


class TestExaGetContentsTool:
    @pytest.mark.asyncio
    async def test_get_contents(self) -> None:
        mock = _mock_client()
        mock.get_contents.return_value = _response(
            [
                _result(title="Page", url="https://page.com", text="Full text here"),
            ]
        )

        tool = ExaGetContentsTool(client=mock)
        result = await tool.run_json({"urls": ["https://page.com"]}, CancellationToken())

        assert len(result.results) == 1
        assert result.results[0].url == "https://page.com"
        assert result.results[0].text == "Full text here"
        mock.get_contents.assert_called_once_with(["https://page.com"], text=True)

    @pytest.mark.asyncio
    async def test_get_contents_multiple_urls(self) -> None:
        mock = _mock_client()
        mock.get_contents.return_value = _response(
            [
                _result(title="A", url="https://a.com", text="text a"),
                _result(title="B", url="https://b.com", text="text b"),
            ]
        )

        tool = ExaGetContentsTool(client=mock)
        result = await tool.run_json({"urls": ["https://a.com", "https://b.com"]}, CancellationToken())

        assert len(result.results) == 2
        assert result.results[0].title == "A"
        assert result.results[1].title == "B"

    def test_get_contents_tool_schema(self) -> None:
        tool = ExaGetContentsTool(client=_mock_client())
        schema = tool.schema

        assert schema["name"] == "exa_get_contents"
        assert "urls" in schema["parameters"]["properties"]


# ---------------------------------------------------------------------------
# ExaAnswerTool
# ---------------------------------------------------------------------------


class TestExaAnswerTool:
    @pytest.mark.asyncio
    async def test_basic_answer(self) -> None:
        mock = _mock_client()
        mock.answer.return_value = SimpleNamespace(
            answer="42 is the answer.",
            citations=[
                SimpleNamespace(url="https://src.com", title="Source", text="relevant passage"),
            ],
        )

        tool = ExaAnswerTool(client=mock)
        result = await tool.run_json({"query": "What is the answer?"}, CancellationToken())

        assert result.answer == "42 is the answer."
        assert len(result.citations) == 1
        assert result.citations[0].url == "https://src.com"
        assert result.citations[0].text == "relevant passage"
        mock.answer.assert_called_once_with("What is the answer?", text=True)

    @pytest.mark.asyncio
    async def test_answer_no_citations(self) -> None:
        mock = _mock_client()
        mock.answer.return_value = SimpleNamespace(answer="No sources found.", citations=None)

        tool = ExaAnswerTool(client=mock)
        result = await tool.run_json({"query": "obscure question"}, CancellationToken())

        assert result.answer == "No sources found."
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_answer_handles_none_title(self) -> None:
        mock = _mock_client()
        mock.answer.return_value = SimpleNamespace(
            answer="answer",
            citations=[SimpleNamespace(url="https://x.com", title=None, text="text")],
        )

        tool = ExaAnswerTool(client=mock)
        result = await tool.run_json({"query": "q"}, CancellationToken())

        assert result.citations[0].title == ""

    def test_answer_tool_schema(self) -> None:
        tool = ExaAnswerTool(client=_mock_client())
        schema = tool.schema

        assert schema["name"] == "exa_answer"
        assert "query" in schema["parameters"]["properties"]
