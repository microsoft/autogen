"""Tests for HttpTool serialization and deserialization (Issue #7172)"""

import pytest
from autogen_core.tools import StaticStreamWorkbench
from autogen_ext.tools.http import HttpTool


@pytest.mark.asyncio
async def test_httptool_config_serialization():
    """Test HttpTool can be serialized and deserialized directly"""
    tool = HttpTool(
        name="test_tool",
        description="test description",
        scheme="https",
        host="httpbin.org",
        port=443,
        path="/get",
        method="GET",
        json_schema={"type": "object", "properties": {}},
        headers={"Authorization": "Bearer test", "Custom-Header": "value"},
    )
    
    # Serialize
    config = tool._to_config()
    
    # Deserialize
    restored_tool = HttpTool._from_config(config)
    
    # Verify all fields are preserved
    assert restored_tool.name == tool.name
    assert restored_tool.server_params.headers == tool.server_params.headers
    assert restored_tool.server_params.host == tool.server_params.host
    assert restored_tool.server_params.port == tool.server_params.port


@pytest.mark.asyncio
async def test_httptool_serialization_without_headers():
    """Test HttpTool serialization works when headers is None"""
    tool = HttpTool(
        name="test_tool_no_headers",
        description="test without headers",
        scheme="https",
        host="httpbin.org",
        port=443,
        path="/get",
        method="GET",
        json_schema={"type": "object", "properties": {}},
        # headers not provided (defaults to None)
    )
    
    # Serialize and deserialize
    config = tool._to_config()
    restored_tool = HttpTool._from_config(config)
    
    # Verify headers is None
    assert restored_tool.server_params.headers is None


@pytest.mark.asyncio
async def test_static_workbench_httptool_serialization():
    """Test StaticStreamWorkbench can save/load with HttpTool (Issue #7172)"""
    tool = HttpTool(
        name="base64_decode",
        description="base64 decode a value",
        scheme="https",
        host="httpbin.org",
        port=443,
        path="/base64/{value}",
        method="GET",
        json_schema={
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "The base64 value to decode"},
            },
            "required": ["value"],
        },
    )
    
    # Create workbench
    workbench = StaticStreamWorkbench(tools=[tool])
    
    # Serialize config
    config = workbench._to_config()
    
    # This should not raise validation error (was failing before fix)
    new_workbench = StaticStreamWorkbench._from_config(config)
    
    # Verify workbench works
    tools = await new_workbench.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "base64_decode"