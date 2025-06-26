from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
from loguru import logger

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool, Resource, Prompt, CallToolResult, GetPromptResult, ReadResourceResult, TextContent, ImageContent, EmbeddedResource
from pydantic import AnyUrl
import httpx

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
    """Direct MCP client that creates connections on-demand"""
    
    def __init__(self):
        self.exit_stack: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None
    
    async def _get_session(self, server_params: McpServerParams) -> ClientSession:
        """Get session based on server transport type"""
        try:
            self.exit_stack = AsyncExitStack()
            
            if isinstance(server_params, StdioServerParams):
                return await self._connect_stdio(server_params)
            elif isinstance(server_params, SseServerParams):
                return await self._connect_sse(server_params)
            elif isinstance(server_params, StreamableHttpServerParams):
                return await self._connect_http(server_params)
            else:
                raise McpConnectionError(f"Unsupported server type: {type(server_params)}")
                
        except Exception as e:
            await self.cleanup()
            raise McpConnectionError(f"Failed to create session: {str(e)}")
    
    async def _connect_stdio(self, server_params: StdioServerParams) -> ClientSession:
        """Connect to STDIO MCP server"""
        if not self.exit_stack:
            raise McpConnectionError("Exit stack not initialized")
            
        stdio_params = StdioServerParameters(
            command=server_params.command,
            args=server_params.args,
            env=server_params.env
        )
        
        # Create STDIO transport
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(stdio_params)
        )
        read, write = stdio_transport
        
        # Create and initialize session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()
        
        logger.info(f"Connected to MCP server via STDIO: {server_params.command}")
        return self.session
    
    async def _connect_sse(self, server_params: SseServerParams) -> ClientSession:
        """Connect to SSE MCP server"""
        if not self.exit_stack:
            raise McpConnectionError("Exit stack not initialized")
            
        # Create SSE transport
        sse_transport = await self.exit_stack.enter_async_context(
            sse_client(
                url=server_params.url,
                headers=server_params.headers or {},
                timeout=server_params.timeout,
                sse_read_timeout=server_params.sse_read_timeout
            )
        )
        read, write = sse_transport
        
        # Create and initialize session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()
        
        logger.info(f"Connected to MCP server via SSE: {server_params.url}")
        return self.session
    
    async def _connect_http(self, server_params: StreamableHttpServerParams) -> ClientSession:
        """Connect to HTTP MCP server"""
        # For now, we'll use httpx directly since streamable_http_client might not be available
        # This is a placeholder - you might need to implement this based on your MCP version
        raise NotImplementedError("HTTP transport not yet implemented - check your MCP SDK version")
    
    async def cleanup(self) -> None:
        """Clean up connection resources"""
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            finally:
                self.exit_stack = None
                self.session = None
    
    async def list_tools(self, server_params: McpServerParams) -> List[Tool]:
        """List available tools from an MCP server"""
        try:
            session = await self._get_session(server_params)
            
            # Get tools from MCP server
            tools_response = await session.list_tools()
            
            logger.info(f"Listed {len(tools_response.tools)} tools")
            return tools_response.tools
            
        except Exception as e:
            logger.error(f"Failed to list tools: {str(e)}")
            raise McpOperationError(f"Failed to list tools: {str(e)}")
        finally:
            await self.cleanup()
    
    async def call_tool(
        self, 
        server_params: McpServerParams,
        tool_name: str, 
        arguments: Dict[str, Any],
        cancellation_token: Optional[CancellationToken] = None
    ) -> CallToolResult:
        """Call a tool on an MCP server"""
        try:
            session = await self._get_session(server_params)
            
            # Call the tool
            result = await session.call_tool(tool_name, arguments)
            
            logger.info(f"Successfully called tool {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {str(e)}")
            raise McpOperationError(f"Failed to call tool: {str(e)}")
        finally:
            await self.cleanup()
    
    async def list_resources(self, server_params: McpServerParams) -> List[Resource]:
        """List available resources from an MCP server"""
        try:
            session = await self._get_session(server_params)
            resources_response = await session.list_resources()
            
            logger.info(f"Listed {len(resources_response.resources)} resources")
            return resources_response.resources
            
        except Exception as e:
            logger.error(f"Failed to list resources: {str(e)}")
            raise McpOperationError(f"Failed to list resources: {str(e)}")
        finally:
            await self.cleanup()
    
    async def get_resource(self, server_params: McpServerParams, uri: str) -> ReadResourceResult:
        """Get a specific resource from an MCP server"""
        try:
            session = await self._get_session(server_params)
            result = await session.read_resource(AnyUrl(uri))
            
            logger.info(f"Retrieved resource {uri}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get resource {uri}: {str(e)}")
            raise McpOperationError(f"Failed to get resource: {str(e)}")
        finally:
            await self.cleanup()
    
    async def list_prompts(self, server_params: McpServerParams) -> List[Prompt]:
        """List available prompts from an MCP server"""
        try:
            session = await self._get_session(server_params)
            prompts_response = await session.list_prompts()
            
            logger.info(f"Listed {len(prompts_response.prompts)} prompts")
            return prompts_response.prompts
            
        except Exception as e:
            logger.error(f"Failed to list prompts: {str(e)}")
            raise McpOperationError(f"Failed to list prompts: {str(e)}")
        finally:
            await self.cleanup()
    
    async def get_prompt(
        self, 
        server_params: McpServerParams,
        name: str, 
        arguments: Optional[Dict[str, Any]] = None
    ) -> GetPromptResult:
        """Get a specific prompt from an MCP server"""
        try:
            session = await self._get_session(server_params)
            result = await session.get_prompt(name, arguments or {})
            
            logger.info(f"Retrieved prompt {name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get prompt {name}: {str(e)}")
            raise McpOperationError(f"Failed to get prompt: {str(e)}")
        finally:
            await self.cleanup()
    
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
