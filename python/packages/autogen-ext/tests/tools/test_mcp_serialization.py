import pytest
from autogen_ext.tools.mcp._base import _to_json_str
from autogen_ext.tools.mcp._stdio import StdioMcpToolAdapter
from mcp.types import TextContent, Tool


def test_to_json_str_no_escape_japanese() -> None:
    """Verify that Japanese text is not escaped in _to_json_str."""
    data = {"text": "日本語"}
    serialized = _to_json_str(data)

    # Check that the literal Japanese characters are in the string
    assert "日本語" in serialized
    # Check that the escaped unicode sequence is NOT in the string
    assert "\\u65e5\\u672c\\u8a9e" not in serialized


def test_mcp_tool_adapter_return_value_no_escape_japanese() -> None:
    """Verify that McpToolAdapter.return_value_as_string does not escape Japanese text."""
    # Mock parameters
    from autogen_ext.tools.mcp import StdioServerParams

    server_params = StdioServerParams(command="echo", args=["test"])
    tool = Tool(name="test_tool", description="A test tool", inputSchema={"type": "object", "properties": {}})

    adapter = StdioMcpToolAdapter(server_params=server_params, tool=tool)

    content = [TextContent(type="text", text="日本語")]
    serialized = adapter.return_value_as_string(content)

    # Check that the literal Japanese characters are in the string
    assert "日本語" in serialized
    # Check that the escaped unicode sequence is NOT in the string
    assert "\\u65e5\\u672c\\u8a9e" not in serialized
