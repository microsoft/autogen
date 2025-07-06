from unittest.mock import AsyncMock

import pytest
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
    sample_mcp_tools: list[Tool], mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams
) -> None:
    """Test McpWorkbench with tool name and description overrides."""

    # Define tool overrides
    overrides = {
        "fetch": ToolOverride(name="web_fetch", description="Enhanced web fetching tool"),
        "search": ToolOverride(description="Advanced search functionality"),  # Only description override
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
        assert tools[0].get("name") == "web_fetch"
        assert tools[0].get("description") == "Enhanced web fetching tool"

        # Check second tool has only description overridden
        assert tools[1].get("name") == "search"  # Original name
        assert tools[1].get("description") == "Advanced search functionality"  # Overridden description

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("list_tools", None)

    finally:
        workbench._actor = None


@pytest.mark.asyncio
async def test_mcp_workbench_call_tool_with_overrides(
    sample_mcp_tools: list[Tool], mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams
) -> None:
    """Test calling tools with override names maps back to original names."""

    overrides = {"fetch": ToolOverride(name="web_fetch", description="Enhanced web fetching tool")}

    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    workbench._actor = mock_mcp_actor

    # Mock successful tool call response
    from mcp.types import CallToolResult, TextContent

    mock_result = CallToolResult(content=[TextContent(text="Mock response", type="text")], isError=False)

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
    sample_mcp_tools: list[Tool], mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams
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
        assert tools[0].get("name") == "fetch"
        assert tools[0].get("description") == "Fetches content from a URL"
        assert tools[1].get("name") == "search"
        assert tools[1].get("description") == "Searches for information"

    finally:
        workbench._actor = None


@pytest.mark.asyncio
async def test_mcp_workbench_serialization_with_overrides(sample_server_params: StdioServerParams) -> None:
    """Test that McpWorkbench can be serialized and deserialized with overrides."""

    overrides = {"fetch": ToolOverride(name="web_fetch", description="Enhanced web fetching tool")}

    # Create workbench with overrides
    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)

    # Save configuration
    config = workbench.dump_component()
    assert "tool_overrides" in config.config
    assert "fetch" in config.config["tool_overrides"]
    assert config.config["tool_overrides"]["fetch"]["name"] == "web_fetch"
    assert config.config["tool_overrides"]["fetch"]["description"] == "Enhanced web fetching tool"

    # Load workbench from configuration
    new_workbench = McpWorkbench.load_component(config)
    assert len(new_workbench._tool_overrides) == 1
    assert new_workbench._tool_overrides["fetch"].name == "web_fetch"
    assert new_workbench._tool_overrides["fetch"].description == "Enhanced web fetching tool"


@pytest.mark.asyncio
async def test_mcp_workbench_partial_overrides(
    sample_mcp_tools: list[Tool], mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams
) -> None:
    """Test McpWorkbench with partial overrides (name only, description only)."""

    overrides = {
        "fetch": ToolOverride(name="web_fetch"),  # Only name override
        "search": ToolOverride(description="Advanced search"),  # Only description override
    }

    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)
    workbench._actor = mock_mcp_actor

    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    mock_mcp_actor.call.return_value = list_tools_result

    try:
        tools = await workbench.list_tools()

        # fetch: name overridden, description unchanged
        assert tools[0].get("name") == "web_fetch"
        assert tools[0].get("description") == "Fetches content from a URL"  # Original description

        # search: name unchanged, description overridden
        assert tools[1].get("name") == "search"  # Original name
        assert tools[1].get("description") == "Advanced search"  # Overridden description

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
async def test_mcp_workbench_override_name_to_original_mapping(sample_server_params: StdioServerParams) -> None:
    """Test that the reverse mapping from override names to original names works correctly."""

    overrides = {
        "original1": ToolOverride(name="override1"),
        "original2": ToolOverride(name="override2"),
        "original3": ToolOverride(description="only description override"),  # No name override
    }

    workbench = McpWorkbench(server_params=sample_server_params, tool_overrides=overrides)

    # Check reverse mapping is built correctly
    assert workbench._override_name_to_original["override1"] == "original1"
    assert workbench._override_name_to_original["override2"] == "original2"
    assert "original3" not in workbench._override_name_to_original  # No name override
    assert len(workbench._override_name_to_original) == 2


def test_mcp_workbench_conflict_detection() -> None:
    """Test that McpWorkbench detects conflicts in tool override names."""

    server_params = StdioServerParams(command="echo", args=["test"])

    # Test 1: Valid overrides - should work
    overrides_valid = {"fetch": ToolOverride(name="web_fetch"), "search": ToolOverride(name="advanced_search")}
    workbench_valid = McpWorkbench(server_params=server_params, tool_overrides=overrides_valid)
    assert workbench_valid._override_name_to_original["web_fetch"] == "fetch"
    assert workbench_valid._override_name_to_original["advanced_search"] == "search"

    # Test 2: Duplicate override names - should fail
    overrides_duplicate = {
        "fetch": ToolOverride(name="same_name"),
        "search": ToolOverride(name="same_name"),  # Duplicate
    }
    with pytest.raises(ValueError):
        McpWorkbench(server_params=server_params, tool_overrides=overrides_duplicate)
