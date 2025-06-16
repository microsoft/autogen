from typing import Any, AsyncGenerator, Mapping, Optional, Sequence, Union

import pytest
from autogen_core import CancellationToken
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
from autogen_ext.agents.duckduckgo_search import DuckDuckGoSearchAgent
from autogen_ext.tools.web_search import DuckDuckGoSearchTool


class MockChatCompletionClient(ChatCompletionClient):
    """Mock chat completion client for testing."""

    def __init__(self) -> None:
        self._model_info = ModelInfo(
            vision=False,
            function_calling=True,
            json_output=False,
            family="test",
            structured_output=False,
        )

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
        """Mock create method."""
        return CreateResult(
            content="test response",
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


class TestDuckDuckGoSearchAgent:
    """Test suite for DuckDuckGoSearchAgent."""

    @pytest.fixture
    def mock_model_client(self) -> MockChatCompletionClient:
        """Create a mock model client for testing."""
        return MockChatCompletionClient()

    @pytest.fixture
    def search_agent(self, mock_model_client: MockChatCompletionClient) -> DuckDuckGoSearchAgent:
        """Create a DuckDuckGoSearchAgent instance for testing."""
        return DuckDuckGoSearchAgent(name="test_agent", model_client=mock_model_client)

    def test_agent_initialization_with_defaults(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test that the agent initializes correctly with default values."""
        agent = DuckDuckGoSearchAgent(name="test_agent", model_client=mock_model_client)

        assert agent.name == "test_agent"
        assert "research assistant" in agent.description.lower()
        assert "duckduckgo" in agent.description.lower()

        # Check that the agent has the DuckDuckGo search tool
        assert len(agent._tools) == 1  # type: ignore
        assert isinstance(agent._tools[0], DuckDuckGoSearchTool)  # type: ignore
        assert agent._tools[0].name == "duckduckgo_search"  # type: ignore

    def test_agent_initialization_with_custom_values(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test that the agent initializes correctly with custom values."""
        custom_description = "Custom research agent"
        custom_system_message = "You are a custom search agent."

        agent = DuckDuckGoSearchAgent(
            name="custom_agent",
            model_client=mock_model_client,
            description=custom_description,
            system_message=custom_system_message,
        )

        assert agent.name == "custom_agent"
        assert agent.description == custom_description
        # Note: We can't directly access system_message, but we can verify it was passed

    def test_agent_has_search_tool(self, search_agent: DuckDuckGoSearchAgent) -> None:
        """Test that the agent has the DuckDuckGo search tool configured."""
        tools = search_agent._tools  # type: ignore
        assert len(tools) == 1

        search_tool = tools[0]
        assert isinstance(search_tool, DuckDuckGoSearchTool)
        assert search_tool.name == "duckduckgo_search"

    def test_agent_system_message_content(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test that the default system message contains expected content."""
        agent = DuckDuckGoSearchAgent(name="test_agent", model_client=mock_model_client)

        # The system message should be in the agent's system messages
        system_messages = agent._system_messages  # type: ignore
        assert len(system_messages) == 1

        system_content = system_messages[0].content
        assert "research assistant" in system_content.lower()
        assert "duckduckgo" in system_content.lower()
        assert "search" in system_content.lower()
        assert "api key" in system_content.lower()

    def test_agent_inherits_from_assistant_agent(self, search_agent: DuckDuckGoSearchAgent) -> None:
        """Test that DuckDuckGoSearchAgent properly inherits from AssistantAgent."""
        from autogen_agentchat.agents import AssistantAgent

        assert isinstance(search_agent, AssistantAgent)

    def test_agent_model_client_assignment(
        self, search_agent: DuckDuckGoSearchAgent, mock_model_client: MockChatCompletionClient
    ) -> None:
        """Test that the model client is properly assigned."""
        assert search_agent._model_client == mock_model_client  # type: ignore

    def test_agent_with_additional_kwargs(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test that additional kwargs are passed to the parent class."""
        agent = DuckDuckGoSearchAgent(
            name="test_agent", model_client=mock_model_client, model_client_stream=True, reflect_on_tool_use=True
        )

        assert agent._model_client_stream is True  # type: ignore
        assert agent._reflect_on_tool_use is True  # type: ignore

    def test_agent_description_default(self, search_agent: DuckDuckGoSearchAgent) -> None:
        """Test the default description content."""
        description = search_agent.description
        expected_keywords = ["research", "assistant", "duckduckgo", "web", "information"]

        for keyword in expected_keywords:
            assert keyword.lower() in description.lower()

    def test_multiple_agents_have_separate_tools(self, mock_model_client: MockChatCompletionClient) -> None:
        """Test that multiple agents have separate tool instances."""
        agent1 = DuckDuckGoSearchAgent(name="agent1", model_client=mock_model_client)
        agent2 = DuckDuckGoSearchAgent(name="agent2", model_client=mock_model_client)

        # Each agent should have its own tool instance
        assert agent1._tools[0] is not agent2._tools[0]  # type: ignore
        assert isinstance(agent1._tools[0], DuckDuckGoSearchTool)  # type: ignore
        assert isinstance(agent2._tools[0], DuckDuckGoSearchTool)  # type: ignore
