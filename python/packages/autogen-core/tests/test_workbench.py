from typing import Annotated, AsyncGenerator

import pytest
from autogen_core._cancellation_token import CancellationToken
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import (
    BaseStreamTool,
    FunctionTool,
    StaticStreamWorkbench,
    StaticWorkbench,
    TextResultContent,
    ToolResult,
    Workbench,
)
from pydantic import BaseModel


class StreamArgs(BaseModel):
    count: int


class StreamResult(BaseModel):
    final_count: int


class StreamItem(BaseModel):
    current: int


class StreamTool(BaseStreamTool[StreamArgs, StreamItem, StreamResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=StreamArgs,
            return_type=StreamResult,
            name="test_stream_tool",
            description="A test stream tool that counts up to a number.",
        )

    async def run(self, args: StreamArgs, cancellation_token: CancellationToken) -> StreamResult:
        # For the regular run method, just return the final result
        return StreamResult(final_count=args.count)

    async def run_stream(
        self, args: StreamArgs, cancellation_token: CancellationToken
    ) -> AsyncGenerator[StreamItem | StreamResult, None]:
        for i in range(1, args.count + 1):
            if cancellation_token.is_cancelled():
                break
            yield StreamItem(current=i)
        yield StreamResult(final_count=args.count)


class StreamToolWithError(BaseStreamTool[StreamArgs, StreamItem, StreamResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=StreamArgs,
            return_type=StreamResult,
            name="test_stream_tool_error",
            description="A test stream tool that raises an error.",
        )

    async def run(self, args: StreamArgs, cancellation_token: CancellationToken) -> StreamResult:
        # For the regular run method, just raise the error
        raise ValueError("Stream tool error")

    async def run_stream(
        self, args: StreamArgs, cancellation_token: CancellationToken
    ) -> AsyncGenerator[StreamItem | StreamResult, None]:
        yield StreamItem(current=1)
        raise ValueError("Stream tool error")


@pytest.mark.asyncio
async def test_static_workbench() -> None:
    def test_tool_func_1(x: Annotated[int, "The number to double."]) -> int:
        return x * 2

    def test_tool_func_2(x: Annotated[int, "The number to add 2."]) -> int:
        raise ValueError("This is a test error")  # Simulate an error

    test_tool_1 = FunctionTool(
        test_tool_func_1,
        name="test_tool_1",
        description="A test tool that doubles a number.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    test_tool_2 = FunctionTool(
        test_tool_func_2,
        name="test_tool_2",
        description="A test tool that adds 2 to a number.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    # Create a StaticWorkbench instance with the test tools.
    async with StaticWorkbench(tools=[test_tool_1, test_tool_2]) as workbench:
        # List tools
        tools = await workbench.list_tools()
        assert len(tools) == 2
        assert "description" in tools[0]
        assert "parameters" in tools[0]
        assert tools[0]["name"] == "test_tool_1"
        assert tools[0]["description"] == "A test tool that doubles a number."
        assert tools[0]["parameters"] == {
            "type": "object",
            "properties": {"x": {"type": "integer", "title": "X", "description": "The number to double."}},
            "required": ["x"],
            "additionalProperties": False,
        }
        assert "description" in tools[1]
        assert "parameters" in tools[1]
        assert tools[1]["name"] == "test_tool_2"
        assert tools[1]["description"] == "A test tool that adds 2 to a number."
        assert tools[1]["parameters"] == {
            "type": "object",
            "properties": {"x": {"type": "integer", "title": "X", "description": "The number to add 2."}},
            "required": ["x"],
            "additionalProperties": False,
        }

        # Call tools
        result_1 = await workbench.call_tool("test_tool_1", {"x": 5})
        assert result_1.name == "test_tool_1"
        assert result_1.result[0].type == "TextResultContent"
        assert result_1.result[0].content == "10"
        assert result_1.to_text() == "10"
        assert result_1.is_error is False

        # Call tool with error
        result_2 = await workbench.call_tool("test_tool_2", {"x": 5})
        assert result_2.name == "test_tool_2"
        assert result_2.result[0].type == "TextResultContent"
        assert result_2.result[0].content == "This is a test error"
        assert result_2.to_text() == "This is a test error"
        assert result_2.is_error is True

        # Save state.
        state = await workbench.save_state()
        assert state["type"] == "StaticWorkbenchState"
        assert "tools" in state
        assert len(state["tools"]) == 2

        # Dump config.
        config = workbench.dump_component()

    # Load the workbench from the config.
    async with Workbench.load_component(config) as new_workbench:
        # Load state.
        await new_workbench.load_state(state)

        # Verify that the tools are still available after loading the state.
        tools = await new_workbench.list_tools()
        assert len(tools) == 2
        assert "description" in tools[0]
        assert "parameters" in tools[0]
        assert tools[0]["name"] == "test_tool_1"
        assert tools[0]["description"] == "A test tool that doubles a number."
        assert tools[0]["parameters"] == {
            "type": "object",
            "properties": {"x": {"type": "integer", "title": "X", "description": "The number to double."}},
            "required": ["x"],
            "additionalProperties": False,
        }
        assert "description" in tools[1]
        assert "parameters" in tools[1]
        assert tools[1]["name"] == "test_tool_2"
        assert tools[1]["description"] == "A test tool that adds 2 to a number."
        assert tools[1]["parameters"] == {
            "type": "object",
            "properties": {"x": {"type": "integer", "title": "X", "description": "The number to add 2."}},
            "required": ["x"],
            "additionalProperties": False,
        }

        # Call tools
        result_1 = await new_workbench.call_tool("test_tool_1", {"x": 5})
        assert result_1.name == "test_tool_1"
        assert result_1.result[0].type == "TextResultContent"
        assert result_1.result[0].content == "10"
        assert result_1.to_text() == "10"
        assert result_1.is_error is False

        # Call tool with error
        result_2 = await new_workbench.call_tool("test_tool_2", {"x": 5})
        assert result_2.name == "test_tool_2"
        assert result_2.result[0].type == "TextResultContent"
        assert result_2.result[0].content == "This is a test error"
        assert result_2.to_text() == "This is a test error"
        assert result_2.is_error is True


@pytest.mark.asyncio
async def test_static_stream_workbench_call_tool_stream() -> None:
    """Test call_tool_stream with streaming tools and regular tools."""

    def regular_tool_func(x: Annotated[int, "The number to double."]) -> int:
        return x * 2

    regular_tool = FunctionTool(
        regular_tool_func,
        name="regular_tool",
        description="A regular tool that doubles a number.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    stream_tool = StreamTool()
    stream_tool_with_error = StreamToolWithError()

    async with StaticStreamWorkbench(tools=[regular_tool, stream_tool, stream_tool_with_error]) as workbench:
        # Test streaming tool
        results: list[StreamItem | StreamResult | ToolResult] = []
        async for result in workbench.call_tool_stream("test_stream_tool", {"count": 3}):
            results.append(result)

        # Should get 3 intermediate results and 1 final result
        assert len(results) == 4

        # Check intermediate results (StreamItem objects)
        for i, result in enumerate(results[:3]):
            assert isinstance(result, StreamItem)
            assert result.current == i + 1

        # Check final result (ToolResult)
        final_result = results[-1]
        assert isinstance(final_result, ToolResult)
        assert final_result.name == "test_stream_tool"
        assert final_result.is_error is False
        assert final_result.result[0].type == "TextResultContent"
        assert "final_count" in final_result.result[0].content

        # Test regular (non-streaming) tool
        results_regular: list[ToolResult] = []
        async for result in workbench.call_tool_stream("regular_tool", {"x": 5}):
            results_regular.append(result)  # type: ignore

        # Should get only 1 result for non-streaming tool
        assert len(results_regular) == 1
        final_result = results_regular[0]
        assert final_result.name == "regular_tool"
        assert final_result.is_error is False
        assert final_result.result[0].content == "10"

        # Test streaming tool with error
        results_error: list[StreamItem | ToolResult] = []
        async for result in workbench.call_tool_stream("test_stream_tool_error", {"count": 3}):
            results_error.append(result)  # type: ignore

        # Should get 1 intermediate result and 1 error result
        assert len(results_error) == 2

        # Check intermediate result
        intermediate_result = results_error[0]
        assert isinstance(intermediate_result, StreamItem)
        assert intermediate_result.current == 1

        # Check error result
        error_result = results_error[1]
        assert isinstance(error_result, ToolResult)
        assert error_result.name == "test_stream_tool_error"
        assert error_result.is_error is True
        result_content = error_result.result[0]
        assert isinstance(result_content, TextResultContent)
        assert "Stream tool error" in result_content.content

        # Test tool not found
        results_not_found: list[ToolResult] = []
        async for result in workbench.call_tool_stream("nonexistent_tool", {"x": 5}):
            results_not_found.append(result)  # type: ignore

        assert len(results_not_found) == 1
        error_result = results_not_found[0]
        assert error_result.name == "nonexistent_tool"
        assert error_result.is_error is True
        result_content = error_result.result[0]
        assert isinstance(result_content, TextResultContent)
        assert "Tool nonexistent_tool not found" in result_content.content

        # Test with no arguments
        results_no_args: list[StreamItem | StreamResult | ToolResult] = []
        async for result in workbench.call_tool_stream("test_stream_tool", {"count": 1}):
            results_no_args.append(result)  # type: ignore

        assert len(results_no_args) == 2  # 1 intermediate + 1 final

        # Test with None arguments
        results_none: list[ToolResult] = []
        async for result in workbench.call_tool_stream("regular_tool", None):
            results_none.append(result)  # type: ignore

        # Should still work but may get error due to missing required argument
        assert len(results_none) == 1
        result = results_none[0]
        assert result.name == "regular_tool"
        # This should error because x is required
        assert result.is_error is True


@pytest.mark.asyncio
async def test_static_stream_workbench_call_tool_stream_cancellation() -> None:
    """Test call_tool_stream with cancellation token."""
    stream_tool = StreamTool()

    async with StaticStreamWorkbench(tools=[stream_tool]) as workbench:
        # Test with cancellation token
        cancellation_token = CancellationToken()

        results: list[StreamItem | StreamResult | ToolResult] = []
        async for result in workbench.call_tool_stream("test_stream_tool", {"count": 5}, cancellation_token):
            results.append(result)  # type: ignore
            if len(results) == 2:  # Cancel after 2 results
                cancellation_token.cancel()

        # Should get at least 2 results before cancellation
        assert len(results) >= 2


@pytest.mark.asyncio
async def test_static_stream_workbench_inheritance() -> None:
    """Test that StaticStreamWorkbench inherits from both StaticWorkbench and StreamWorkbench."""
    stream_tool = StreamTool()

    async with StaticStreamWorkbench(tools=[stream_tool]) as workbench:
        # Test that it has regular workbench functionality
        tools = await workbench.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_stream_tool"

        # Test regular call_tool method
        result = await workbench.call_tool("test_stream_tool", {"count": 2})
        assert result.name == "test_stream_tool"
        assert result.is_error is False

        # Test streaming functionality exists
        assert hasattr(workbench, "call_tool_stream")
        results: list[StreamItem | StreamResult | ToolResult] = []
        async for result in workbench.call_tool_stream("test_stream_tool", {"count": 2}):
            results.append(result)  # type: ignore
        assert len(results) == 3  # 2 intermediate + 1 final
