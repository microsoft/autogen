#!/usr/bin/env python3
"""
Example demonstrating tool name and description override functionality 
for both StaticWorkbench and McpWorkbench.

This example shows how to:
1. Override tool names and descriptions in StaticWorkbench
2. Override tool names and descriptions in McpWorkbench
3. Handle serialization/deserialization with overrides
4. Use different types of overrides (name only, description only, both)
"""

import asyncio
from typing import Annotated

from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool, StaticWorkbench, ToolOverride
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, ToolOverride as McpToolOverride


async def static_workbench_example():
    """Example using StaticWorkbench with tool overrides."""
    print("=== StaticWorkbench Override Example ===")
    
    # Define some example tools
    def multiply_numbers(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
        """Multiply two numbers together."""
        return a * b
    
    def format_text(text: Annotated[str, "Text to format"], style: Annotated[str, "Format style"]) -> str:
        """Format text with a given style."""
        if style == "upper":
            return text.upper()
        elif style == "lower":
            return text.lower()
        else:
            return text
    
    # Create tools
    multiply_tool = FunctionTool(
        multiply_numbers,
        name="multiply",
        description="Multiplies two numbers",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    
    format_tool = FunctionTool(
        format_text,
        name="format",
        description="Formats text in different styles",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    
    # Define tool overrides
    tool_overrides = {
        "multiply": ToolOverride(
            name="calculate_product", 
            description="Advanced multiplication calculator for two integers"
        ),
        "format": ToolOverride(
            description="Enhanced text formatting tool with multiple style options"
            # Note: No name override, so original name "format" will be used
        )
    }
    
    # Create workbench with overrides
    async with StaticWorkbench(tools=[multiply_tool, format_tool], tool_overrides=tool_overrides) as workbench:
        # List tools to see overrides applied
        tools = await workbench.list_tools()
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        print("\nTesting tool calls with override names:")
        
        # Call tool using override name
        result1 = await workbench.call_tool("calculate_product", {"a": 6, "b": 7})
        print(f"calculate_product(6, 7) = {result1.result[0].content}")
        
        # Call tool using original name (since only description was overridden)
        result2 = await workbench.call_tool("format", {"text": "Hello World", "style": "upper"})
        print(f"format('Hello World', 'upper') = {result2.result[0].content}")
        
        # Demonstrate serialization with overrides
        print("\nTesting serialization/deserialization:")
        config = workbench.dump_component()
        print("✓ Workbench configuration saved successfully")
    
    # Load workbench from configuration
    async with StaticWorkbench.load_component(config) as restored_workbench:
        tools = await restored_workbench.list_tools()
        print(f"✓ Restored workbench has {len(tools)} tools with overrides preserved")
        
        # Verify overrides still work
        result = await restored_workbench.call_tool("calculate_product", {"a": 3, "b": 4})
        print(f"✓ Restored calculate_product(3, 4) = {result.result[0].content}")


async def mcp_workbench_example():
    """Example using McpWorkbench with tool overrides (simulated)."""
    print("\n=== McpWorkbench Override Example ===")
    
    # Define tool overrides for MCP server tools
    tool_overrides = {
        "fetch": McpToolOverride(
            name="web_scraper",
            description="Advanced web content fetching and scraping tool"
        ),
        "search": McpToolOverride(
            description="Intelligent search functionality with enhanced algorithms"
            # Note: No name override, so original name "search" will be used
        )
    }
    
    # Create MCP workbench with overrides
    server_params = StdioServerParams(
        command="echo",  # Simple command for demonstration
        args=["MCP server simulation"],
        read_timeout_seconds=5,
    )
    
    workbench = McpWorkbench(server_params=server_params, tool_overrides=tool_overrides)
    
    # Demonstrate serialization (without actually starting the server)
    print("Testing MCP workbench serialization with overrides:")
    config = workbench.dump_component()
    print("✓ MCP workbench configuration saved successfully")
    
    # Load workbench from configuration
    restored_workbench = McpWorkbench.load_component(config)
    print(f"✓ Restored MCP workbench with {len(restored_workbench._tool_overrides)} tool overrides")
    
    # Show override mapping
    print("Override name mappings:")
    for override_name, original_name in restored_workbench._override_name_to_original.items():
        print(f"  {override_name} -> {original_name}")
    
    print("Note: Full MCP functionality requires an actual MCP server to be running.")


def conflict_detection_example():
    """Example demonstrating conflict detection in tool overrides."""
    print("\n=== Conflict Detection Example ===")
    
    def tool1_func(x: Annotated[int, "Input"]) -> int:
        return x
    
    def tool2_func(x: Annotated[int, "Input"]) -> int:
        return x
    
    tool1 = FunctionTool(
        tool1_func,
        name="tool1",
        description="Tool 1",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    
    tool2 = FunctionTool(
        tool2_func,
        name="tool2",
        description="Tool 2",
        global_imports=[ImportFromModule(module="typing_extensions", imports=["Annotated"])],
    )
    
    print("Testing conflict detection:")
    
    # Example 1: Valid overrides
    try:
        valid_overrides = {
            "tool1": ToolOverride(name="renamed_tool1"),
            "tool2": ToolOverride(name="renamed_tool2")
        }
        workbench = StaticWorkbench(tools=[tool1, tool2], tool_overrides=valid_overrides)
        print("✓ Valid overrides accepted")
    except ValueError as e:
        print(f"✗ Unexpected error: {e}")
    
    # Example 2: Conflict with existing tool name
    try:
        conflicting_overrides = {
            "tool1": ToolOverride(name="tool2")  # tool2 already exists!
        }
        workbench = StaticWorkbench(tools=[tool1, tool2], tool_overrides=conflicting_overrides)
        print("✗ Should have detected conflict!")
    except ValueError as e:
        print(f"✓ Detected name conflict: {e}")
    
    # Example 3: Duplicate override names
    try:
        duplicate_overrides = {
            "tool1": ToolOverride(name="same_name"),
            "tool2": ToolOverride(name="same_name")  # Duplicate!
        }
        workbench = StaticWorkbench(tools=[tool1, tool2], tool_overrides=duplicate_overrides)
        print("✗ Should have detected duplicate names!")
    except ValueError as e:
        print(f"✓ Detected duplicate override names: {e}")


async def main():
    """Run all examples."""
    await static_workbench_example()
    await mcp_workbench_example()
    conflict_detection_example()
    
    print("\n🎉 All examples completed successfully!")
    print("\nKey Features Demonstrated:")
    print("• Tool name and description overrides")
    print("• Partial overrides (name only or description only)")  
    print("• Serialization/deserialization with overrides")
    print("• Conflict detection and validation")
    print("• Reverse mapping for tool calls")


if __name__ == "__main__":
    asyncio.run(main())