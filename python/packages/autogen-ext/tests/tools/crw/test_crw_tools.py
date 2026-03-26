"""Unit tests for CRW web scraping tools."""

from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.crw import CrwCrawlTool, CrwMapTool, CrwScrapeTool
from autogen_ext.tools.crw._crw_tools import (
    CrawlArgs,
    MapArgs,
    MapResult,
    ScrapeArgs,
    ScrapeResult,
)


# --- CrwScrapeTool ---


class TestCrwScrapeTool:
    def test_tool_properties(self) -> None:
        tool = CrwScrapeTool(base_url="http://localhost:3000")
        assert tool.name == "scrape_url"
        assert "content" in tool.description
        assert "CRW" in tool.description

    def test_custom_base_url_strips_trailing_slash(self) -> None:
        tool = CrwScrapeTool(base_url="http://example.com:8080/")
        assert tool._base_url == "http://example.com:8080"

    def test_headers_without_api_key(self) -> None:
        tool = CrwScrapeTool()
        headers = tool._headers()
        assert headers == {"Content-Type": "application/json"}
        assert "Authorization" not in headers

    def test_headers_with_api_key(self) -> None:
        tool = CrwScrapeTool(api_key="test-key")
        headers = tool._headers()
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_scrape_success(self) -> None:
        tool = CrwScrapeTool(base_url="http://localhost:3000")
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "markdown": "# Hello World",
                "metadata": {"title": "Test Page", "sourceURL": "https://example.com"},
            },
        }
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client):
            result = await tool.run(ScrapeArgs(url="https://example.com"), CancellationToken())

        assert isinstance(result, ScrapeResult)
        assert result.success is True
        assert result.markdown == "# Hello World"
        assert result.title == "Test Page"

    @pytest.mark.asyncio
    async def test_scrape_error(self) -> None:
        tool = CrwScrapeTool(base_url="http://localhost:3000")

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client):
            result = await tool.run(ScrapeArgs(url="https://example.com"), CancellationToken())

        assert result.success is False
        assert "Connection refused" in (result.error or "")


# --- CrwCrawlTool ---


class TestCrwCrawlTool:
    def test_tool_properties(self) -> None:
        tool = CrwCrawlTool(base_url="http://localhost:3000")
        assert tool.name == "crawl_website"

    @pytest.mark.asyncio
    async def test_crawl_no_poll(self) -> None:
        tool = CrwCrawlTool(base_url="http://localhost:3000")
        mock_response = AsyncMock()
        mock_response.json.return_value = {"success": True, "id": "job-123"}
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client):
            result = await tool.run(
                CrawlArgs(url="https://example.com", poll=False),
                CancellationToken(),
            )

        assert result.success is True
        assert result.job_id == "job-123"
        assert result.status == "scraping"

    @pytest.mark.asyncio
    async def test_crawl_initial_failure(self) -> None:
        """POST /v1/crawl returns success=false or no job id."""
        tool = CrwCrawlTool(base_url="http://localhost:3000")
        mock_response = AsyncMock()
        mock_response.json.return_value = {"success": False, "error": "Invalid URL"}
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client):
            result = await tool.run(
                CrawlArgs(url="https://example.com"),
                CancellationToken(),
            )

        assert result.success is False
        assert result.error == "Invalid URL"

    @pytest.mark.asyncio
    async def test_crawl_poll_completed(self) -> None:
        tool = CrwCrawlTool(base_url="http://localhost:3000")

        post_response = AsyncMock()
        post_response.json.return_value = {"success": True, "id": "job-456"}
        post_response.raise_for_status = AsyncMock()

        get_response = AsyncMock()
        get_response.json.return_value = {
            "status": "completed",
            "total": 1,
            "completed": 1,
            "data": [
                {
                    "markdown": "# Page",
                    "metadata": {"title": "Page Title", "sourceURL": "https://example.com", "statusCode": 200},
                }
            ],
        }
        get_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = post_response
        mock_client.get.return_value = get_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client),
            patch("autogen_ext.tools.crw._crw_tools.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await tool.run(
                CrawlArgs(url="https://example.com", poll_interval=0.01),
                CancellationToken(),
            )

        assert result.success is True
        assert result.job_id == "job-456"
        assert len(result.pages) == 1
        assert result.pages[0].title == "Page Title"


# --- CrwMapTool ---


class TestCrwMapTool:
    def test_tool_properties(self) -> None:
        tool = CrwMapTool(base_url="http://localhost:3000")
        assert tool.name == "map_site"
        assert "links" in tool.description

    @pytest.mark.asyncio
    async def test_map_success(self) -> None:
        tool = CrwMapTool(base_url="http://localhost:3000")
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"links": ["https://example.com/a", "https://example.com/b"]},
        }
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client):
            result = await tool.run(MapArgs(url="https://example.com"), CancellationToken())

        assert isinstance(result, MapResult)
        assert result.success is True
        assert len(result.links) == 2

    @pytest.mark.asyncio
    async def test_map_error(self) -> None:
        tool = CrwMapTool(base_url="http://localhost:3000")

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autogen_ext.tools.crw._crw_tools.httpx.AsyncClient", return_value=mock_client):
            result = await tool.run(MapArgs(url="https://example.com"), CancellationToken())

        assert result.success is False
        assert "Timeout" in (result.error or "")
