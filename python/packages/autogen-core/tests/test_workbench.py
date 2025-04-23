from typing import Annotated

import pytest
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool, StaticWorkbench


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
        assert result_1.is_error is False

        # Call tool with error
        result_2 = await workbench.call_tool("test_tool_2", {"x": 5})
        assert result_2.name == "test_tool_2"
        assert result_2.result[0].type == "TextResultContent"
        assert result_2.result[0].content == "This is a test error"
        assert result_2.is_error is True

        # Save state.
        state = await workbench.save_state()
        assert state["type"] == "StaticWorkbenchState"
        assert "tools" in state
        assert len(state["tools"]) == 2

        # Dump config.
        config = workbench.dump_component()

    # Load the workbench from the config.
    async with StaticWorkbench.load_component(config) as workbench:
        # Load state.
        await workbench.load_state(state)

        # Verify that the tools are still available after loading the state.
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
        assert result_1.is_error is False

        # Call tool with error
        result_2 = await workbench.call_tool("test_tool_2", {"x": 5})
        assert result_2.name == "test_tool_2"
        assert result_2.result[0].type == "TextResultContent"
        assert result_2.result[0].content == "This is a test error"
        assert result_2.is_error is True
