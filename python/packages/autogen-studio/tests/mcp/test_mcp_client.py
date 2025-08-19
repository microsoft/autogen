#!/usr/bin/env python3
"""Test the MCP client implementation"""

import asyncio
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from mcp.types import (
    ListToolsResult, 
    Tool, 
    CallToolResult,
    TextContent,
    ListResourcesResult,
    Resource,
    ReadResourceResult,
    TextResourceContents,
    ListPromptsResult,
    Prompt,
    GetPromptResult,
    PromptMessage,
    InitializeResult,
    ServerCapabilities,
    Implementation
)

from autogenstudio.mcp.client import MCPClient, MCPEventHandler
from autogenstudio.mcp.utils import McpOperationError


class MockEventHandler(MCPEventHandler):
    """Mock event handler for testing"""
    
    def __init__(self):
        self.events = []
    
    async def on_initialized(self, session_id: str, capabilities: Any) -> None:
        self.events.append(("initialized", session_id, capabilities))
    
    async def on_operation_result(self, operation: str, data: dict) -> None:
        self.events.append(("operation_result", operation, data))
    
    async def on_operation_error(self, operation: str, error: str) -> None:
        self.events.append(("operation_error", operation, error))
    
    async def on_mcp_activity(self, activity_type: str, message: str, details: dict) -> None:
        self.events.append(("mcp_activity", activity_type, message, details))
    
    async def on_elicitation_request(self, request_id: str, message: str, requested_schema: Any) -> None:
        self.events.append(("elicitation_request", request_id, message, requested_schema))


class TestMCPClient:
    """Test the MCPClient class"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock MCP session"""
        session = AsyncMock()
        
        # Mock initialization
        session.initialize.return_value = InitializeResult(
            protocolVersion="2024-11-05",
            capabilities=ServerCapabilities(),
            serverInfo=Implementation(name="test-server", version="1.0.0")
        )
        
        # Mock tools
        session.list_tools.return_value = ListToolsResult(
            tools=[
                Tool(
                    name="test_tool",
                    description="A test tool",
                    inputSchema={
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"]
                    }
                )
            ]
        )
        
        # Mock tool call
        session.call_tool.return_value = CallToolResult(
            content=[TextContent(type="text", text="Tool executed successfully")],
            isError=False
        )
        
        # Mock resources
        from pydantic import HttpUrl
        test_uri = HttpUrl("https://example.com/test.txt")
        session.list_resources.return_value = ListResourcesResult(
            resources=[
                Resource(
                    uri=test_uri,
                    name="test.txt",
                    description="A test resource",
                    mimeType="text/plain"
                )
            ]
        )
        
        session.read_resource.return_value = ReadResourceResult(
            contents=[TextResourceContents(
                uri=test_uri,
                text="This is test content",
                mimeType="text/plain"
            )]
        )
        
        # Mock prompts
        session.list_prompts.return_value = ListPromptsResult(
            prompts=[
                Prompt(
                    name="test_prompt",
                    description="A test prompt"
                )
            ]
        )
        
        session.get_prompt.return_value = GetPromptResult(
            description="Test prompt result",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text="Test prompt content")
                )
            ]
        )
        
        return session
    
    @pytest.fixture
    def mock_event_handler(self):
        """Create a mock event handler"""
        return MockEventHandler()
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_session, mock_event_handler):
        """Test MCPClient initialization"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        
        assert client.session == mock_session
        assert client.session_id == "test-session"
        assert client.event_handler == mock_event_handler
        assert not client._initialized
        assert client._capabilities is None
    
    @pytest.mark.asyncio
    async def test_client_initialize(self, mock_session, mock_event_handler):
        """Test MCPClient.initialize()"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        
        await client.initialize()
        
        # Verify session.initialize was called
        mock_session.initialize.assert_called_once()
        
        # Verify client state
        assert client._initialized
        assert client.capabilities is not None
        
        # Verify event handler was called
        events = [e for e in mock_event_handler.events if e[0] == "initialized"]
        assert len(events) == 1
        assert events[0][1] == "test-session"
    
    @pytest.mark.asyncio
    async def test_list_tools_operation(self, mock_session, mock_event_handler):
        """Test list_tools operation"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        await client.initialize()
        
        # Test list_tools operation
        operation = {"operation": "list_tools"}
        await client.handle_operation(operation)
        
        # Verify session method was called
        mock_session.list_tools.assert_called_once()
        
        # Verify result event was fired
        result_events = [e for e in mock_event_handler.events if e[0] == "operation_result"]
        assert len(result_events) == 1
        assert result_events[0][1] == "list_tools"
        assert "tools" in result_events[0][2]
    
    @pytest.mark.asyncio
    async def test_call_tool_operation(self, mock_session, mock_event_handler):
        """Test call_tool operation"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        await client.initialize()
        
        # Test call_tool operation
        operation = {
            "operation": "call_tool",
            "tool_name": "test_tool",
            "arguments": {"message": "test"}
        }
        await client.handle_operation(operation)
        
        # Verify session method was called
        mock_session.call_tool.assert_called_once_with("test_tool", {"message": "test"})
        
        # Verify result event was fired
        result_events = [e for e in mock_event_handler.events if e[0] == "operation_result"]
        assert len(result_events) == 1
        assert result_events[0][1] == "call_tool"
        assert result_events[0][2]["tool_name"] == "test_tool"
    
    @pytest.mark.asyncio
    async def test_call_tool_missing_name(self, mock_session, mock_event_handler):
        """Test call_tool operation with missing tool name"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        await client.initialize()
        
        # Test call_tool operation without tool_name
        operation = {
            "operation": "call_tool",
            "arguments": {"message": "test"}
        }
        await client.handle_operation(operation)
        
        # Verify error event was fired
        error_events = [e for e in mock_event_handler.events if e[0] == "operation_error"]
        assert len(error_events) == 1
        assert error_events[0][1] == "call_tool"
        assert "Tool name is required" in error_events[0][2]
    
    @pytest.mark.asyncio
    async def test_unknown_operation(self, mock_session, mock_event_handler):
        """Test unknown operation handling"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        await client.initialize()
        
        # Test unknown operation
        operation = {"operation": "unknown_op"}
        await client.handle_operation(operation)
        
        # Verify error event was fired
        error_events = [e for e in mock_event_handler.events if e[0] == "operation_error"]
        assert len(error_events) == 1
        assert error_events[0][1] == "unknown_op"
        assert "Unknown operation" in error_events[0][2]
    
    @pytest.mark.asyncio
    async def test_operation_exception_handling(self, mock_session, mock_event_handler):
        """Test operation exception handling"""
        client = MCPClient(mock_session, "test-session", mock_event_handler)
        await client.initialize()
        
        # Mock session to raise exception
        mock_session.list_tools.side_effect = Exception("Test error")
        
        # Test list_tools operation
        operation = {"operation": "list_tools"}
        await client.handle_operation(operation)
        
        # Verify error event was fired
        error_events = [e for e in mock_event_handler.events if e[0] == "operation_error"]
        assert len(error_events) == 1
        assert error_events[0][1] == "list_tools"
        assert "Test error" in error_events[0][2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
