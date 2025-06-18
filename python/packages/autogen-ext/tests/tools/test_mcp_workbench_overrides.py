import asyncio
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import CancellationToken
from autogen_core.tools import Workbench
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, ToolOverride
from mcp import Tool
from mcp.types import ListToolsResult


@pytest.fixture
def sample_mcp_tools() -> list[Tool]:
    """Create sample MCP tools for testing."""
    return [
        Tool(
            name="fetch",
            description="Fetches content from a URL",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        ),
        Tool(
            name="search",
            description="Searches for information",
            inputSchema={
                "type": "object", 
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
    ]


@pytest.fixture
def mock_mcp_actor():
    """Mock MCP session actor."""
    actor = AsyncMock()
    return actor


@pytest.fixture
def sample_server_params() -> StdioServerParams:
    """Sample server parameters for testing."""
    return StdioServerParams(command="echo", args=["test"])


@pytest.mark.asyncio
async def test_mcp_workbench_with_tool_overrides(
    sample_mcp_tools: list[Tool], 
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams
) -> None:
    """Test McpWorkbench with tool name and description overrides."""
    
    # Define tool overrides
    overrides = {
        "fetch": ToolOverride(name="web_fetch", description="Enhanced web fetching tool"),
        "search": ToolOverride(description="Advanced search functionality")  # Only description override
    }
    
    # Create workbench with overrides
    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    workbench._actor = mock_mcp_actor
    
    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    mock_mcp_actor.call.return_value = list_tools_result
    
    try:
        # List tools and verify overrides are applied
        tools = await workbench.list_tools()
        assert len(tools) == 2
        
        # Check first tool has name and description overridden
        assert tools[0]["name"] == "web_fetch"
        assert tools[0]["description"] == "Enhanced web fetching tool"
        assert tools[0]["parameters"]["properties"]["url"]["type"] == "string"
        
        # Check second tool has only description overridden
        assert tools[1]["name"] == "search"  # Original name
        assert tools[1]["description"] == "Advanced search functionality"  # Overridden description
        assert tools[1]["parameters"]["properties"]["query"]["type"] == "string"
        
        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("list_tools", None)
        
    finally:
        workbench._actor = None


@pytest.mark.asyncio
async def test_mcp_workbench_call_tool_with_overrides(
    sample_mcp_tools: list[Tool],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams
) -> None:
    """Test calling tools with override names maps back to original names."""
    
    overrides = {
        "fetch": ToolOverride(name="web_fetch", description="Enhanced web fetching tool")
    }
    
    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    workbench._actor = mock_mcp_actor
    
    # Mock successful tool call response
    from mcp.types import CallToolResult, TextContent
    mock_result = CallToolResult(
        content=[TextContent(text="Mock response", type="text")],
        isError=False
    )
    
    # Setup mock to return different results for different calls
    async def mock_call(method, args):
        if method == "list_tools":
            return ListToolsResult(tools=sample_mcp_tools)
        elif method == "call_tool":
            return mock_result
        else:
            raise ValueError(f"Unexpected method: {method}")
    
    mock_mcp_actor.call.side_effect = mock_call
    
    try:
        # Call tool using override name
        result = await workbench.call_tool("web_fetch", {"url": "https://example.com"})
        
        # Verify the result
        assert result.name == "web_fetch"  # Should return the override name
        assert result.result[0].content == "Mock response"
        assert result.is_error is False
        
        # Verify the actor was called with the original tool name
        call_args = mock_mcp_actor.call.call_args_list[-1]
        assert call_args[0][0] == "call_tool"
        assert call_args[0][1]["name"] == "fetch"  # Original name should be used
        assert call_args[0][1]["kargs"] == {"url": "https://example.com"}
        
    finally:
        workbench._actor = None


@pytest.mark.asyncio
async def test_mcp_workbench_without_overrides(
    sample_mcp_tools: list[Tool],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams
) -> None:
    """Test McpWorkbench without overrides (original behavior)."""
    
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor
    
    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    mock_mcp_actor.call.return_value = list_tools_result
    
    try:
        tools = await workbench.list_tools()
        assert len(tools) == 2
        
        # Verify original names and descriptions are preserved
        assert tools[0]["name"] == "fetch"
        assert tools[0]["description"] == "Fetches content from a URL"
        assert tools[1]["name"] == "search"
        assert tools[1]["description"] == "Searches for information"
        
    finally:
        workbench._actor = None


@pytest.mark.asyncio
async def test_mcp_workbench_serialization_with_overrides(
    sample_server_params: StdioServerParams
) -> None:
    """Test that McpWorkbench can be serialized and deserialized with overrides."""
    
    overrides = {
        "fetch": ToolOverride(name="web_fetch", description="Enhanced web fetching tool")
    }
    
    # Create workbench with overrides
    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    
    # Save configuration
    config = workbench.dump_component()
    assert "tool_overrides" in config["component_config"]
    assert "fetch" in config["component_config"]["tool_overrides"]
    assert config["component_config"]["tool_overrides"]["fetch"]["name"] == "web_fetch"
    assert config["component_config"]["tool_overrides"]["fetch"]["description"] == "Enhanced web fetching tool"
    
    # Load workbench from configuration
    new_workbench = McpWorkbench.load_component(config)
    assert len(new_workbench._tool_overrides) == 1
    assert new_workbench._tool_overrides["fetch"].name == "web_fetch"
    assert new_workbench._tool_overrides["fetch"].description == "Enhanced web fetching tool"


@pytest.mark.asyncio
async def test_mcp_workbench_partial_overrides(
    sample_mcp_tools: list[Tool],
    mock_mcp_actor: AsyncMock, 
    sample_server_params: StdioServerParams
) -> None:
    """Test McpWorkbench with partial overrides (name only, description only)."""
    
    overrides = {
        "fetch": ToolOverride(name="web_fetch"),  # Only name override
        "search": ToolOverride(description="Advanced search")  # Only description override
    }
    
    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    workbench._actor = mock_mcp_actor
    
    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    mock_mcp_actor.call.return_value = list_tools_result
    
    try:
        tools = await workbench.list_tools()
        
        # fetch: name overridden, description unchanged
        assert tools[0]["name"] == "web_fetch"
        assert tools[0]["description"] == "Fetches content from a URL"  # Original description
        
        # search: name unchanged, description overridden
        assert tools[1]["name"] == "search"  # Original name
        assert tools[1]["description"] == "Advanced search"  # Overridden description
        
    finally:
        workbench._actor = None


def test_mcp_tool_override_model() -> None:
    """Test ToolOverride model functionality for MCP."""
    
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


@pytest.mark.asyncio
async def test_mcp_workbench_override_name_to_original_mapping(
    sample_server_params: StdioServerParams
) -> None:
    """Test that the reverse mapping from override names to original names works correctly."""
    
    overrides = {
        "original1": ToolOverride(name="override1"),
        "original2": ToolOverride(name="override2"),
        "original3": ToolOverride(description="only description override")  # No name override
    }
    
    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    
    # Check reverse mapping is built correctly
    assert workbench._override_name_to_original["override1"] == "original1"
    assert workbench._override_name_to_original["override2"] == "original2"
    assert "original3" not in workbench._override_name_to_original  # No name override
    assert len(workbench._override_name_to_original) == 2


if __name__ == "__main__":
    # Run tests individually since we can't use pytest directly
    import sys
    import traceback
    
    async def run_all_tests():
        try:
            # Create fixtures
            sample_tools = [
                Tool(
                    name="fetch",
                    description="Fetches content from a URL",
                    inputSchema={
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                ),
                Tool(
                    name="search", 
                    description="Searches for information",
                    inputSchema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                ),
            ]
            mock_actor = AsyncMock()
            server_params = StdioServerParams(command="echo", args=["test"])
            
            await test_mcp_workbench_with_tool_overrides(sample_tools, mock_actor, server_params)
            await test_mcp_workbench_call_tool_with_overrides(sample_tools, mock_actor, server_params)
            await test_mcp_workbench_without_overrides(sample_tools, mock_actor, server_params)
            await test_mcp_workbench_serialization_with_overrides(server_params)
            await test_mcp_workbench_partial_overrides(sample_tools, mock_actor, server_params)
            test_mcp_tool_override_model()
            await test_mcp_workbench_override_name_to_original_mapping(server_params)
            
            print("All McpWorkbench override tests passed!")
            
        except Exception as e:
            print(f"Test failed: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(run_all_tests())