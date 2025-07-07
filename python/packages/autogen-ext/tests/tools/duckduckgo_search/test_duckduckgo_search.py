from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.duckduckgo_search import (
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
            num_results=2,  # Should be limited to 2
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

            # Should return only 2 results (from mock HTML)
            assert len(result.results) == 2

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

    def test_search_args_edge_cases(self) -> None:
        """Test edge cases for search arguments."""
        # Test empty query handling in validation
        args = DuckDuckGoSearchArgs(query="")
        assert args.query == ""

        # Test maximum num_results
        args = DuckDuckGoSearchArgs(query="test", num_results=50)
        assert args.num_results == 50

        # Test zero num_results
        args = DuckDuckGoSearchArgs(query="test", num_results=0)
        assert args.num_results == 0

        # Test negative num_results
        args = DuckDuckGoSearchArgs(query="test", num_results=-5)
        assert args.num_results == -5

        # Test very long content_max_length
        args = DuckDuckGoSearchArgs(query="test", content_max_length=1000000)
        assert args.content_max_length == 1000000

        # Test None content_max_length
        args = DuckDuckGoSearchArgs(query="test", content_max_length=None)
        assert args.content_max_length is None

    @pytest.mark.asyncio
    async def test_search_url_building(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test that search URLs are built correctly with different parameters."""
        search_args = DuckDuckGoSearchArgs(
            query="test query with spaces", language="es", region="mx", safe_search=False
        )

        mock_response = MagicMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await search_tool.run(search_args, CancellationToken())

            # Verify the client.get was called with correct parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args

            # Check URL contains query
            assert "test%2Bquery%2Bwith%2Bspaces" in call_args[0][0] or "test+query+with+spaces" in call_args[0][0]

            # Check parameters
            params = call_args[1]["params"]
            assert params["kl"] == "es"
            assert params["kad"] == "MX"
            assert params["safesearch"] == "0"

    @pytest.mark.asyncio
    async def test_duckduckgo_redirect_url_handling(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of DuckDuckGo redirect URLs."""
        redirect_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A//example.com/test%3Fq%3Dvalue">Test Result</a>
                    <a class="result__snippet">Test snippet</a>
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = redirect_html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            assert result.results[0]["link"] == "https://example.com/test?q=value"

    @pytest.mark.asyncio
    async def test_protocol_relative_url_handling(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of protocol-relative URLs."""
        protocol_relative_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="//example.com/test">Test Result</a>
                    <a class="result__snippet">Test snippet</a>
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = protocol_relative_html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            assert result.results[0]["link"] == "https://example.com/test"

    @pytest.mark.asyncio
    async def test_relative_url_handling(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of relative URLs."""
        relative_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="/relative/path">Test Result</a>
                    <a class="result__snippet">Test snippet</a>
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = relative_html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            assert result.results[0]["link"] == "https://duckduckgo.com/relative/path"

    @pytest.mark.asyncio
    async def test_malformed_html_handling(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of malformed HTML."""
        malformed_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a">Missing href attribute</a>
                    <a class="result__snippet">Test snippet</a>
                </div>
                <div class="result">
                    <a class="result__a" href="https://example.com">Valid link without title</a>
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = malformed_html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            # Should handle malformed HTML gracefully
            assert len(result.results) == 2

            # First result should have empty link due to missing href
            assert result.results[0]["link"] == ""
            assert result.results[0]["title"] == "Missing href attribute"

            # Second result should be valid
            assert result.results[1]["link"] == "https://example.com"
            assert result.results[1]["title"] == "Valid link without title"

    @pytest.mark.asyncio
    async def test_content_fetching_with_various_html_structures(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test content fetching with different HTML structures."""
        search_args = DuckDuckGoSearchArgs(query="test", num_results=1, include_content=True)

        search_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="https://example.com">Test Result</a>
                    <a class="result__snippet">Test snippet</a>
                </div>
            </body>
        </html>
        """

        # Test content with main tag
        content_with_main = """
        <html>
            <body>
                <header>Header content</header>
                <nav>Navigation</nav>
                <main>
                    <h1>Main Content Title</h1>
                    <p>This is the main content that should be extracted.</p>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """

        mock_search_response = MagicMock()
        mock_search_response.text = search_html
        mock_search_response.raise_for_status = MagicMock()

        mock_content_response = MagicMock()
        mock_content_response.text = content_with_main
        mock_content_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_search_response, mock_content_response]

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            content = result.results[0]["content"]
            assert "Main Content Title" in content
            assert "main content that should be extracted" in content
            # Should not contain header, nav, or footer content
            assert "Header content" not in content
            assert "Navigation" not in content
            assert "Footer content" not in content

    @pytest.mark.asyncio
    async def test_content_fetching_fallback_to_largest_div(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test content fetching fallback to largest div when no main content found."""
        search_args = DuckDuckGoSearchArgs(query="test", num_results=1, include_content=True)

        search_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="https://example.com">Test Result</a>
                </div>
            </body>
        </html>
        """

        # Content with no main tag, should fallback to largest div
        content_no_main = """
        <html>
            <body>
                <div>Small content</div>
                <div>
                    <h1>Large Content Section</h1>
                    <p>This is a much larger content section that should be selected as the main content when no main tag is present. It contains multiple paragraphs and more text.</p>
                    <p>Another paragraph with more content to make this div larger.</p>
                </div>
                <div>Another small div</div>
            </body>
        </html>
        """

        mock_search_response = MagicMock()
        mock_search_response.text = search_html
        mock_search_response.raise_for_status = MagicMock()

        mock_content_response = MagicMock()
        mock_content_response.text = content_no_main
        mock_content_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_search_response, mock_content_response]

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            content = result.results[0]["content"]
            assert "Large Content Section" in content
            assert "larger content section" in content
            assert "Small content" not in content

    @pytest.mark.asyncio
    async def test_content_fetching_timeout_handling(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test handling of timeout errors during content fetching."""
        search_args = DuckDuckGoSearchArgs(query="test", num_results=1, include_content=True)

        search_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="https://example.com">Test Result</a>
                </div>
            </body>
        </html>
        """

        mock_search_response = MagicMock()
        mock_search_response.text = search_html
        mock_search_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First call succeeds (search), second call times out (content fetch)
        mock_client.get.side_effect = [mock_search_response, httpx.TimeoutException("Timeout")]

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            assert "Error fetching content: Timeout" in result.results[0]["content"]

    @pytest.mark.asyncio
    async def test_content_length_truncation(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test that content is properly truncated when it exceeds max length."""
        search_args = DuckDuckGoSearchArgs(query="test", num_results=1, include_content=True, content_max_length=100)

        search_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="https://example.com">Test Result</a>
                </div>
            </body>
        </html>
        """

        # Content that's longer than max_length
        long_content = (
            """
        <html>
            <body>
                <main>
                    <p>"""
            + "This is a very long paragraph that should be truncated. " * 20
            + """</p>
                </main>
            </body>
        </html>
        """
        )

        mock_search_response = MagicMock()
        mock_search_response.text = search_html
        mock_search_response.raise_for_status = MagicMock()

        mock_content_response = MagicMock()
        mock_content_response.text = long_content
        mock_content_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_search_response, mock_content_response]

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            content = result.results[0]["content"]
            assert len(content) <= 115  # 100 + "...(truncated)"
            assert content.endswith("...(truncated)")

    @pytest.mark.asyncio
    async def test_invalid_url_content_handling(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test handling of invalid URLs when fetching content."""
        search_args = DuckDuckGoSearchArgs(query="test", num_results=1, include_content=True)

        search_html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="invalid-url">Test Result</a>
                </div>
            </body>
        </html>
        """

        mock_search_response = MagicMock()
        mock_search_response.text = search_html
        mock_search_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_search_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await search_tool.run(search_args, CancellationToken())

            assert len(result.results) == 1
            assert result.results[0]["content"] == "Error: Invalid URL format"

    @pytest.mark.asyncio
    async def test_httpx_request_error_handling(
        self, search_tool: DuckDuckGoSearchTool, search_args: DuckDuckGoSearchArgs
    ) -> None:
        """Test handling of httpx RequestError."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError, match="Failed to perform search: Connection failed"):
                await search_tool.run(search_args, CancellationToken())

    def test_return_value_as_string_empty_results(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test return_value_as_string with empty results."""
        empty_result = DuckDuckGoSearchResult(results=[])
        string_output = search_tool.return_value_as_string(empty_result)
        assert string_output == "No search results found."

    def test_return_value_as_string_with_all_fields(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test return_value_as_string with all possible fields."""
        result = DuckDuckGoSearchResult(
            results=[
                {
                    "title": "Test Title 1",
                    "link": "https://example.com/1",
                    "snippet": "Test snippet 1",
                    "content": "Test content 1",
                },
                {
                    "title": "Test Title 2",
                    "link": "https://example.com/2",
                    "snippet": "Test snippet 2",
                    "content": "Test content 2",
                },
            ]
        )

        string_output = search_tool.return_value_as_string(result)

        assert "Result 1:" in string_output
        assert "Title: Test Title 1" in string_output
        assert "URL: https://example.com/1" in string_output
        assert "Snippet: Test snippet 1" in string_output
        assert "Content: Test content 1" in string_output

        assert "Result 2:" in string_output
        assert "Title: Test Title 2" in string_output
        assert "URL: https://example.com/2" in string_output
        assert "Snippet: Test snippet 2" in string_output
        assert "Content: Test content 2" in string_output

    def test_return_value_as_string_missing_fields(self, search_tool: DuckDuckGoSearchTool) -> None:
        """Test return_value_as_string with missing optional fields."""
        result = DuckDuckGoSearchResult(
            results=[
                {
                    "title": "Test Title",
                    "link": "https://example.com",
                    # No snippet or content
                }
            ]
        )

        string_output = search_tool.return_value_as_string(result)

        assert "Result 1:" in string_output
        assert "Title: Test Title" in string_output
        assert "URL: https://example.com" in string_output
        assert "Snippet:" not in string_output
        assert "Content:" not in string_output
