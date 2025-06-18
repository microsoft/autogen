#!/usr/bin/env python3
"""
Test script for Workbench tool name and description overrides.
This script tests both StaticWorkbench and McpWorkbench implementations.
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path

# Add the autogen-core package to Python path
sys.path.insert(0, str(Path(__file__).parent / "python" / "packages" / "autogen-core" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "python" / "packages" / "autogen-ext" / "src"))

from typing import Annotated
from autogen_core.tools import FunctionTool, StaticWorkbench, ToolOverride
from autogen_core.code_executor import ImportFromModule


def test_static_workbench_overrides():
    """Test StaticWorkbench with tool overrides."""
    print("Testing StaticWorkbench with tool overrides...")
    
    def double_number(x: Annotated[int, "The number to double."]) -> int:
        return x * 2

    def add_numbers(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
        return a + b

    # Create tools
    double_tool = FunctionTool(
        double_number,
        name="double",
        description="Doubles a number",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    
    add_tool = FunctionTool(
        add_numbers,
        name="add",
        description="Adds two numbers",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    
    # Define overrides
    overrides = {
        "double": ToolOverride(name="multiply_by_two", description="Multiplies a number by 2"),
        "add": ToolOverride(description="Performs addition of two integers")
    }
    
    async def run_test():
        # Test with overrides
        async with StaticWorkbench(tools=[double_tool, add_tool], tool_overrides=overrides) as wb:
            tools = await wb.list_tools()
            
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
            
            # Test that names are overridden correctly
            assert tools[0]["name"] == "multiply_by_two", f"Expected 'multiply_by_two', got {tools[0]['name']}"
            assert tools[0]["description"] == "Multiplies a number by 2", f"Expected overridden description, got {tools[0]['description']}"
            assert tools[1]["name"] == "add", f"Expected 'add', got {tools[1]['name']}"
            assert tools[1]["description"] == "Performs addition of two integers", f"Expected overridden description, got {tools[1]['description']}"
            
            # Test calling tools with override names
            result1 = await wb.call_tool("multiply_by_two", {"x": 5})
            assert result1.result[0].content == "10", f"Expected '10', got {result1.result[0].content}"
            assert result1.name == "multiply_by_two", f"Expected return name 'multiply_by_two', got {result1.name}"
            
            result2 = await wb.call_tool("add", {"a": 3, "b": 7})
            assert result2.result[0].content == "10", f"Expected '10', got {result2.result[0].content}"
            assert result2.name == "add", f"Expected return name 'add', got {result2.name}"
            
            print("✓ StaticWorkbench override tests passed!")
            
        # Test without overrides
        async with StaticWorkbench(tools=[double_tool, add_tool]) as wb:
            tools = await wb.list_tools()
            assert tools[0]["name"] == "double", f"Expected 'double', got {tools[0]['name']}"
            assert tools[0]["description"] == "Doubles a number", f"Expected original description, got {tools[0]['description']}"
            print("✓ StaticWorkbench without overrides works correctly!")
            
        # Test serialization
        wb_with_overrides = StaticWorkbench(tools=[double_tool, add_tool], tool_overrides=overrides)
        config = wb_with_overrides.dump_component()
        print(f"✓ Serialization works: {config['component_config']['tool_overrides']}")
        
        # Test deserialization
        wb_from_config = StaticWorkbench.load_component(config)
        async with wb_from_config as wb:
            tools = await wb.list_tools()
            assert tools[0]["name"] == "multiply_by_two", f"Expected 'multiply_by_two' after deserialization, got {tools[0]['name']}"
            print("✓ Deserialization works correctly!")
    
    asyncio.run(run_test())


def test_mcp_workbench_overrides():
    """Test McpWorkbench with tool overrides."""
    print("\nTesting McpWorkbench with tool overrides...")
    
    # We'll use a mock approach since we don't have the full MCP infrastructure
    try:
        from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, ToolOverride as McpToolOverride
        
        overrides = {
            "fetch": McpToolOverride(name="web_fetch", description="Enhanced web fetching tool")
        }
        
        params = StdioServerParams(
            command="echo",  # Simple command that won't fail
            args=["test"],
            read_timeout_seconds=5,
        )
        
        # Test serialization/deserialization without actually running MCP
        workbench = McpWorkbench(server_params=params, tool_overrides=overrides)
        config = workbench.dump_component()
        
        print(f"✓ McpWorkbench serialization works: {config['component_config']['tool_overrides']}")
        
        # Test deserialization
        workbench_from_config = McpWorkbench.load_component(config)
        assert workbench_from_config._tool_overrides == overrides
        print("✓ McpWorkbench deserialization works correctly!")
        
    except ImportError as e:
        print(f"⚠ McpWorkbench test skipped due to missing dependencies: {e}")


if __name__ == "__main__":
    test_static_workbench_overrides()
    test_mcp_workbench_overrides()
    print("\n🎉 All tests passed!")