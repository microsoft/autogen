from typing import Annotated, Dict

import pytest
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool, StaticWorkbench, ToolOverride, Workbench


@pytest.mark.asyncio
async def test_static_workbench_with_tool_overrides() -> None:
    """Test StaticWorkbench with tool name and description overrides."""

    def test_tool_func_1(x: Annotated[int, "The number to double."]) -> int:
        return x * 2

    def test_tool_func_2(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
        return a + b

    test_tool_1 = FunctionTool(
        test_tool_func_1,
        name="double",
        description="A test tool that doubles a number.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    test_tool_2 = FunctionTool(
        test_tool_func_2,
        name="add",
        description="A test tool that adds two numbers.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    # Define tool overrides
    overrides: Dict[str, ToolOverride] = {
        "double": ToolOverride(name="multiply_by_two", description="Multiplies a number by 2"),
        "add": ToolOverride(description="Performs addition of two integers"),  # Only override description
    }

    # Create a StaticWorkbench instance with tool overrides
    async with StaticWorkbench(tools=[test_tool_1, test_tool_2], tool_overrides=overrides) as workbench:
        # List tools and verify overrides are applied
        tools = await workbench.list_tools()
        assert len(tools) == 2

        # Check first tool has name and description overridden
        assert tools[0]["name"] == "multiply_by_two"
        assert tools[0].get("description") == "Multiplies a number by 2"
        assert tools[0].get("parameters") == {
            "type": "object",
            "properties": {"x": {"type": "integer", "title": "X", "description": "The number to double."}},
            "required": ["x"],
            "additionalProperties": False,
        }

        # Check second tool has only description overridden
        assert tools[1]["name"] == "add"  # Original name
        assert tools[1].get("description") == "Performs addition of two integers"  # Overridden description
        assert tools[1].get("parameters") == {
            "type": "object",
            "properties": {
                "a": {"type": "integer", "title": "A", "description": "First number"},
                "b": {"type": "integer", "title": "B", "description": "Second number"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        }

        # Call tools using override names
        result_1 = await workbench.call_tool("multiply_by_two", {"x": 5})
        assert result_1.name == "multiply_by_two"  # Should return the override name
        assert result_1.result[0].type == "TextResultContent"
        assert result_1.result[0].content == "10"
        assert result_1.to_text() == "10"
        assert result_1.is_error is False

        # Call tool using original name (should still work for description-only override)
        result_2 = await workbench.call_tool("add", {"a": 3, "b": 7})
        assert result_2.name == "add"
        assert result_2.result[0].type == "TextResultContent"
        assert result_2.result[0].content == "10"
        assert result_2.to_text() == "10"
        assert result_2.is_error is False

        # Test calling non-existent tool
        result_3 = await workbench.call_tool("nonexistent", {"x": 5})
        assert result_3.name == "nonexistent"
        assert result_3.is_error is True
        assert result_3.result[0].type == "TextResultContent"
        assert "Tool nonexistent not found" in result_3.result[0].content


@pytest.mark.asyncio
async def test_static_workbench_without_overrides() -> None:
    """Test StaticWorkbench without overrides (original behavior)."""

    def test_tool_func(x: Annotated[int, "The number to double."]) -> int:
        return x * 2

    test_tool = FunctionTool(
        test_tool_func,
        name="double",
        description="A test tool that doubles a number.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    # Create workbench without overrides
    async with StaticWorkbench(tools=[test_tool]) as workbench:
        tools = await workbench.list_tools()
        assert len(tools) == 1
        assert tools[0].get("name") == "double"
        assert tools[0].get("description") == "A test tool that doubles a number."


@pytest.mark.asyncio
async def test_static_workbench_serialization_with_overrides() -> None:
    """Test that StaticWorkbench can be serialized and deserialized with overrides."""

    def test_tool_func(x: Annotated[int, "The number to double."]) -> int:
        return x * 2

    test_tool = FunctionTool(
        test_tool_func,
        name="double",
        description="A test tool that doubles a number.",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    overrides: Dict[str, ToolOverride] = {
        "double": ToolOverride(name="multiply_by_two", description="Multiplies a number by 2")
    }

    # Create workbench with overrides
    workbench = StaticWorkbench(tools=[test_tool], tool_overrides=overrides)

    # Save configuration
    config = workbench.dump_component()
    assert "tool_overrides" in config.config

    # Load workbench from configuration
    async with Workbench.load_component(config) as new_workbench:
        tools = await new_workbench.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "multiply_by_two"
        assert tools[0].get("description") == "Multiplies a number by 2"

        # Test calling tool with override name
        result = await new_workbench.call_tool("multiply_by_two", {"x": 5})
        assert result.name == "multiply_by_two"
        assert result.result[0].content == "10"
        assert result.is_error is False


@pytest.mark.asyncio
async def test_static_workbench_partial_overrides() -> None:
    """Test StaticWorkbench with partial overrides (name only, description only)."""

    def tool1_func(x: Annotated[int, "Number"]) -> int:
        return x

    def tool2_func(x: Annotated[int, "Number"]) -> int:
        return x

    tool1 = FunctionTool(
        tool1_func,
        name="tool1",
        description="Original description 1",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    tool2 = FunctionTool(
        tool2_func,
        name="tool2",
        description="Original description 2",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    overrides: Dict[str, ToolOverride] = {
        "tool1": ToolOverride(name="renamed_tool1"),  # Only name override
        "tool2": ToolOverride(description="New description 2"),  # Only description override
    }

    async with StaticWorkbench(tools=[tool1, tool2], tool_overrides=overrides) as workbench:
        tools = await workbench.list_tools()

        # tool1: name overridden, description unchanged
        assert tools[0].get("name") == "renamed_tool1"
        assert tools[0].get("description") == "Original description 1"

        # tool2: name unchanged, description overridden
        assert tools[1].get("name") == "tool2"
        assert tools[1].get("description") == "New description 2"

        # Test calling with override name
        result1 = await workbench.call_tool("renamed_tool1", {"x": 42})
        assert result1.name == "renamed_tool1"
        assert result1.result[0].content == "42"

        # Test calling with original name
        result2 = await workbench.call_tool("tool2", {"x": 42})
        assert result2.name == "tool2"
        assert result2.result[0].content == "42"


def test_tool_override_model() -> None:
    """Test ToolOverride model functionality."""

    # Test with both fields
    override1 = ToolOverride(name="new_name", description="new_desc")
    assert override1.name == "new_name"
    assert override1.description == "new_desc"

    # Test with only name
    override2 = ToolOverride(name="new_name")
    assert override2.name == "new_name"
    assert override2.description is None

    # Test with only description
    override3 = ToolOverride(description="new_desc")
    assert override3.name is None
    assert override3.description == "new_desc"

    # Test empty
    override4 = ToolOverride()
    assert override4.name is None
    assert override4.description is None


def test_static_workbench_conflict_detection() -> None:
    """Test that StaticWorkbench detects conflicts in tool override names."""

    def test_tool_func_1(x: Annotated[int, "Number"]) -> int:
        return x

    def test_tool_func_2(x: Annotated[int, "Number"]) -> int:
        return x

    def test_tool_func_3(x: Annotated[int, "Number"]) -> int:
        return x

    tool1 = FunctionTool(
        test_tool_func_1,
        name="tool1",
        description="Tool 1",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    tool2 = FunctionTool(
        test_tool_func_2,
        name="tool2",
        description="Tool 2",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    tool3 = FunctionTool(
        test_tool_func_3,
        name="tool3",
        description="Tool 3",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )

    # Test 1: Valid overrides - should work
    overrides_valid: Dict[str, ToolOverride] = {
        "tool1": ToolOverride(name="renamed_tool1"),
        "tool2": ToolOverride(name="renamed_tool2"),
    }
    workbench_valid = StaticWorkbench(tools=[tool1, tool2, tool3], tool_overrides=overrides_valid)
    assert "renamed_tool1" in workbench_valid._override_name_to_original  # type: ignore[reportPrivateUsage]
    assert "renamed_tool2" in workbench_valid._override_name_to_original  # type: ignore[reportPrivateUsage]

    # Test 2: Conflict with existing tool name - should fail
    overrides_conflict: Dict[str, ToolOverride] = {
        "tool1": ToolOverride(name="tool2")  # tool2 already exists
    }
    with pytest.raises(ValueError):
        StaticWorkbench(tools=[tool1, tool2, tool3], tool_overrides=overrides_conflict)

    # Test 3: Duplicate override names - should fail
    overrides_duplicate: Dict[str, ToolOverride] = {
        "tool1": ToolOverride(name="same_name"),
        "tool2": ToolOverride(name="same_name"),  # Duplicate
    }
    with pytest.raises(ValueError):
        StaticWorkbench(tools=[tool1, tool2, tool3], tool_overrides=overrides_duplicate)

    # Test 4: Self-renaming - should work but not add to reverse mapping
    overrides_self: Dict[str, ToolOverride] = {
        "tool1": ToolOverride(name="tool1")  # Renaming to itself
    }
    workbench_self = StaticWorkbench(tools=[tool1, tool2, tool3], tool_overrides=overrides_self)
    assert "tool1" not in workbench_self._override_name_to_original  # type: ignore[reportPrivateUsage]
