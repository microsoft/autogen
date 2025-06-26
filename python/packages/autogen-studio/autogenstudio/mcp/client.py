"""
MCP Client Implementation

This client implementation follows a "session-per-operation" pattern to avoid 
task boundary issues with async context managers. Each MCP operation:

1. Creates a new connection/session
2. Executes the operation within the same async context
3. Automatically cleans up the connection when done

This prevents the "Attempted to exit cancel scope in a different task" error
that occurs when trying to share MCP sessions across HTTP request boundaries
or different async task groups.

Key changes from persistent connection approach:
- No persistent state (exit_stack, session, initialize_result)
- Each operation is self-contained
- Proper async context manager usage within same task
- Automatic cleanup without cross-task issues
"""

from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import timedelta
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from loguru import logger

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool, Resource, Prompt, CallToolResult, GetPromptResult, ReadResourceResult, InitializeResult, ServerCapabilities
from pydantic import AnyUrl

# Autogen imports (keeping compatibility with your current types)
from autogen_ext.tools.mcp._config import McpServerParams, StdioServerParams, SseServerParams, StreamableHttpServerParams
from autogen_core import CancellationToken


class McpConnectionError(Exception):
    """Raised when MCP connection fails"""
    pass


class McpOperationError(Exception):
    """Raised when MCP operation fails"""
    pass

 
class McpClient:
    """Direct MCP client that creates short-lived connections per operation"""
    
    def __init__(self):
        # Remove persistent state - each operation will create its own session
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # No cleanup needed since we don't maintain persistent connections
        pass
    
    async def _execute_with_session(self, server_params: McpServerParams, operation):
        """Execute an operation with a session, managing the session lifecycle properly"""
        if isinstance(server_params, StdioServerParams):
            return await self._execute_with_stdio(server_params, operation)
        elif isinstance(server_params, SseServerParams):
            return await self._execute_with_sse(server_params, operation)
        elif isinstance(server_params, StreamableHttpServerParams):
            return await self._execute_with_http(server_params, operation)
        else:
            raise McpConnectionError(f"Unsupported server type: {type(server_params)}")
    
    async def _execute_with_stdio(self, server_params: StdioServerParams, operation):
        """Execute operation with STDIO session"""
        stdio_params = StdioServerParameters(
            command=server_params.command,
            args=server_params.args,
            env=server_params.env
        )
        
        async with stdio_client(stdio_params) as (read, write):
            async with ClientSession(read, write) as session:
                initialize_result = await session.initialize()
                logger.debug(f"Connected to MCP server via STDIO: {server_params.command}")
                return await operation(session, initialize_result)
    
    async def _execute_with_sse(self, server_params: SseServerParams, operation):
        """Execute operation with SSE session"""
        async with sse_client(
            url=server_params.url,
            headers=server_params.headers or {},
            timeout=server_params.timeout,
            sse_read_timeout=server_params.sse_read_timeout
        ) as (read, write):
            async with ClientSession(read, write) as session:
                initialize_result = await session.initialize()
                logger.debug(f"Connected to MCP server via SSE: {server_params.url}")
                return await operation(session, initialize_result)
    
    async def _execute_with_http(self, server_params: StreamableHttpServerParams, operation):
        """Execute operation with StreamableHTTP session"""
        if streamablehttp_client is None:
            raise McpConnectionError("StreamableHTTP client not available in this MCP version")
            
        async with streamablehttp_client(
            url=server_params.url,
            headers=server_params.headers or {},
            timeout=timedelta(seconds=server_params.timeout),
            sse_read_timeout=timedelta(seconds=server_params.sse_read_timeout),
            auth=getattr(server_params, 'auth', None)
        ) as (read, write, get_session_id):
            async with ClientSession(read, write) as session:
                initialize_result = await session.initialize()
                logger.debug(f"Connected to MCP server via StreamableHTTP: {server_params.url}")
                return await operation(session, initialize_result)
    
    async def list_tools(self, server_params: McpServerParams) -> List[Tool]:
        """List available tools from an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                tools_response = await session.list_tools()
                logger.info(f"Listed {len(tools_response.tools)} tools")
                return tools_response.tools
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to list tools: {str(e)}")
            raise McpOperationError(f"Failed to list tools: {str(e)}")
    
    async def call_tool(
        self, 
        server_params: McpServerParams,
        tool_name: str, 
        arguments: Dict[str, Any],
        cancellation_token: Optional[CancellationToken] = None
    ) -> CallToolResult:
        """Call a tool on an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                result = await session.call_tool(tool_name, arguments)
                logger.info(f"Successfully called tool {tool_name}")
                return result
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {str(e)}")
            raise McpOperationError(f"Failed to call tool: {str(e)}")
    
    async def list_resources(self, server_params: McpServerParams) -> List[Resource]:
        """List available resources from an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                resources_response = await session.list_resources()
                logger.info(f"Listed {len(resources_response.resources)} resources")
                return resources_response.resources
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to list resources: {str(e)}")
            raise McpOperationError(f"Failed to list resources: {str(e)}")
    
    async def get_resource(self, server_params: McpServerParams, uri: str) -> ReadResourceResult:
        """Get a specific resource from an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                result = await session.read_resource(AnyUrl(uri))
                logger.info(f"Retrieved resource {uri}")
                return result
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to get resource {uri}: {str(e)}")
            raise McpOperationError(f"Failed to get resource: {str(e)}")
    
    async def list_prompts(self, server_params: McpServerParams) -> List[Prompt]:
        """List available prompts from an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                prompts_response = await session.list_prompts()
                logger.info(f"Listed {len(prompts_response.prompts)} prompts")
                return prompts_response.prompts
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to list prompts: {str(e)}")
            raise McpOperationError(f"Failed to list prompts: {str(e)}")
    
    async def get_prompt(
        self, 
        server_params: McpServerParams,
        name: str, 
        arguments: Optional[Dict[str, Any]] = None
    ) -> GetPromptResult:
        """Get a specific prompt from an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                result = await session.get_prompt(name, arguments or {})
                logger.info(f"Retrieved prompt {name}")
                return result
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to get prompt {name}: {str(e)}")
            raise McpOperationError(f"Failed to get prompt: {str(e)}")
    
    async def get_capabilities(self, server_params: McpServerParams) -> ServerCapabilities:
        """Get server capabilities from an MCP server"""
        try:
            async def operation(session: ClientSession, initialize_result: InitializeResult):
                capabilities = initialize_result.capabilities
                logger.info(f"Retrieved server capabilities")
                return capabilities
            
            return await self._execute_with_session(server_params, operation)
            
        except Exception as e:
            logger.error(f"Failed to get capabilities: {str(e)}")
            raise McpOperationError(f"Failed to get capabilities: {str(e)}")
    
    # Future capability methods (placeholder for when MCP spec supports them)
    async def sample_text(
        self, 
        server_params: McpServerParams,
        prompt: str, 
        **kwargs
    ) -> str:
        """Sample text from an MCP server (future capability)"""
        # TODO: Implement sampling when available in MCP spec
        raise NotImplementedError("Sampling capability not yet implemented in MCP spec")
    
    async def elicit_input(
        self, 
        server_params: McpServerParams,
        prompt: str, 
        input_schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Elicit input from user via MCP server (future capability)"""
        # TODO: Implement elicitation when available in MCP spec
        raise NotImplementedError("Elicitation capability not yet implemented in MCP spec")
    
    async def subscribe_notifications(
        self, 
        server_params: McpServerParams,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Subscribe to notifications from an MCP server (future capability)"""
        # TODO: Implement notifications when available in MCP spec
        raise NotImplementedError("Notifications capability not yet implemented in MCP spec")


