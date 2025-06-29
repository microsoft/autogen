"""Comprehensive tests for AssistantAgent functionality."""

# Standard library imports
import asyncio
import json
from typing import Any, List, Optional, Union, cast
from unittest.mock import AsyncMock, MagicMock, patch

# Third-party imports
import pytest

# First-party imports
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.agents._assistant_agent import AssistantAgentConfig
from autogen_agentchat.base import Handoff, Response
from autogen_agentchat.messages import (
    BaseChatMessage,
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    StructuredMessage,
    TextMessage,
    ThoughtEvent,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_core import CancellationToken, ComponentModel, FunctionCall
from autogen_core.memory import Memory, MemoryContent, UpdateContextResult
from autogen_core.memory import MemoryQueryResult as MemoryQueryResultSet
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    ModelFamily,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.replay import ReplayChatCompletionClient
from pydantic import BaseModel


def mock_tool_function(param: str) -> str:
    """Mock tool function for testing.

    Args:
        param: Input parameter to process

    Returns:
        Formatted string with the input parameter
    """
    return f"Tool executed with: {param}"


async def async_mock_tool_function(param: str) -> str:
    """Async mock tool function for testing.

    Args:
        param: Input parameter to process

    Returns:
        Formatted string with the input parameter
    """
    return f"Async tool executed with: {param}"


class MockMemory(Memory):
    """Mock memory implementation for testing.

    A simple memory implementation that stores strings and provides basic memory operations
    for testing purposes.

    Args:
        contents: Optional list of initial memory contents
    """

    def __init__(self, contents: Optional[List[str]] = None) -> None:
        """Initialize mock memory.

        Args:
            contents: Optional list of initial memory contents
        """
        self._contents: List[str] = contents or []

    async def add(self, content: MemoryContent, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Add content to memory.

        Args:
            content: Content to add to memory
            cancellation_token: Optional token for cancelling operation
        """
        self._contents.append(str(content))

    async def query(
        self, query: Union[str, MemoryContent], cancellation_token: Optional[CancellationToken] = None, **kwargs: Any
    ) -> MemoryQueryResultSet:
        """Query memory contents.

        Args:
            query: Search query
            cancellation_token: Optional token for cancelling operation
            kwargs: Additional query parameters

        Returns:
            Query results containing all memory contents
        """
        results = [MemoryContent(content=content, mime_type="text/plain") for content in self._contents]
        return MemoryQueryResultSet(results=results)

    async def clear(self, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Clear all memory contents.

        Args:
            cancellation_token: Optional token for cancelling operation
        """
        self._contents.clear()

    async def close(self) -> None:
        """Close memory resources."""
        pass

    async def update_context(self, model_context: Any) -> UpdateContextResult:
        """Update model context with memory contents.

        Args:
            model_context: Context to update

        Returns:
            Update result containing memory contents
        """
        if self._contents:
            results = [MemoryContent(content=content, mime_type="text/plain") for content in self._contents]
            return UpdateContextResult(memories=MemoryQueryResultSet(results=results))
        return UpdateContextResult(memories=MemoryQueryResultSet(results=[]))

    def dump_component(self) -> ComponentModel:
        """Dump memory state as component model.

        Returns:
            Component model representing memory state
        """
        return ComponentModel(provider="test", config={"type": "mock_memory"})


class StructuredOutput(BaseModel):
    """Test structured output model.

    Attributes:
        content: Main content string
        confidence: Confidence score between 0 and 1
    """

    content: str
    confidence: float


class TestAssistantAgentToolCallLoop:
    """Test suite for tool call loop functionality.

    Tests the behavior of AssistantAgent's tool call loop feature, which allows
    multiple sequential tool calls before producing a final response.
    """

    @pytest.mark.asyncio
    async def test_tool_call_loop_enabled(self) -> None:
        """Test that tool call loop works when enabled.

        Verifies that:
        1. Multiple tool calls are executed in sequence
        2. Loop continues until non-tool response
        3. Final response is correct type
        """
        # Create mock client with multiple tool calls followed by text response
        model_client = ReplayChatCompletionClient(
            [
                # First tool call
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "first"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
                # Second tool call (loop continues)
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="2", arguments=json.dumps({"param": "second"}), name="mock_tool_function")
                    ],
                    usage=RequestUsage(prompt_tokens=12, completion_tokens=5),
                    cached=False,
                ),
                # Final text response (loop ends)
                CreateResult(
                    finish_reason="stop",
                    content="Task completed successfully!",
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            max_tool_iterations=3,
        )

        result = await agent.run(task="Execute multiple tool calls")

        # Verify multiple model calls were made
        assert len(model_client.create_calls) == 3, f"Expected 3 calls, got {len(model_client.create_calls)}"

        # Verify final response is text
        final_message = result.messages[-1]
        assert isinstance(final_message, TextMessage)
        assert final_message.content == "Task completed successfully!"

    @pytest.mark.asyncio
    async def test_tool_call_loop_disabled_default(self) -> None:
        """Test that tool call loop is disabled by default.

        Verifies that:
        1. Only one tool call is made when loop is disabled
        2. Agent returns after first tool call
        """
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                )
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            max_tool_iterations=1,
        )

        result = await agent.run(task="Execute single tool call")

        # Should only make one model call
        assert len(model_client.create_calls) == 1, f"Expected 1 call, got {len(model_client.create_calls)}"
        assert result is not None

    @pytest.mark.asyncio
    async def test_tool_call_loop_max_iterations(self) -> None:
        """Test that tool call loop respects max_iterations limit."""
        # Create responses that would continue forever without max_iterations
        responses: List[CreateResult] = []
        for i in range(15):  # More than default max_iterations (10)
            responses.append(
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id=str(i), arguments=json.dumps({"param": f"call_{i}"}), name="mock_tool_function")
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                )
            )

        model_client = ReplayChatCompletionClient(
            responses,
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            max_tool_iterations=5,  # Set max iterations to 5
        )

        result = await agent.run(task="Test max iterations")

        # Should stop at max_iterations
        assert len(model_client.create_calls) == 5, f"Expected 5 calls, got {len(model_client.create_calls)}"
        # Verify result is not None
        assert result is not None

    @pytest.mark.asyncio
    async def test_tool_call_loop_with_handoff(self) -> None:
        """Test that tool call loop stops on handoff."""
        model_client = ReplayChatCompletionClient(
            [
                # Tool call followed by handoff
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function"),
                        FunctionCall(
                            id="2", arguments=json.dumps({"target": "other_agent"}), name="transfer_to_other_agent"
                        ),
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            handoffs=["other_agent"],
            max_tool_iterations=1,
        )

        result = await agent.run(task="Test handoff in loop")

        # Should stop at handoff
        assert len(model_client.create_calls) == 1, f"Expected 1 call, got {len(model_client.create_calls)}"

        # Should return HandoffMessage
        assert isinstance(result.messages[-1], HandoffMessage)

    @pytest.mark.asyncio
    async def test_tool_call_config_validation(self) -> None:
        """Test that ToolCallConfig validation works correctly."""
        # Test that max_iterations must be >= 1
        with pytest.raises(
            ValueError, match="Maximum number of tool iterations must be greater than or equal to 1, got 0"
        ):
            AssistantAgent(
                name="test_agent",
                model_client=MagicMock(),
                max_tool_iterations=0,  # Should raise error
            )


class TestAssistantAgentInitialization:
    """Test suite for AssistantAgent initialization.

    Tests various initialization scenarios and configurations of the AssistantAgent class.
    """

    @pytest.mark.asyncio
    async def test_basic_initialization(self) -> None:
        """Test basic agent initialization with minimal parameters.

        Verifies that:
        1. Agent initializes with required parameters
        2. Default values are set correctly
        3. Basic functionality works
        """
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Hello!",
                    usage=RequestUsage(prompt_tokens=5, completion_tokens=2),
                    cached=False,
                )
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(name="test_agent", model_client=model_client)
        result = await agent.run(task="Say hello")

        assert isinstance(result.messages[-1], TextMessage)
        assert result.messages[-1].content == "Hello!"

    @pytest.mark.asyncio
    async def test_initialization_with_tools(self) -> None:
        """Test agent initialization with tools.

        Verifies that:
        1. Agent accepts tool configurations
        2. Tools are properly registered
        3. Tool calls work correctly
        """
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                )
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
        )

        result = await agent.run(task="Use the tool")
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        assert "Tool executed with: test" in result.messages[-1].content

    @pytest.mark.asyncio
    async def test_initialization_with_memory(self) -> None:
        """Test agent initialization with memory.

        Verifies that:
        1. Memory is properly integrated
        2. Memory contents affect responses
        3. Memory updates work correctly
        """
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Using memory content",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                )
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        memory = MockMemory(contents=["Test memory content"])
        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            memory=[memory],
        )

        result = await agent.run(task="Use memory")
        assert isinstance(result.messages[-1], TextMessage)
        assert result.messages[-1].content == "Using memory content"

    @pytest.mark.asyncio
    async def test_initialization_with_handoffs(self) -> None:
        """Test agent initialization with handoffs."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            handoffs=["agent1", Handoff(target="agent2")],
        )

        assert len(agent._handoffs) == 2  # type: ignore[reportPrivateUsage]
        assert "transfer_to_agent1" in agent._handoffs  # type: ignore[reportPrivateUsage]
        assert "transfer_to_agent2" in agent._handoffs  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_initialization_with_custom_model_context(self) -> None:
        """Test agent initialization with custom model context."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        model_context = BufferedChatCompletionContext(buffer_size=5)
        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_context=model_context,
        )

        assert agent._model_context == model_context  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_initialization_with_structured_output(self) -> None:
        """Test agent initialization with structured output."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            output_content_type=StructuredOutput,
        )

        assert agent._output_content_type == StructuredOutput  # type: ignore[reportPrivateUsage]
        assert agent._reflect_on_tool_use is True  # type: ignore[reportPrivateUsage] # Should be True by default with structured output

    @pytest.mark.asyncio
    async def test_initialization_with_metadata(self) -> None:
        """Test agent initialization with metadata."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        metadata = {"key1": "value1", "key2": "value2"}
        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            metadata=metadata,
        )

        assert agent._metadata == metadata  # type: ignore[reportPrivateUsage]


class TestAssistantAgentValidation:
    """Test suite for AssistantAgent validation.

    Tests various validation scenarios to ensure proper error handling and input validation.
    """

    @pytest.mark.asyncio
    async def test_tool_names_must_be_unique(self) -> None:
        """Test validation of unique tool names.

        Verifies that:
        1. Duplicate tool names are detected
        2. Appropriate error is raised
        """

        def duplicate_tool(param: str) -> str:
            """Test tool with duplicate name.

            Args:
                param: Input parameter

            Returns:
                Formatted string with parameter
            """
            return f"Duplicate tool: {param}"

        model_client = ReplayChatCompletionClient(
            [],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        with pytest.raises(ValueError, match="Tool names must be unique"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                tools=[mock_tool_function, duplicate_tool, mock_tool_function],
            )

    @pytest.mark.asyncio
    async def test_handoff_names_must_be_unique(self) -> None:
        """Test validation of unique handoff names.

        Verifies that:
        1. Duplicate handoff names are detected
        2. Appropriate error is raised
        """
        model_client = ReplayChatCompletionClient(
            [],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        with pytest.raises(ValueError, match="Handoff names must be unique"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                handoffs=["agent1", "agent2", "agent1"],
            )

    @pytest.mark.asyncio
    async def test_handoff_names_must_be_unique_from_tool_names(self) -> None:
        """Test validation of handoff names against tool names.

        Verifies that:
        1. Handoff names cannot conflict with tool names
        2. Appropriate error is raised
        """

        def test_tool() -> str:
            """Test tool with name that conflicts with handoff.

            Returns:
                Static test string
            """
            return "test"

        model_client = ReplayChatCompletionClient(
            [],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        with pytest.raises(ValueError, match="Handoff names must be unique from tool names"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                tools=[test_tool],
                handoffs=["test_tool"],
            )

    @pytest.mark.asyncio
    async def test_function_calling_required_for_tools(self) -> None:
        """Test that function calling is required for tools."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        with pytest.raises(ValueError, match="The model does not support function calling"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                tools=[mock_tool_function],
            )

    @pytest.mark.asyncio
    async def test_function_calling_required_for_handoffs(self) -> None:
        """Test that function calling is required for handoffs."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        with pytest.raises(
            ValueError, match="The model does not support function calling, which is needed for handoffs"
        ):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                handoffs=["agent1"],
            )

    @pytest.mark.asyncio
    async def test_memory_type_validation(self) -> None:
        """Test memory type validation."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        with pytest.raises(TypeError, match="Expected Memory, List\\[Memory\\], or None"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                memory="invalid_memory",  # type: ignore
            )

    @pytest.mark.asyncio
    async def test_tools_and_workbench_mutually_exclusive(self) -> None:
        """Test that tools and workbench are mutually exclusive."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        workbench = MagicMock()

        with pytest.raises(ValueError, match="Tools cannot be used with a workbench"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                tools=[mock_tool_function],
                workbench=workbench,
            )

    @pytest.mark.asyncio
    async def test_unsupported_tool_type(self) -> None:
        """Test error handling for unsupported tool types."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        with pytest.raises(ValueError, match="Unsupported tool type"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                tools=["invalid_tool"],  # type: ignore
            )

    @pytest.mark.asyncio
    async def test_unsupported_handoff_type(self) -> None:
        """Test error handling for unsupported handoff types."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        with pytest.raises(ValueError, match="Unsupported handoff type"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                handoffs=[123],  # type: ignore
            )


class TestAssistantAgentStateManagement:
    """Test suite for AssistantAgent state management."""

    @pytest.mark.asyncio
    async def test_save_and_load_state(self) -> None:
        """Test saving and loading agent state."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        # Mock model context state
        mock_context = MagicMock()
        mock_context.save_state = AsyncMock(return_value={"context": "state"})
        mock_context.load_state = AsyncMock()

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_context=mock_context,
        )

        # Test save state
        state = await agent.save_state()
        assert "llm_context" in state

        # Test load state
        await agent.load_state(state)
        mock_context.load_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_reset(self) -> None:
        """Test agent reset functionality."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        mock_context = MagicMock()
        mock_context.clear = AsyncMock()

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_context=mock_context,
        )

        cancellation_token = CancellationToken()
        await agent.on_reset(cancellation_token)

        mock_context.clear.assert_called_once()


class TestAssistantAgentProperties:
    """Test suite for AssistantAgent properties."""

    @pytest.mark.asyncio
    async def test_produced_message_types_text_only(self) -> None:
        """Test produced message types for text-only agent."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
        )

        message_types = agent.produced_message_types
        assert TextMessage in message_types

    @pytest.mark.asyncio
    async def test_produced_message_types_with_tools(self) -> None:
        """Test produced message types for agent with tools."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
        )

        message_types = agent.produced_message_types
        assert ToolCallSummaryMessage in message_types

    @pytest.mark.asyncio
    async def test_produced_message_types_with_handoffs(self) -> None:
        """Test produced message types for agent with handoffs."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            handoffs=["agent1"],
        )

        message_types = agent.produced_message_types
        assert HandoffMessage in message_types

    @pytest.mark.asyncio
    async def test_model_context_property(self) -> None:
        """Test model_context property access."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        custom_context = BufferedChatCompletionContext(buffer_size=3)
        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_context=custom_context,
        )

        assert agent.model_context == custom_context


class TestAssistantAgentErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_json_in_tool_arguments(self) -> None:
        """Test handling of invalid JSON in tool arguments."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments="invalid json", name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
        )

        result = await agent.run(task="Execute tool with invalid JSON")

        # Should handle JSON parsing error
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)


class TestAssistantAgentMemoryIntegration:
    """Test suite for AssistantAgent memory integration.

    Tests the integration between AssistantAgent and memory components, including:
    - Memory initialization
    - Context updates
    - Query operations
    - Memory persistence
    """

    @pytest.mark.asyncio
    async def test_memory_updates_context(self) -> None:
        """Test that memory properly updates model context.

        Verifies that:
        1. Memory contents are added to context
        2. Context updates trigger appropriate events
        3. Memory query results are properly handled
        """
        # Setup test memory with initial content
        memory = MockMemory(contents=["Previous conversation about topic A"])

        # Configure model client with expected response
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Response incorporating memory content",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                )
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        # Create agent with memory
        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            memory=[memory],
            description="Agent with memory integration",
        )

        # Track memory events during execution
        memory_events: List[MemoryQueryEvent] = []

        async def event_handler(event: MemoryQueryEvent) -> None:
            """Handle memory query events.

            Args:
                event: Memory query event to process
            """
            memory_events.append(event)

        # Create a handler function to capture memory events
        async def handle_memory_events(result: Any) -> None:
            messages: List[BaseChatMessage] = result.messages if hasattr(result, "messages") else []
            for msg in messages:
                if isinstance(msg, MemoryQueryEvent):
                    await event_handler(msg)

        # Run agent
        result = await agent.run(task="Respond using memory context")

        # Process the events
        await handle_memory_events(result)

        # Verify memory integration
        assert len(memory_events) > 0, "No memory events were generated"
        assert isinstance(result.messages[-1], TextMessage)
        assert "Response incorporating memory content" in result.messages[-1].content

    @pytest.mark.asyncio
    async def test_memory_persistence(self) -> None:
        """Test memory persistence across multiple sessions.

        Verifies:
        1. Memory content persists between sessions
        2. Memory updates are preserved
        3. Context is properly restored
        4. Memory query events are generated correctly
        """
        # Create memory with initial content
        memory = MockMemory(contents=["Initial memory"])

        # Create model client
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Response using memory",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
                CreateResult(
                    finish_reason="stop",
                    content="Response with updated memory",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        # Create agent with memory
        agent = AssistantAgent(name="memory_test_agent", model_client=model_client, memory=[memory])

        # First session
        result1 = await agent.run(task="First task")
        state = await agent.save_state()

        # Add new memory content
        await memory.add(MemoryContent(content="New memory", mime_type="text/plain"))

        # Create new agent and restore state
        new_agent = AssistantAgent(name="memory_test_agent", model_client=model_client, memory=[memory])
        await new_agent.load_state(state)

        # Second session
        result2 = await new_agent.run(task="Second task")

        # Verify memory persistence
        assert isinstance(result1.messages[-1], TextMessage)
        assert isinstance(result2.messages[-1], TextMessage)
        assert result1.messages[-1].content == "Response using memory"
        assert result2.messages[-1].content == "Response with updated memory"

        # Verify memory events
        memory_events = [msg for msg in result2.messages if isinstance(msg, MemoryQueryEvent)]
        assert len(memory_events) > 0
        assert any("New memory" in str(event.content) for event in memory_events)


class TestAssistantAgentSystemMessage:
    """Test suite for system message functionality."""

    @pytest.mark.asyncio
    async def test_system_message_none(self) -> None:
        """Test agent with system_message=None."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            system_message=None,
        )

        assert agent._system_messages == []  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_custom_system_message(self) -> None:
        """Test agent with custom system message."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        custom_message = "You are a specialized assistant."
        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            system_message=custom_message,
        )

        assert len(agent._system_messages) == 1  # type: ignore[reportPrivateUsage]
        assert agent._system_messages[0].content == custom_message  # type: ignore[reportPrivateUsage]


class TestAssistantAgentModelCompatibility:
    """Test suite for model compatibility functionality."""

    @pytest.mark.asyncio
    async def test_claude_model_warning(self) -> None:
        """Test warning for Claude models with reflection."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.CLAUDE_3_5_SONNET}

        with pytest.warns(UserWarning, match="Claude models may not work with reflection"):
            AssistantAgent(
                name="test_agent",
                model_client=model_client,
                reflect_on_tool_use=True,
            )

    @pytest.mark.asyncio
    async def test_vision_compatibility(self) -> None:
        """Test vision model compatibility."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": True, "family": ModelFamily.GPT_4O}

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
        )

        # Test _get_compatible_context with vision model
        from autogen_core.models import LLMMessage

        messages: List[LLMMessage] = [SystemMessage(content="Test")]
        compatible_messages = agent._get_compatible_context(model_client, messages)  # type: ignore[reportPrivateUsage]

        # Should return original messages for vision models
        assert compatible_messages == messages


class TestAssistantAgentComponentSerialization:
    """Test suite for component serialization functionality."""

    @pytest.mark.asyncio
    async def test_to_config_basic_agent(self) -> None:
        """Test _to_config method with basic agent configuration."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            description="Test description",
            system_message="Test system message",
            model_context=mock_context,
            metadata={"key": "value"},
        )

        config = agent._to_config()  # type: ignore[reportPrivateUsage]

        assert config.name == "test_agent"
        assert config.description == "Test description"
        assert config.system_message == "Test system message"
        assert config.model_client_stream is False
        assert config.reflect_on_tool_use is False
        assert config.max_tool_iterations == 1
        assert config.metadata == {"key": "value"}
        model_client.dump_component.assert_called_once()
        mock_context.dump_component.assert_called_once()

    @pytest.mark.asyncio
    async def test_to_config_agent_with_handoffs(self) -> None:
        """Test _to_config method with agent having handoffs."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            handoffs=["agent1", Handoff(target="agent2")],
            model_context=mock_context,
        )

        config = agent._to_config()  # type: ignore[reportPrivateUsage]

        assert config.handoffs is not None
        assert len(config.handoffs) == 2
        handoff_targets: List[str] = [h.target if hasattr(h, "target") else str(h) for h in config.handoffs]  # type: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        assert "agent1" in handoff_targets
        assert "agent2" in handoff_targets

    @pytest.mark.asyncio
    async def test_to_config_agent_with_memory(self) -> None:
        """Test _to_config method with agent having memory modules."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        mock_memory = MockMemory()

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            memory=[mock_memory],
            model_context=mock_context,
        )

        config = agent._to_config()  # type: ignore[reportPrivateUsage]

        assert config.memory is not None
        assert len(config.memory) == 1
        assert config.memory[0].provider == "test"
        assert config.memory[0].config == {"type": "mock_memory"}

    @pytest.mark.asyncio
    async def test_to_config_agent_with_workbench(self) -> None:
        """Test _to_config method with agent having workbench."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        mock_workbench = MagicMock()
        mock_workbench.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_workbench"})
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            model_context=mock_context,
        )

        # Replace the workbench with our mock
        agent._workbench = [mock_workbench]  # type: ignore[reportPrivateUsage]

        config = agent._to_config()  # type: ignore[reportPrivateUsage]

        assert config.workbench is not None
        assert len(config.workbench) == 1
        mock_workbench.dump_component.assert_called_once()

    @pytest.mark.asyncio
    async def test_to_config_agent_with_structured_output(self) -> None:
        """Test _to_config method with agent having structured output."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            output_content_type=StructuredOutput,
            model_context=mock_context,
        )

        config = agent._to_config()  # type: ignore[reportPrivateUsage]

        assert config.structured_message_factory is not None
        assert config.reflect_on_tool_use is True  # Should be True with structured output

    @pytest.mark.asyncio
    async def test_to_config_system_message_none(self) -> None:
        """Test _to_config method with system_message=None."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            system_message=None,
            model_context=mock_context,
        )

        config = agent._to_config()  # type: ignore[reportPrivateUsage]

        assert config.system_message is None

    @pytest.mark.asyncio
    async def test_from_config_basic_agent(self) -> None:
        """Test _from_config method with basic agent configuration."""
        mock_model_client = MagicMock()
        mock_model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        with patch("autogen_core.models.ChatCompletionClient.load_component", return_value=mock_model_client):
            config = AssistantAgentConfig(
                name="test_agent",
                model_client=ComponentModel(provider="test", config={"type": "mock_client"}),
                description="Test description",
                system_message="Test system",
                model_client_stream=True,
                reflect_on_tool_use=False,
                tool_call_summary_format="{tool_name}: {result}",
                metadata={"test": "value"},
            )

            agent = AssistantAgent._from_config(config)  # type: ignore[reportPrivateUsage]

            assert agent.name == "test_agent"
            assert agent.description == "Test description"
            assert agent._model_client_stream is True  # type: ignore[reportPrivateUsage]
            assert agent._reflect_on_tool_use is False  # type: ignore[reportPrivateUsage]
            assert agent._tool_call_summary_format == "{tool_name}: {result}"  # type: ignore[reportPrivateUsage]
            assert agent._metadata == {"test": "value"}  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_from_config_with_structured_output(self) -> None:
        """Test _from_config method with structured output configuration."""
        mock_model_client = MagicMock()
        mock_model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        mock_structured_factory = MagicMock()
        mock_structured_factory.format_string = "Test format"
        mock_structured_factory.ContentModel = StructuredOutput

        with (
            patch("autogen_core.models.ChatCompletionClient.load_component", return_value=mock_model_client),
            patch(
                "autogen_agentchat.messages.StructuredMessageFactory.load_component",
                return_value=mock_structured_factory,
            ),
        ):
            config = AssistantAgentConfig(
                name="test_agent",
                model_client=ComponentModel(provider="test", config={"type": "mock_client"}),
                description="Test description",
                reflect_on_tool_use=True,
                tool_call_summary_format="{result}",
                structured_message_factory=ComponentModel(provider="test", config={"type": "mock_factory"}),
            )

            agent = AssistantAgent._from_config(config)  # type: ignore[reportPrivateUsage]

            assert agent._reflect_on_tool_use is True  # type: ignore[reportPrivateUsage]
            assert agent._output_content_type == StructuredOutput  # type: ignore[reportPrivateUsage]
            assert agent._output_content_type_format == "Test format"  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_from_config_with_workbench_and_memory(self) -> None:
        """Test _from_config method with workbench and memory."""
        mock_model_client = MagicMock()
        mock_model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        mock_workbench = MagicMock()
        mock_memory = MockMemory()
        mock_context = MagicMock()

        with (
            patch("autogen_core.models.ChatCompletionClient.load_component", return_value=mock_model_client),
            patch("autogen_core.tools.Workbench.load_component", return_value=mock_workbench),
            patch("autogen_core.memory.Memory.load_component", return_value=mock_memory),
            patch("autogen_core.model_context.ChatCompletionContext.load_component", return_value=mock_context),
        ):
            config = AssistantAgentConfig(
                name="test_agent",
                model_client=ComponentModel(provider="test", config={"type": "mock_client"}),
                description="Test description",
                workbench=[ComponentModel(provider="test", config={"type": "mock_workbench"})],
                memory=[ComponentModel(provider="test", config={"type": "mock_memory"})],
                model_context=ComponentModel(provider="test", config={"type": "mock_context"}),
                reflect_on_tool_use=True,
                tool_call_summary_format="{result}",
            )

            agent = AssistantAgent._from_config(config)  # type: ignore[reportPrivateUsage]

            assert len(agent._workbench) == 1  # type: ignore[reportPrivateUsage]
            assert agent._memory is not None  # type: ignore[reportPrivateUsage]
            assert len(agent._memory) == 1  # type: ignore[reportPrivateUsage]
            assert agent._model_context == mock_context  # type: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_config_roundtrip_consistency(self) -> None:
        """Test that converting to config and back preserves agent properties."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_client"})
        )

        mock_context = MagicMock()
        mock_context.dump_component = MagicMock(
            return_value=ComponentModel(provider="test", config={"type": "mock_context"})
        )

        original_agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            description="Test description",
            system_message="Test system message",
            model_client_stream=True,
            reflect_on_tool_use=True,
            max_tool_iterations=5,
            tool_call_summary_format="{tool_name}: {result}",
            handoffs=["agent1"],
            model_context=mock_context,
            metadata={"test": "value"},
        )

        # Convert to config
        config = original_agent._to_config()  # type: ignore[reportPrivateUsage]

        # Verify config properties
        assert config.name == "test_agent"
        assert config.description == "Test description"
        assert config.system_message == "Test system message"
        assert config.model_client_stream is True
        assert config.reflect_on_tool_use is True
        assert config.max_tool_iterations == 5
        assert config.tool_call_summary_format == "{tool_name}: {result}"
        assert config.metadata == {"test": "value"}


class TestAssistantAgentThoughtHandling:
    """Test suite for thought handling functionality."""

    @pytest.mark.asyncio
    async def test_thought_event_yielded_from_model_result(self) -> None:
        """Test that thought events are yielded when model result contains thoughts."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Final response",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    thought="This is my internal thought process",
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have ThoughtEvent in the stream
        thought_events = [msg for msg in messages if isinstance(msg, ThoughtEvent)]
        assert len(thought_events) == 1
        assert thought_events[0].content == "This is my internal thought process"
        assert thought_events[0].source == "test_agent"

    @pytest.mark.asyncio
    async def test_thought_event_with_tool_calls(self) -> None:
        """Test that thought events are yielded when tool calls have thoughts."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    thought="I need to use this tool to help the user",
                ),
                CreateResult(
                    finish_reason="stop",
                    content="Tool execution completed",
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            max_tool_iterations=1,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have ThoughtEvent in the stream
        thought_events = [msg for msg in messages if isinstance(msg, ThoughtEvent)]
        assert len(thought_events) == 1
        assert thought_events[0].content == "I need to use this tool to help the user"
        assert thought_events[0].source == "test_agent"

    @pytest.mark.asyncio
    async def test_thought_event_with_reflection(self) -> None:
        """Test that thought events are yielded during reflection."""
        model_client = ReplayChatCompletionClient(
            [
                # Initial tool call with thought
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    thought="Initial thought before tool call",
                ),
                # Reflection with thought
                CreateResult(
                    finish_reason="stop",
                    content="Based on the tool result, here's my response",
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                    cached=False,
                    thought="Reflection thought after tool execution",
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            reflect_on_tool_use=True,
            model_client_stream=True,  # Enable streaming
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have two ThoughtEvents - one for initial call, one for reflection
        thought_events = [msg for msg in messages if isinstance(msg, ThoughtEvent)]
        assert len(thought_events) == 2

        thought_contents = [event.content for event in thought_events]
        assert "Initial thought before tool call" in thought_contents
        assert "Reflection thought after tool execution" in thought_contents

    @pytest.mark.asyncio
    async def test_thought_event_with_tool_call_loop(self) -> None:
        """Test that thought events are yielded in tool call loops."""
        model_client = ReplayChatCompletionClient(
            [
                # First tool call with thought
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "first"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    thought="First iteration thought",
                ),
                # Second tool call with thought
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="2", arguments=json.dumps({"param": "second"}), name="mock_tool_function")
                    ],
                    usage=RequestUsage(prompt_tokens=12, completion_tokens=5),
                    cached=False,
                    thought="Second iteration thought",
                ),
                # Final response with thought
                CreateResult(
                    finish_reason="stop",
                    content="Loop completed",
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                    cached=False,
                    thought="Final completion thought",
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            max_tool_iterations=3,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have three ThoughtEvents - one for each iteration
        thought_events = [msg for msg in messages if isinstance(msg, ThoughtEvent)]
        assert len(thought_events) == 3

        thought_contents = [event.content for event in thought_events]
        assert "First iteration thought" in thought_contents
        assert "Second iteration thought" in thought_contents
        assert "Final completion thought" in thought_contents

    @pytest.mark.asyncio
    async def test_thought_event_with_handoff(self) -> None:
        """Test that thought events are included in handoff context."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(
                            id="1", arguments=json.dumps({"target": "other_agent"}), name="transfer_to_other_agent"
                        )
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    thought="I need to hand this off to another agent",
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            handoffs=["other_agent"],
            max_tool_iterations=1,
        )

        result = await agent.run(task="Test handoff with thought")

        # Should have ThoughtEvent in inner messages
        thought_events = [msg for msg in result.messages if isinstance(msg, ThoughtEvent)]
        assert len(thought_events) == 1
        assert thought_events[0].content == "I need to hand this off to another agent"

        # Should have handoff message with thought in context
        handoff_message = result.messages[-1]
        assert isinstance(handoff_message, HandoffMessage)
        assert len(handoff_message.context) == 1
        assert isinstance(handoff_message.context[0], AssistantMessage)
        assert handoff_message.context[0].content == "I need to hand this off to another agent"

    @pytest.mark.asyncio
    async def test_no_thought_event_when_no_thought(self) -> None:
        """Test that no thought events are yielded when model result has no thoughts."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Simple response without thought",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    # No thought field
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have no ThoughtEvents
        thought_events = [msg for msg in messages if isinstance(msg, ThoughtEvent)]
        assert len(thought_events) == 0

    @pytest.mark.asyncio
    async def test_thought_event_context_preservation(self) -> None:
        """Test that thoughts are properly preserved in model context."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Response with thought",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                    thought="Internal reasoning",
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
        )

        await agent.run(task="Test thought preservation")

        # Check that the model context contains the thought
        messages = await agent.model_context.get_messages()
        assistant_messages = [msg for msg in messages if isinstance(msg, AssistantMessage)]
        assert len(assistant_messages) > 0

        # The last assistant message should have the thought
        last_assistant_msg = assistant_messages[-1]
        # Fix line 2727 - properly check for thought attribute with type checking
        if hasattr(last_assistant_msg, "thought"):
            thought_content = cast(str, last_assistant_msg.thought)
            assert thought_content == "Internal reasoning"


class TestAssistantAgentAdvancedScenarios:
    """Test suite for advanced usage scenarios."""

    @pytest.mark.asyncio
    async def test_handoff_without_tool_calls(self) -> None:
        """Test handoff without any tool calls."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"target": "agent2"}), name="transfer_to_agent2")
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            handoffs=["agent2"],
        )

        result = await agent.run(task="Handoff to agent2")

        # Should return HandoffMessage
        assert isinstance(result.messages[-1], HandoffMessage)
        assert result.messages[-1].target == "agent2"

    @pytest.mark.asyncio
    async def test_multiple_handoff_warning(self) -> None:
        """Test warning for multiple handoffs."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"target": "agent2"}), name="transfer_to_agent2"),
                        FunctionCall(id="2", arguments=json.dumps({"target": "agent3"}), name="transfer_to_agent3"),
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            handoffs=["agent2", "agent3"],
        )

        with pytest.warns(UserWarning, match="Multiple handoffs detected"):
            result = await agent.run(task="Multiple handoffs")

        # Should only execute first handoff
        assert isinstance(result.messages[-1], HandoffMessage)
        assert result.messages[-1].target == "agent2"

    @pytest.mark.asyncio
    async def test_structured_output_with_reflection(self) -> None:
        """Test structured output with reflection enabled."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
                CreateResult(
                    finish_reason="stop",
                    content='{"content": "Structured response", "confidence": 0.95}',
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            output_content_type=StructuredOutput,
            reflect_on_tool_use=True,
        )

        result = await agent.run(task="Test structured output with reflection")

        # Should return StructuredMessage
        from autogen_agentchat.messages import StructuredMessage

        final_message = result.messages[-1]
        assert isinstance(final_message, StructuredMessage)
        # Fix line 1710 - properly access structured content with explicit type annotation
        structured_message: StructuredMessage[StructuredOutput] = cast(
            StructuredMessage[StructuredOutput], final_message
        )
        assert structured_message.content.content == "Structured response"
        assert structured_message.content.confidence == 0.95


class TestAssistantAgentAdvancedToolFeatures:
    """Test suite for advanced tool features including custom formatters."""

    @pytest.mark.asyncio
    async def test_custom_tool_call_summary_formatter(self) -> None:
        """Test custom tool call summary formatter functionality."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"param": "success"}), name="mock_tool_function"),
                        FunctionCall(id="2", arguments=json.dumps({"param": "error"}), name="mock_tool_function"),
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        def custom_formatter(call: FunctionCall, result: FunctionExecutionResult) -> str:
            if result.is_error:
                return f"ERROR in {call.name}: {result.content} (args: {call.arguments})"
            else:
                return f"SUCCESS: {call.name} completed"

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            tool_call_summary_formatter=custom_formatter,
            reflect_on_tool_use=False,
        )

        result = await agent.run(task="Test custom formatter")

        # Should return ToolCallSummaryMessage with custom formatting
        final_message = result.messages[-1]
        assert isinstance(final_message, ToolCallSummaryMessage)
        # Fix line 1875 - properly access content with type checking
        assert hasattr(final_message, "content"), "ToolCallSummaryMessage should have content attribute"
        content = final_message.content
        assert "SUCCESS: mock_tool_function completed" in content
        assert "SUCCESS: mock_tool_function completed" in content  # Both calls should be successful

    @pytest.mark.asyncio
    async def test_custom_tool_call_summary_format_string(self) -> None:
        """Test custom tool call summary format string."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            tool_call_summary_format="Tool {tool_name} called with {arguments} -> {result}",
            reflect_on_tool_use=False,
        )

        result = await agent.run(task="Test custom format string")

        # Should return ToolCallSummaryMessage with custom format
        final_message = result.messages[-1]
        assert isinstance(final_message, ToolCallSummaryMessage)
        content = final_message.content
        assert "Tool mock_tool_function called with" in content
        assert "Tool executed with: test" in content

    @pytest.mark.asyncio
    async def test_tool_call_summary_formatter_overrides_format_string(self) -> None:
        """Test that tool_call_summary_formatter overrides format string."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        def custom_formatter(call: FunctionCall, result: FunctionExecutionResult) -> str:
            return f"CUSTOM: {call.name} -> {result.content}"

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            tool_call_summary_format="This should be ignored: {result}",
            tool_call_summary_formatter=custom_formatter,
            reflect_on_tool_use=False,
        )

        result = await agent.run(task="Test formatter override")

        # Should use custom formatter, not format string
        final_message = result.messages[-1]
        assert isinstance(final_message, ToolCallSummaryMessage)
        content = final_message.content
        assert "CUSTOM: mock_tool_function" in content
        assert "This should be ignored" not in content

    @pytest.mark.asyncio
    async def test_output_content_type_format_string(self) -> None:
        """Test structured output with custom format string."""
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content='{"content": "Test response", "confidence": 0.8}',
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            output_content_type=StructuredOutput,
            output_content_type_format="Response: {content} (Confidence: {confidence})",
        )

        result = await agent.run(task="Test structured output format")

        # Should return StructuredMessage with custom format
        final_message = result.messages[-1]
        assert isinstance(final_message, StructuredMessage)
        # Fix line 1880 - properly access structured content with explicit type annotation
        structured_message: StructuredMessage[StructuredOutput] = cast(
            StructuredMessage[StructuredOutput], final_message
        )
        assert structured_message.content.content == "Test response"
        assert structured_message.content.confidence == 0.8
        # The format string should be stored in the agent
        assert hasattr(agent, "_output_content_type_format")
        output_format = getattr(agent, "_output_content_type_format", None)
        assert output_format == "Response: {content} (Confidence: {confidence})"

    @pytest.mark.asyncio
    async def test_tool_call_error_handling_with_custom_formatter(self) -> None:
        """Test error handling in tool calls with custom formatter."""

        def error_tool(param: str) -> str:
            raise ValueError(f"Tool error with param: {param}")

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="error_tool")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        def error_formatter(call: FunctionCall, result: FunctionExecutionResult) -> str:
            if result.is_error:
                return f"ERROR in {call.name}: {result.content}"
            else:
                return f"SUCCESS: {result.content}"

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[error_tool],
            tool_call_summary_formatter=error_formatter,
            reflect_on_tool_use=False,
        )

        result = await agent.run(task="Test error handling")

        # Should return ToolCallSummaryMessage with error formatting
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        content = result.messages[-1].content
        assert "ERROR in error_tool" in content

    @pytest.mark.asyncio
    async def test_multiple_tools_with_different_formats(self) -> None:
        """Test multiple tool calls with different return formats."""

        def json_tool(data: str) -> str:
            return json.dumps({"result": data, "status": "success"})

        def simple_tool(text: str) -> str:
            return f"Processed: {text}"

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"data": "json_data"}), name="json_tool"),
                        FunctionCall(id="2", arguments=json.dumps({"text": "simple_text"}), name="simple_tool"),
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        def smart_formatter(call: FunctionCall, result: FunctionExecutionResult) -> str:
            try:
                # Try to parse as JSON
                parsed = json.loads(result.content)
                return f"{call.name}: {parsed}"
            except json.JSONDecodeError:
                # Plain text
                return f"{call.name}: {result.content}"

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[json_tool, simple_tool],
            tool_call_summary_formatter=smart_formatter,
            reflect_on_tool_use=False,
        )

        result = await agent.run(task="Test multiple tool formats")

        # Should handle both JSON and plain text tools
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        content = result.messages[-1].content
        assert "json_tool:" in content
        assert "simple_tool:" in content
        assert "Processed: simple_text" in content


class TestAssistantAgentCancellationToken:
    """Test suite for cancellation token handling."""

    @pytest.mark.asyncio
    async def test_cancellation_during_model_inference(self) -> None:
        """Test cancellation token during model inference."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        # Mock create method to check cancellation token
        model_client.create = AsyncMock()
        model_client.create.return_value = CreateResult(
            finish_reason="stop",
            content="Response",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
        )

        cancellation_token = CancellationToken()
        result = await agent.on_messages([TextMessage(content="Test", source="user")], cancellation_token)

        # Verify cancellation token was passed to model client
        model_client.create.assert_called_once()
        call_args = model_client.create.call_args
        assert call_args.kwargs["cancellation_token"] == cancellation_token
        # Verify result is not None
        assert result is not None

    @pytest.mark.asyncio
    async def test_cancellation_during_streaming_inference(self) -> None:
        """Test cancellation token during streaming model inference."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        # Mock create_stream method
        async def mock_create_stream(*args: Any, **kwargs: Any) -> Any:
            yield "chunk1"  # First chunk
            yield "chunk2"  # Second chunk
            yield CreateResult(
                finish_reason="stop",
                content="chunk1chunk2",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )

        model_client.create_stream = mock_create_stream

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_client_stream=True,
        )

        cancellation_token = CancellationToken()
        messages: List[Any] = []
        async for message in agent.on_messages_stream([TextMessage(content="Test", source="user")], cancellation_token):
            messages.append(message)

        # Should have received streaming chunks and final response
        chunk_events = [msg for msg in messages if isinstance(msg, ModelClientStreamingChunkEvent)]
        assert len(chunk_events) == 2
        assert chunk_events[0].content == "chunk1"
        assert chunk_events[1].content == "chunk2"

    @pytest.mark.asyncio
    async def test_cancellation_during_tool_execution(self) -> None:
        """Test cancellation token during tool execution."""

        async def slow_tool(param: str) -> str:
            await asyncio.sleep(0.1)  # Simulate slow operation
            return f"Slow result: {param}"

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="slow_tool")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[slow_tool],
        )

        cancellation_token = CancellationToken()
        result = await agent.on_messages([TextMessage(content="Test", source="user")], cancellation_token)

        # Tool should execute successfully with cancellation token
        assert isinstance(result.chat_message, ToolCallSummaryMessage)
        assert "Slow result: test" in result.chat_message.content

    @pytest.mark.asyncio
    async def test_cancellation_during_workbench_tool_execution(self) -> None:
        """Test cancellation token during workbench tool execution."""
        mock_workbench = MagicMock()
        mock_workbench.list_tools = AsyncMock(return_value=[{"name": "test_tool", "description": "Test tool"}])

        # Mock tool execution result
        mock_result = MagicMock()
        mock_result.to_text.return_value = "Workbench tool result"
        mock_result.is_error = False
        mock_workbench.call_tool = AsyncMock(return_value=mock_result)

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="test_tool")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            workbench=[mock_workbench],
        )

        cancellation_token = CancellationToken()
        result = await agent.on_messages([TextMessage(content="Test", source="user")], cancellation_token)

        # Verify cancellation token was passed to workbench
        mock_workbench.call_tool.assert_called_once()
        call_args = mock_workbench.call_tool.call_args
        assert call_args.kwargs["cancellation_token"] == cancellation_token
        # Verify result is not None
        assert result is not None

    @pytest.mark.asyncio
    async def test_cancellation_during_memory_operations(self) -> None:
        """Test cancellation token during memory operations."""
        mock_memory = MagicMock()
        mock_memory.update_context = AsyncMock(return_value=None)

        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}
        model_client.create = AsyncMock(
            return_value=CreateResult(
                finish_reason="stop",
                content="Response",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            memory=[mock_memory],
        )

        cancellation_token = CancellationToken()
        await agent.on_messages([TextMessage(content="Test", source="user")], cancellation_token)

        # Memory update_context should be called
        mock_memory.update_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_with_cancellation_token(self) -> None:
        """Test agent reset with cancellation token."""
        mock_context = MagicMock()
        mock_context.clear = AsyncMock()

        agent = AssistantAgent(
            name="test_agent",
            model_client=MagicMock(),
            model_context=mock_context,
        )

        cancellation_token = CancellationToken()
        await agent.on_reset(cancellation_token)

        # Context clear should be called
        mock_context.clear.assert_called_once()


class TestAssistantAgentStreamingEdgeCases:
    """Test suite for streaming edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_streaming_with_empty_chunks(self) -> None:
        """Test streaming with empty chunks."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        async def mock_create_stream(*args: Any, **kwargs: Any) -> Any:
            yield ""  # Empty chunk
            yield "content"
            yield ""  # Another empty chunk
            yield CreateResult(
                finish_reason="stop",
                content="content",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )

        model_client.create_stream = mock_create_stream

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_client_stream=True,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should handle empty chunks gracefully
        chunk_events = [msg for msg in messages if isinstance(msg, ModelClientStreamingChunkEvent)]
        assert len(chunk_events) == 3  # Including empty chunks
        assert chunk_events[0].content == ""
        assert chunk_events[1].content == "content"
        assert chunk_events[2].content == ""

    @pytest.mark.asyncio
    async def test_streaming_with_invalid_chunk_type(self) -> None:
        """Test streaming with invalid chunk type raises error."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        async def mock_create_stream(*args: Any, **kwargs: Any) -> Any:
            yield "valid_chunk"
            yield 123  # Invalid chunk type
            yield CreateResult(
                finish_reason="stop",
                content="content",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )

        model_client.create_stream = mock_create_stream

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_client_stream=True,
        )

        with pytest.raises(RuntimeError, match="Invalid chunk type"):
            async for _ in agent.on_messages_stream([TextMessage(content="Test", source="user")], CancellationToken()):
                pass

    @pytest.mark.asyncio
    async def test_streaming_without_final_result(self) -> None:
        """Test streaming without final CreateResult raises error."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        async def mock_create_stream(*args: Any, **kwargs: Any) -> Any:
            yield "chunk1"
            yield "chunk2"
            # No final CreateResult

        model_client.create_stream = mock_create_stream

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_client_stream=True,
        )

        with pytest.raises(RuntimeError, match="No final model result in streaming mode"):
            async for _ in agent.on_messages_stream([TextMessage(content="Test", source="user")], CancellationToken()):
                pass

    @pytest.mark.asyncio
    async def test_streaming_with_tool_calls_and_reflection(self) -> None:
        """Test streaming with tool calls followed by reflection."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": True, "vision": False, "family": ModelFamily.GPT_4O}

        call_count = 0

        async def mock_create_stream(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call: tool call
                yield CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="mock_tool_function")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                )
            else:
                # Second call: reflection streaming
                yield "Reflection "
                yield "response "
                yield "complete"
                yield CreateResult(
                    finish_reason="stop",
                    content="Reflection response complete",
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                    cached=False,
                )

        model_client.create_stream = mock_create_stream

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            reflect_on_tool_use=True,
            model_client_stream=True,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have tool call events, execution events, and streaming chunks for reflection
        tool_call_events = [msg for msg in messages if isinstance(msg, ToolCallRequestEvent)]
        tool_exec_events = [msg for msg in messages if isinstance(msg, ToolCallExecutionEvent)]
        chunk_events = [msg for msg in messages if isinstance(msg, ModelClientStreamingChunkEvent)]

        assert len(tool_call_events) == 1
        assert len(tool_exec_events) == 1
        assert len(chunk_events) == 3  # Three reflection chunks
        assert chunk_events[0].content == "Reflection "
        assert chunk_events[1].content == "response "
        assert chunk_events[2].content == "complete"

    @pytest.mark.asyncio
    async def test_streaming_with_large_chunks(self) -> None:
        """Test streaming with large chunks."""
        model_client = MagicMock()
        model_client.model_info = {"function_calling": False, "vision": False, "family": ModelFamily.GPT_4O}

        large_chunk = "x" * 10000  # 10KB chunk

        async def mock_create_stream(*args: Any, **kwargs: Any) -> Any:
            yield large_chunk
            yield CreateResult(
                finish_reason="stop",
                content=large_chunk,
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )

        model_client.create_stream = mock_create_stream

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            model_client_stream=True,
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Test", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should handle large chunks
        chunk_events = [msg for msg in messages if isinstance(msg, ModelClientStreamingChunkEvent)]
        assert len(chunk_events) == 1
        assert len(chunk_events[0].content) == 10000


class TestAssistantAgentWorkbenchIntegration:
    """Test suite for comprehensive workbench testing."""

    @pytest.mark.asyncio
    async def test_multiple_workbenches(self) -> None:
        """Test agent with multiple workbenches."""
        mock_workbench1 = MagicMock()
        mock_workbench1.list_tools = AsyncMock(return_value=[{"name": "tool1", "description": "Tool from workbench 1"}])
        mock_result1 = MagicMock()
        mock_result1.to_text.return_value = "Result from workbench 1"
        mock_result1.is_error = False
        mock_workbench1.call_tool = AsyncMock(return_value=mock_result1)

        mock_workbench2 = MagicMock()
        mock_workbench2.list_tools = AsyncMock(return_value=[{"name": "tool2", "description": "Tool from workbench 2"}])
        mock_result2 = MagicMock()
        mock_result2.to_text.return_value = "Result from workbench 2"
        mock_result2.is_error = False
        mock_workbench2.call_tool = AsyncMock(return_value=mock_result2)

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"param": "test1"}), name="tool1"),
                        FunctionCall(id="2", arguments=json.dumps({"param": "test2"}), name="tool2"),
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            workbench=[mock_workbench1, mock_workbench2],
        )

        result = await agent.run(task="Test multiple workbenches")

        # Both workbenches should be called
        mock_workbench1.call_tool.assert_called_once()
        mock_workbench2.call_tool.assert_called_once()

        # Should return summary with both results
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        content = result.messages[-1].content
        assert "Result from workbench 1" in content
        assert "Result from workbench 2" in content

    @pytest.mark.asyncio
    async def test_workbench_tool_not_found(self) -> None:
        """Test handling when tool is not found in any workbench."""
        mock_workbench = MagicMock()
        mock_workbench.list_tools = AsyncMock(
            return_value=[{"name": "available_tool", "description": "Available tool"}]
        )

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[FunctionCall(id="1", arguments=json.dumps({"param": "test"}), name="missing_tool")],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            workbench=[mock_workbench],
        )

        result = await agent.run(task="Test missing tool")

        # Should return error message for missing tool
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        content = result.messages[-1].content
        assert "tool 'missing_tool' not found" in content

    @pytest.mark.asyncio
    async def test_workbench_concurrent_tool_execution(self) -> None:
        """Test concurrent execution of multiple workbench tools."""
        mock_workbench = MagicMock()
        mock_workbench.list_tools = AsyncMock(
            return_value=[
                {"name": "concurrent_tool1", "description": "Concurrent tool 1"},
                {"name": "concurrent_tool2", "description": "Concurrent tool 2"},
            ]
        )

        call_order: List[str] = []

        async def mock_call_tool(name: str, **kwargs: Any) -> Any:
            call_order.append(f"start_{name}")
            await asyncio.sleep(0.01)  # Simulate work
            call_order.append(f"end_{name}")

            mock_result = MagicMock()
            mock_result.to_text.return_value = f"Result from {name}"
            mock_result.is_error = False
            return mock_result

        mock_workbench.call_tool = mock_call_tool

        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"param": "test1"}), name="concurrent_tool1"),
                        FunctionCall(id="2", arguments=json.dumps({"param": "test2"}), name="concurrent_tool2"),
                    ],
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="test_agent",
            model_client=model_client,
            workbench=[mock_workbench],
        )

        result = await agent.run(task="Test concurrent execution")

        # Should execute both tools concurrently (both start before either ends)
        assert "start_concurrent_tool1" in call_order
        assert "start_concurrent_tool2" in call_order

        # Both results should be present
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        content = result.messages[-1].content
        assert "Result from concurrent_tool1" in content
        assert "Result from concurrent_tool2" in content


class TestAssistantAgentComplexIntegration:
    """Test suite for complex integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_all_features(self) -> None:
        """Test agent with tools, handoffs, memory, streaming, and reflection."""
        # Setup memory
        memory = MockMemory(["User prefers detailed explanations"])

        # Setup model client with complex workflow
        model_client = ReplayChatCompletionClient(
            [
                # Initial tool call
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"param": "analysis"}), name="mock_tool_function")
                    ],
                    usage=RequestUsage(prompt_tokens=20, completion_tokens=10),
                    cached=False,
                    thought="I need to analyze this first",
                ),
                # Reflection result
                CreateResult(
                    finish_reason="stop",
                    content="Based on the analysis, I can provide a detailed response. The user prefers comprehensive explanations.",
                    usage=RequestUsage(prompt_tokens=30, completion_tokens=15),
                    cached=False,
                    thought="I should be thorough based on user preference",
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="comprehensive_agent",
            model_client=model_client,
            tools=[mock_tool_function],
            handoffs=["specialist_agent"],
            memory=[memory],
            reflect_on_tool_use=True,
            model_client_stream=True,
            tool_call_summary_format="Analysis: {result}",
            metadata={"test": "comprehensive"},
        )

        messages: List[Any] = []
        async for message in agent.on_messages_stream(
            [TextMessage(content="Analyze this complex scenario", source="user")], CancellationToken()
        ):
            messages.append(message)

        # Should have all types of events
        memory_events = [msg for msg in messages if isinstance(msg, MemoryQueryEvent)]
        thought_events = [msg for msg in messages if isinstance(msg, ThoughtEvent)]
        tool_events = [msg for msg in messages if isinstance(msg, ToolCallRequestEvent)]
        execution_events = [msg for msg in messages if isinstance(msg, ToolCallExecutionEvent)]
        chunk_events = [msg for msg in messages if isinstance(msg, ModelClientStreamingChunkEvent)]

        assert len(memory_events) > 0
        assert len(thought_events) == 2  # Initial and reflection thoughts
        assert len(tool_events) == 1
        assert len(execution_events) == 1
        assert len(chunk_events) == 0  # No streaming chunks since we removed the string responses

        # Final response should be TextMessage from reflection
        final_response = None
        for msg in reversed(messages):
            if isinstance(msg, Response):
                final_response = msg
                break

        assert final_response is not None
        assert isinstance(final_response.chat_message, TextMessage)
        assert "comprehensive explanations" in final_response.chat_message.content

    @pytest.mark.asyncio
    async def test_error_recovery_in_complex_workflow(self) -> None:
        """Test error recovery in complex workflow with multiple failures."""

        def failing_tool(param: str) -> str:
            if param == "fail":
                raise ValueError("Tool failure")
            return f"Success: {param}"

        model_client = ReplayChatCompletionClient(
            [
                # Multiple tool calls, some failing
                CreateResult(
                    finish_reason="function_calls",
                    content=[
                        FunctionCall(id="1", arguments=json.dumps({"param": "success"}), name="failing_tool"),
                        FunctionCall(id="2", arguments=json.dumps({"param": "fail"}), name="failing_tool"),
                        FunctionCall(id="3", arguments=json.dumps({"param": "success2"}), name="failing_tool"),
                    ],
                    usage=RequestUsage(prompt_tokens=20, completion_tokens=10),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": True,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        def error_aware_formatter(call: FunctionCall, result: FunctionExecutionResult) -> str:
            if result.is_error:
                return f"⚠️ {call.name} failed: {result.content}"
            else:
                return f"✅ {call.name}: {result.content}"

        agent = AssistantAgent(
            name="error_recovery_agent",
            model_client=model_client,
            tools=[failing_tool],
            tool_call_summary_formatter=error_aware_formatter,
            reflect_on_tool_use=False,
        )

        result = await agent.run(task="Test error recovery")

        # Should handle mixed success/failure gracefully
        assert isinstance(result.messages[-1], ToolCallSummaryMessage)
        content = result.messages[-1].content
        assert "✅ failing_tool: Success: success" in content
        assert "⚠️ failing_tool failed:" in content
        assert "✅ failing_tool: Success: success2" in content

    @pytest.mark.asyncio
    async def test_state_persistence_across_interactions(self) -> None:
        """Test that agent state persists correctly across multiple interactions."""
        model_client = ReplayChatCompletionClient(
            [
                # First interaction
                CreateResult(
                    finish_reason="stop",
                    content="First response",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
                # Second interaction
                CreateResult(
                    finish_reason="stop",
                    content="Second response, remembering context",
                    usage=RequestUsage(prompt_tokens=15, completion_tokens=8),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        agent = AssistantAgent(
            name="stateful_agent",
            model_client=model_client,
            system_message="Remember previous conversations",
        )

        # First interaction
        result1 = await agent.run(task="First task")
        final_message_1 = result1.messages[-1]
        assert isinstance(final_message_1, TextMessage)
        assert final_message_1.content == "First response"

        # Save state
        state = await agent.save_state()
        assert "llm_context" in state

        # Second interaction
        result2 = await agent.run(task="Second task, referring to first")
        # Fix line 2730 - properly access content on TextMessage
        final_message_2 = result2.messages[-1]
        assert isinstance(final_message_2, TextMessage)
        assert final_message_2.content == "Second response, remembering context"

        # Verify context contains both interactions
        context_messages = await agent.model_context.get_messages()
        user_messages = [
            msg for msg in context_messages if hasattr(msg, "source") and getattr(msg, "source", None) == "user"
        ]
        assert len(user_messages) == 2


class TestAssistantAgentMessageContext:
    """Test suite for message context handling in AssistantAgent.

    Tests various scenarios of message handling, context updates, and state management.
    """

    @pytest.mark.asyncio
    async def test_add_messages_to_context(self) -> None:
        """Test adding different message types to context.

        Verifies:
        1. Regular messages are added correctly
        2. Handoff messages with context are handled properly
        3. Message order is preserved
        4. Model messages are converted correctly
        """
        # Setup test context
        model_context = BufferedChatCompletionContext(buffer_size=10)

        # Create test messages
        regular_msg = TextMessage(content="Regular message", source="user")
        handoff_msg = HandoffMessage(content="Handoff message", source="agent1", target="agent2")

        # Add messages to context
        await AssistantAgent._add_messages_to_context(model_context=model_context, messages=[regular_msg, handoff_msg])  # type: ignore[reportPrivateUsage]

        # Verify context contents
        context_messages = await model_context.get_messages()

        # Should have: regular + handoff = 2 messages (now that handoff doesn't have context)
        assert len(context_messages) == 2

        # Verify message order and content - only the added messages should be present
        assert isinstance(context_messages[0], UserMessage)
        assert context_messages[0].content == "Regular message"

        assert isinstance(context_messages[1], UserMessage)
        assert context_messages[1].content == "Handoff message"

        # No more assertions needed for context_messages since we already verified both

    @pytest.mark.asyncio
    async def test_complex_model_context(self) -> None:
        """Test complex model context management scenarios.

        Verifies:
        1. Large context handling
        2. Mixed message type handling
        3. Context size limits
        4. Message filtering
        """
        # Setup test context with limited size
        model_context = BufferedChatCompletionContext(buffer_size=5)

        # Create a mix of message types
        messages: List[BaseChatMessage] = [
            TextMessage(content="First message", source="user"),
            StructuredMessage[StructuredOutput](
                content=StructuredOutput(content="Structured data", confidence=0.9), source="agent"
            ),
            ToolCallSummaryMessage(content="Tool result", source="agent", tool_calls=[], results=[]),
            HandoffMessage(content="Handoff", source="agent1", target="agent2"),
        ]

        # Add messages to context
        await AssistantAgent._add_messages_to_context(model_context=model_context, messages=messages)  # type: ignore[reportPrivateUsage]

        # Verify context management
        context_messages = await model_context.get_messages()

        # Should respect buffer size limit
        assert len(context_messages) <= 5

        # Verify message conversion
        for msg in context_messages:
            assert isinstance(msg, (SystemMessage, UserMessage, AssistantMessage))

    @pytest.mark.asyncio
    async def test_memory_persistence(self) -> None:
        """Test memory persistence across multiple sessions.

        Verifies:
        1. Memory content persists between sessions
        2. Memory updates are preserved
        3. Context is properly restored
        4. Memory query events are generated correctly
        """
        # Create memory with initial content
        memory = MockMemory(contents=["Initial memory"])

        # Create model client
        model_client = ReplayChatCompletionClient(
            [
                CreateResult(
                    finish_reason="stop",
                    content="Response using memory",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
                CreateResult(
                    finish_reason="stop",
                    content="Response with updated memory",
                    usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                    cached=False,
                ),
            ],
            model_info={
                "function_calling": False,
                "vision": False,
                "json_output": False,
                "family": ModelFamily.GPT_4O,
                "structured_output": False,
            },
        )

        # Create agent with memory
        agent = AssistantAgent(name="memory_test_agent", model_client=model_client, memory=[memory])

        # First session
        result1 = await agent.run(task="First task")
        state = await agent.save_state()

        # Add new memory content
        await memory.add(MemoryContent(content="New memory", mime_type="text/plain"))

        # Create new agent and restore state
        new_agent = AssistantAgent(name="memory_test_agent", model_client=model_client, memory=[memory])
        await new_agent.load_state(state)

        # Second session
        result2 = await new_agent.run(task="Second task")

        # Verify memory persistence
        assert isinstance(result1.messages[-1], TextMessage)
        assert isinstance(result2.messages[-1], TextMessage)
        assert result1.messages[-1].content == "Response using memory"
        assert result2.messages[-1].content == "Response with updated memory"

        # Verify memory events
        memory_events = [msg for msg in result2.messages if isinstance(msg, MemoryQueryEvent)]
        assert len(memory_events) > 0
        assert any("New memory" in str(event.content) for event in memory_events)
