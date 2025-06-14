"""Tests for OpenAIAgent built-in tool support."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_ext.agents.openai import OpenAIAgent
from openai import AsyncOpenAI


def create_mock_openai_client() -> AsyncOpenAI:
    """Create a mock OpenAI client for the Responses API."""
    client = AsyncMock(spec=AsyncOpenAI)

    async def mock_responses_create(**kwargs: Any) -> Any:
        _ = kwargs  # Mark as used

        class MockResponse:
            def __init__(self, output_text: str, id: str) -> None:
                self.output_text = output_text
                self.id = id

        return MockResponse(output_text="Response with tools", id="resp-123")

    responses = MagicMock()
    responses.create = AsyncMock(side_effect=mock_responses_create)
    client.responses = responses
    return client


@pytest.fixture
def mock_openai_client() -> AsyncOpenAI:
    return create_mock_openai_client()


class TestOpenAIAgentBuiltinTools:
    """Test class for OpenAIAgent built-in tool support."""

    def test_file_search_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that file_search tool is properly configured."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with file search",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["file_search"],
        )

        assert len(agent._tools) == 1  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "file_search"}  # type: ignore[reportPrivateUsage]

    def test_code_interpreter_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that code_interpreter tool is properly configured."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with code interpreter",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["code_interpreter"],
        )

        assert len(agent._tools) == 1  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "code_interpreter"}  # type: ignore[reportPrivateUsage]

    def test_web_search_preview_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that web_search_preview tool is properly configured."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with web search",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["web_search_preview"],
        )

        assert len(agent._tools) == 1  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "web_search_preview"}  # type: ignore[reportPrivateUsage]

    def test_computer_use_preview_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that computer_use_preview tool is properly configured."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with computer use",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["computer_use_preview"],
        )

        assert len(agent._tools) == 1  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "computer_use_preview"}  # type: ignore[reportPrivateUsage]

    def test_image_generation_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that image_generation tool is properly configured."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with image generation",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["image_generation"],
        )

        assert len(agent._tools) == 1  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "image_generation"}  # type: ignore[reportPrivateUsage]

    def test_mcp_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that mcp tool is properly configured."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with MCP",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["mcp"],
        )

        assert len(agent._tools) == 1  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "mcp"}  # type: ignore[reportPrivateUsage]

    def test_multiple_builtin_tools(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that multiple built-in tools can be configured together."""
        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with multiple tools",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["file_search", "code_interpreter", "web_search_preview"],
        )

        assert len(agent._tools) == 3  # type: ignore[reportPrivateUsage]
        expected_tools = [{"type": "file_search"}, {"type": "code_interpreter"}, {"type": "web_search_preview"}]
        assert agent._tools == expected_tools  # type: ignore[reportPrivateUsage]

    def test_unsupported_builtin_tool(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that unsupported built-in tool types raise an error."""
        with pytest.raises(ValueError, match="Unsupported built-in tool type: unsupported_tool"):
            OpenAIAgent(
                name="test_agent",
                description="Test agent with unsupported tool",
                client=mock_openai_client,
                model="gpt-4.1",
                instructions="You are a helpful assistant.",
                tools=["unsupported_tool"],  # type: ignore[reportArgumentType]
            )

    def test_mixed_tools_with_custom_function(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that built-in tools can be mixed with custom function tools."""
        from typing import Any, Mapping, Type

        from autogen_core import CancellationToken
        from autogen_core.tools import Tool, ToolSchema
        from pydantic import BaseModel

        class MockTool(Tool):
            @property
            def name(self) -> str:
                return "mock_tool"

            @property
            def description(self) -> str:
                return "A mock tool"

            @property
            def schema(self) -> ToolSchema:
                return ToolSchema(
                    name="mock_tool",
                    description="A mock tool",
                    parameters={"type": "object", "properties": {}, "required": []},
                )

            def args_type(self) -> Type[BaseModel]:
                return BaseModel

            def return_type(self) -> Type[Any]:
                return str

            def state_type(self) -> Type[BaseModel] | None:
                return None

            def return_value_as_string(self, value: Any) -> str:
                return str(value)

            async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> str:
                _ = args  # Mark as used
                _ = cancellation_token  # Mark as used
                return "mock result"

            async def load_state_json(self, state: Mapping[str, Any]) -> None:
                _ = state  # Mark as used

            async def save_state_json(self) -> Mapping[str, Any]:
                return {}

        mock_tool = MockTool()

        agent = OpenAIAgent(
            name="test_agent",
            description="Test agent with mixed tools",
            client=mock_openai_client,
            model="gpt-4.1",
            instructions="You are a helpful assistant.",
            tools=["file_search", mock_tool, "code_interpreter"],
        )

        assert len(agent._tools) == 3  # type: ignore[reportPrivateUsage]
        assert agent._tools[0] == {"type": "file_search"}  # type: ignore[reportPrivateUsage]
        assert agent._tools[1]["type"] == "function"  # type: ignore[reportPrivateUsage]
        assert agent._tools[1]["function"]["name"] == "mock_tool"  # type: ignore[reportPrivateUsage]
        assert agent._tools[2] == {"type": "code_interpreter"}  # type: ignore[reportPrivateUsage]

        # Check that the custom tool is in the tool map
        assert "mock_tool" in agent._tool_map  # type: ignore[reportPrivateUsage]
        assert agent._tool_map["mock_tool"] == mock_tool  # type: ignore[reportPrivateUsage]

    def test_unsupported_tool_type(self, mock_openai_client: AsyncOpenAI) -> None:
        """Test that unsupported tool types raise an error."""
        with pytest.raises(ValueError, match="Unsupported tool type"):
            OpenAIAgent(
                name="test_agent",
                description="Test agent with unsupported tool type",
                client=mock_openai_client,
                model="gpt-4.1",
                instructions="You are a helpful assistant.",
                tools=[123],  # type: ignore[reportArgumentType]  # Invalid tool type
            )
