from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from autogen_ext.tools.mcp import McpWorkbench
from autogen_ext.tools.mcp._config import McpServerParams
from autogen_core import CancellationToken
from autogen_core.tools import ToolSchema, ToolResult
from loguru import logger

router = APIRouter()

class ListToolsRequest(BaseModel):
    """Request model for listing tools"""
    server_params: McpServerParams

class ListToolsResponse(BaseModel):
    """Response model for listing tools"""
    status: bool
    message: str
    tools: Optional[List[ToolSchema]] = None

class CallToolRequest(BaseModel):
    """Request model for calling a tool"""
    server_params: McpServerParams
    tool_name: str
    arguments: Dict[str, Any]

class CallToolResponse(BaseModel):
    """Response model for tool execution"""
    status: bool
    message: str
    result: Optional[Dict[str, Any]] = None

@router.post("/tools")
async def list_mcp_tools(request: ListToolsRequest) -> ListToolsResponse:
    """List available tools from an MCP server"""
    try:
        logger.info(f"Listing tools for MCP server: {request.server_params.type}")
        
        # Create workbench with server params
        workbench = McpWorkbench(server_params=request.server_params)
        
        await workbench.start()
        
        tools = await workbench.list_tools()
        
        await workbench.stop()
        
        logger.info(f"Successfully listed {len(tools)} tools")
        
        return ListToolsResponse(
            status=True,
            message="Tools retrieved successfully",
            tools=tools
        )
    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}")
        return ListToolsResponse(
            status=False,
            message=f"Failed to list tools: {str(e)}"
        )

@router.post("/tools/call")
async def call_mcp_tool(request: CallToolRequest) -> CallToolResponse:
    """Execute a specific tool with provided arguments"""
    try:
        logger.info(f"Calling tool: {request.tool_name} with args: {request.arguments}")
        
        # Create workbench with server params
        workbench = McpWorkbench(server_params=request.server_params)
        
        await workbench.start()
        
        result = await workbench.call_tool(
            name=request.tool_name,
            arguments=request.arguments,
            cancellation_token=CancellationToken()
        )
        
        await workbench.stop()
        
        # Convert ToolResult to dict for JSON serialization
        result_dict = {
            "name": result.name,
            "result": [],
            "is_error": result.is_error
        }
        
        # Handle different content types in result
        for item in result.result:
            if hasattr(item, 'content'):
                result_dict["result"].append({"content": item.content})
            else:
                result_dict["result"].append({"content": str(item)})
        
        logger.info(f"Successfully executed tool: {request.tool_name}")
        
        return CallToolResponse(
            status=True,
            message="Tool executed successfully",
            result=result_dict
        )
    except Exception as e:
        logger.error(f"Failed to execute tool {request.tool_name}: {str(e)}")
        return CallToolResponse(
            status=False,
            message=f"Failed to execute tool: {str(e)}"
        )

@router.get("/health")
async def mcp_health_check():
    """Health check endpoint for MCP functionality"""
    return {
        "status": True,
        "message": "MCP service is healthy",
    }
