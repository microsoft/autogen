"""
Integration tests for DuckDuckGo Search Agent.

These tests demonstrate the full functionality of the DuckDuckGo search agent
and can be used to verify that the implementation works as expected.

Note: These tests make actual network requests to DuckDuckGo and may be slower
or fail if there are network issues. They are marked as integration tests
and can be skipped in CI environments.
"""

import asyncio
import os
import sys
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional, Sequence, Union

import pytest

# Add the src directory to Python path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResultMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.agents.duckduckgo_search._duckduckgo_agent import DuckDuckGoSearchAgent
from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchTool


class MockChatCompletionClient(ChatCompletionClient):
    """Mock chat completion client that simulates tool usage."""

    def __init__(self) -> None:
        self._model_info = ModelInfo(
            vision=False,
            function_calling=True,
            json_output=False,
            family="test",
            structured_output=False,
        )
        self.call_count = 0

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    @property
    def capabilities(self) -> ModelInfo:
        return self._model_info

    async def create(
        self,
        messages: Sequence[Union[SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage]],
        *,
        tools: Optional[Sequence[Union[Tool, ToolSchema]]] = None,
        json_output: Optional[Union[bool, type[Any]]] = None,
        extra_create_args: Optional[Mapping[str, Any]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Mock create method that simulates tool calling."""
        self.call_count += 1

        # Simulate the model deciding to use the search tool
        if self.call_count == 1 and tools:
            # First call: model decides to use search tool
            return CreateResult(
                content=[
                    FunctionCall(
                        id="call_123",
                        name="duckduckgo_search",
                        arguments='{"query": "Python programming", "num_results": 2, "include_content": false}',
                    )
                ],
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
                finish_reason="function_calls",
            )
        else:
            # Second call: model provides final response
            return CreateResult(
                content="Based on my search results, I found information about Python programming. Python is a popular programming language known for its simplicity and versatility.",
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
                finish_reason="stop",
            )

    async def create_stream(
        self,
        messages: Sequence[Union[SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage]],
        *,
        tools: Optional[Sequence[Union[Tool, ToolSchema]]] = None,
        json_output: Optional[Union[bool, type[Any]]] = None,
        extra_create_args: Optional[Mapping[str, Any]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Mock create_stream method."""
        yield "test response"

    async def close(self) -> None:
        """Mock close method."""
        pass

    def count_tokens(
        self,
        messages: Sequence[Union[SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage]],
        *,
        tools: Optional[Sequence[Union[Tool, ToolSchema]]] = None,
    ) -> int:
        """Mock count_tokens method."""
        return sum(len(str(msg)) for msg in messages)

    def remaining_tokens(
        self,
        messages: Sequence[Union[SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage]],
        *,
        tools: Optional[Sequence[Union[Tool, ToolSchema]]] = None,
    ) -> int:
        """Mock remaining_tokens method."""
        return 1000


@pytest.mark.integration
class TestDuckDuckGoIntegration:
    """Integration tests for DuckDuckGo functionality."""

    @pytest.fixture
    def mock_model_client(self) -> MockChatCompletionClient:
        """Create a mock model client for testing."""
        return MockChatCompletionClient()

    @pytest.mark.asyncio
    async def test_search_tool_real_request(self) -> None:
        """Test the search tool with a real request to DuckDuckGo."""
        search_tool = DuckDuckGoSearchTool()

        # Test with a simple query
        from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs

        args = DuckDuckGoSearchArgs(
            query="Python programming language",
            num_results=2,
            include_content=False,  # Skip content fetching for faster test
            include_snippets=True,
        )

        result = await search_tool.run(args, CancellationToken())

        # Verify we got results
        assert len(result.results) > 0
        assert len(result.results) <= 2

        # Check that each result has the expected structure
        for search_result in result.results:
            assert "title" in search_result
            assert "link" in search_result
            assert search_result["title"]  # Should not be empty
            assert search_result["link"].startswith("http")  # Should be a valid URL

            if args.include_snippets:
                assert "snippet" in search_result

    @pytest.mark.asyncio
    async def test_agent_with_mock_model(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test the agent with a mock model client that simulates tool usage."""
        agent = DuckDuckGoSearchAgent(name="test_researcher", model_client=mock_model_client)

        # This test just verifies the agent is set up correctly with mock model
        assert agent.name == "test_researcher"
        assert len(agent._tools) == 1  # type: ignore
        assert agent._tools[0].name == "duckduckgo_search"  # type: ignore

    @pytest.mark.asyncio
    async def test_search_with_content_fetching(self) -> None:
        """Test search with content fetching enabled (slower test)."""
        search_tool = DuckDuckGoSearchTool()

        from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs

        args = DuckDuckGoSearchArgs(
            query="OpenAI",
            num_results=1,
            include_content=True,
            content_max_length=500,  # Limit content length for faster test
        )

        result = await search_tool.run(args, CancellationToken())

        # Verify we got results with content
        assert len(result.results) > 0
        first_result = result.results[0]

        assert "title" in first_result
        assert "link" in first_result
        assert "content" in first_result
        assert first_result["content"]  # Should not be empty

        # Content should be markdown-formatted
        content = first_result["content"]
        assert len(content) <= 500 + 20  # Allow some margin for truncation message

    @pytest.mark.asyncio
    async def test_search_error_handling(self) -> None:
        """Test that the search tool handles errors gracefully."""
        search_tool = DuckDuckGoSearchTool()

        # Test with an invalid/problematic query
        from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs

        args = DuckDuckGoSearchArgs(
            query="",  # Empty query might cause issues
            num_results=1,
            include_content=False,
        )

        # This should either return empty results or handle the error gracefully
        try:
            result = await search_tool.run(args, CancellationToken())
            # If it succeeds, verify the result structure
            assert hasattr(result, "results")
            assert isinstance(result.results, list)
        except ValueError as e:
            # If it fails, it should be a ValueError with a descriptive message
            assert "search" in str(e).lower() or "error" in str(e).lower()

    def test_agent_configuration(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test that the agent is configured correctly."""
        agent = DuckDuckGoSearchAgent(name="config_test", model_client=mock_model_client)

        # Verify basic configuration
        assert agent.name == "config_test"
        assert "duckduckgo" in agent.description.lower()

        # Verify tool configuration
        assert len(agent._tools) == 1  # type: ignore
        search_tool = agent._tools[0]  # type: ignore
        assert isinstance(search_tool, DuckDuckGoSearchTool)
        assert search_tool.name == "duckduckgo_search"

        # Verify system message contains expected content
        system_messages = agent._system_messages  # type: ignore
        assert len(system_messages) == 1
        system_content = system_messages[0].content.lower()
        assert "research" in system_content
        assert "duckduckgo" in system_content
        assert "search" in system_content

    @pytest.mark.asyncio
    async def test_search_different_parameters(self) -> None:
        """Test search with different parameter combinations."""
        search_tool = DuckDuckGoSearchTool()

        from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs

        # Test with different languages and regions
        test_cases: List[Dict[str, Any]] = [
            {"query": "machine learning", "language": "en", "region": "us"},
            {"query": "artificial intelligence", "num_results": 1, "safe_search": True},
            {"query": "programming", "include_snippets": False, "include_content": False},
        ]

        for case in test_cases:
            args = DuckDuckGoSearchArgs(**case)
            result = await search_tool.run(args, CancellationToken())

            # Basic validation
            assert hasattr(result, "results")
            assert isinstance(result.results, list)

            # If we got results, verify structure
            if result.results:
                first_result = result.results[0]
                assert "title" in first_result
                assert "link" in first_result

                # Check snippets based on parameter
                include_snippets = case.get("include_snippets", True)
                if include_snippets:
                    # Snippets might not always be available
                    pass
                else:
                    # When snippets are disabled, they shouldn't be included
                    assert "snippet" not in first_result or not first_result["snippet"]


if __name__ == "__main__":
    # Run a simple test to verify functionality
    # ruff: noqa: T201
    async def simple_test() -> None:
        print("Testing DuckDuckGo Search Tool...")

        search_tool = DuckDuckGoSearchTool()
        from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs

        args = DuckDuckGoSearchArgs(query="Python programming", num_results=2, include_content=False)

        try:
            result = await search_tool.run(args, CancellationToken())
            print(f"Found {len(result.results)} results:")

            for i, search_result in enumerate(result.results, 1):
                print(f"{i}. {search_result['title']}")
                print(f"   URL: {search_result['link']}")
                if "snippet" in search_result:
                    print(f"   {search_result['snippet']}")
                print()

        except Exception as e:
            print(f"Error during test: {e}")

    asyncio.run(simple_test())
