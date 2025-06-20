from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.web_search._duckduckgo_search import (
    DuckDuckGoSearchArgs,
    DuckDuckGoSearchResult,
    DuckDuckGoSearchTool,
)


class TestDuckDuckGoSearchTool:
    """Test suite for DuckDuckGoSearchTool."""

    @pytest.fixture
    def search_tool(self) -> DuckDuckGoSearchTool:
        """Create a DuckDuckGoSearchTool instance for testing."""
        return DuckDuckGoSearchTool()

    @pytest.fixture
    def search_args(self) -> DuckDuckGoSearchArgs:
        """Create default search arguments for testing."""
        return DuckDuckGoSearchArgs(
            query="test query",
            num_results=3,
            include_snippets=True,
            include_content=False,  # Disable content fetching for faster tests
            language="en",
            safe_search=True,
        )

    @pytest.fixture
    def mock_html_response(self) -> str:
        """Mock HTML response from DuckDuckGo."""
        return """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="https://example.com/1">Test Result 1</a>
                    <a class="result__snippet">This is a test snippet 1</a>
                </div>
                <div class="result">
                    <a class="result__a" href="https://example.com/2">Test Result 2</a>
                    <a class="result__snippet">This is a test snippet 2</a>
                </div>
                <div class="result">
                    <a class="result__a" href="https://example.com/3">Test Result 3</a>
                    <a class="result__snippet">This is a test snippet 3</a>
                </div>
            </body>
        </html>
        """

    def test_tool_initialization(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test that the tool initializes correctly."""
        assert search_tool.name == "duckduckgo_search"
        assert "DuckDuckGo searches" in search_tool.description
        assert isinstance(search_tool.args_type, type) and issubclass(search_tool.args_type, DuckDuckGoSearchArgs)
        assert isinstance(search_tool.return_type, type) and issubclass(search_tool.return_type, DuckDuckGoSearchResult)

    def test_search_args_validation(self) -> None:
        """Test that search arguments are validated correctly."""
        # Valid args
        args = DuckDuckGoSearchArgs(query="test")
        assert args.query == "test"
        assert args.num_results == 3  # default
        assert args.include_snippets is True  # default

        # Test with custom values
        args = DuckDuckGoSearchArgs(
            query="custom query", num_results=5, include_snippets=False, language="es", region="us"
        )
        assert args.query == "custom query"
        assert args.num_results == 5
        assert args.include_snippets is False
        assert args.language == "es"
        assert args.region == "us"

    @pytest.mark.asyncio
    async def test_successful_search(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs, mock_html_response: str
    ) -> None:
        """Test a successful search operation."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert isinstance(result, DuckDuckGoSearchResult)
            assert len(result.results) == 3

            # Check first result
            first_result = result.results[0]
            assert first_result["title"] == "Test Result 1"
            assert first_result["link"] == "https://example.com/1"
            assert first_result["snippet"] == "This is a test snippet 1"

    @pytest.mark.asyncio
    async def test_search_with_content_fetching(
        self, search_tool: DuckDuckGoSearchTool, mock_html_response: str
    ) -> None:
        """Test search with content fetching enabled."""
        search_args = DuckDuckGoSearchArgs(
            query="test query", num_results=1, include_content=True, content_max_length=1000
        )

        # Mock the search response
        mock_search_response = MagicMock()
        mock_search_response.text = mock_html_response
        mock_search_response.raise_for_status = MagicMock()

        # Mock the content response
        mock_content_response = MagicMock()
        mock_content_response.text = "<html><body><h1>Test Content</h1><p>This is test content.</p></body></html>"
        mock_content_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_search_response, mock_content_response]

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            assert "content" in result.results[0]
            assert "Test Content" in result.results[0]["content"]

    @pytest.mark.asyncio
    async def test_search_without_snippets(self, search_tool: DuckDuckGoSearchTool, mock_html_response: str) -> None:
        """Test search with snippets disabled."""
        search_args = DuckDuckGoSearchArgs(query="test query", include_snippets=False, include_content=False)

        mock_response = MagicMock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            # Snippets should not be included
            for search_result in result.results:
                assert "snippet" not in search_result or search_result["snippet"] == ""

    @pytest.mark.asyncio
    async def test_num_results_limit(self, search_tool: DuckDuckGoSearchTool, mock_html_response: str) -> None:
        """Test that num_results is properly limited."""
        # Test with more than 10 results requested
        search_args = DuckDuckGoSearchArgs(
            query="test query",
            num_results=15,  # Should be limited to 10
            include_content=False,
        )

        mock_response = MagicMock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            # Should return only 3 results (from mock HTML)
            assert len(result.results) == 3

    @pytest.mark.asyncio
    async def test_http_error_handling(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of HTTP errors."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError, match="Error during search"):
                await search_tool.run(search_args, CancellationToken())

    @pytest.mark.asyncio
    async def test_content_fetch_error_handling(
        self, search_tool: DuckDuckGoSearchTool, mock_html_response: str
    ) -> None:
        """Test handling of content fetching errors."""
        search_args = DuckDuckGoSearchArgs(query="test query", num_results=1, include_content=True)

        # Mock successful search but failed content fetch
        mock_search_response = MagicMock()
        mock_search_response.text = mock_html_response
        mock_search_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First call succeeds (search), second call fails (content fetch)
        mock_client.get.side_effect = [mock_search_response, Exception("Content fetch error")]

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            # Should still return results, but with error message in content
            assert len(result.results) == 1
            assert "Error fetching content" in result.results[0]["content"]

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of empty search results."""
        empty_html = "<html><body></body></html>"

        mock_response = MagicMock()
        mock_response.text = empty_html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert isinstance(result, DuckDuckGoSearchResult)
            assert len(result.results) == 0

    def test_search_args_defaults(self) -> None:
        """Test that search arguments have correct defaults."""
        args = DuckDuckGoSearchArgs(query="test")

        assert args.num_results == 3
        assert args.include_snippets is True
        assert args.include_content is True
        assert args.content_max_length == 10000
        assert args.language == "en"
        assert args.region is None
        assert args.safe_search is True
