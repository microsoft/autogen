from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from autogen_ext.tools.mcp._config import McpServerParams
from autogen_core import CancellationToken
from loguru import logger
from mcp.types import (
    TextResourceContents, 
    BlobResourceContents, 
    TextContent, 
    ImageContent, 
    Tool,
    CallToolResult,
    Resource,
    Prompt,
    GetPromptResult,
    ReadResourceResult
)

# Import your new MCP client
from autogenstudio.mcp.client import (
    McpClient,
    McpOperationError,
    McpConnectionError
)

router = APIRouter()

class ListToolsRequest(BaseModel):
    """Request model for listing tools"""
    server_params: McpServerParams

class ListToolsResponse(BaseModel):
    """Response model for listing tools"""
    status: bool
    message: str
    tools: Optional[List[Tool]] = None

class CallToolRequest(BaseModel):
    """Request model for calling a tool"""
    server_params: McpServerParams
    tool_name: str
    arguments: Dict[str, Any]

class CallToolResponse(BaseModel):
    """Response model for tool execution"""
    status: bool
    message: str
    result: Optional[CallToolResult] = None

# Additional request models for new capabilities
class ListResourcesRequest(BaseModel):
    """Request model for listing resources"""
    server_params: McpServerParams

class GetResourceRequest(BaseModel):
    """Request model for getting a resource"""
    server_params: McpServerParams
    uri: str

class ListPromptsRequest(BaseModel):
    """Request model for listing prompts"""
    server_params: McpServerParams

class GetPromptRequest(BaseModel):
    """Request model for getting a prompt"""
    server_params: McpServerParams
    name: str
    arguments: Optional[Dict[str, Any]] = None

@router.post("/tools/list")
async def list_mcp_tools(request: ListToolsRequest) -> ListToolsResponse:
    """List available tools from an MCP server"""
    try:
        logger.info(f"Listing tools for MCP server: {request.server_params.type}")
        
        # Use the new MCP client directly
        client = McpClient()
        tools: List[Tool] = await client.list_tools(request.server_params)
        
        logger.info(f"Successfully listed {len(tools)} tools")
        
        return ListToolsResponse(
            status=True,
            message="Tools retrieved successfully",
            tools=tools
        )
    except (McpConnectionError, McpOperationError) as e:
        logger.error(f"MCP error listing tools: {str(e)}")
        return ListToolsResponse(
            status=False,
            message=f"Failed to list tools: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing tools: {str(e)}")
        return ListToolsResponse(
            status=False,
            message=f"Failed to list tools: {str(e)}"
        )

@router.post("/tools/call")
async def call_mcp_tool(request: CallToolRequest) -> CallToolResponse:
    """Execute a specific tool with provided arguments"""
    try:
        logger.info(f"Calling tool: {request.tool_name} with args: {request.arguments}")
        
        # Use the new MCP client directly
        client = McpClient()
        result = await client.call_tool(
            server_params=request.server_params,
            tool_name=request.tool_name,
            arguments=request.arguments
        )
        
        logger.info(f"Successfully executed tool: {request.tool_name}")
        
        return CallToolResponse(
            status=True,
            message="Tool executed successfully",
            result=result
        )
    except (McpConnectionError, McpOperationError) as e:
        logger.error(f"MCP error executing tool {request.tool_name}: {str(e)}")
        return CallToolResponse(
            status=False,
            message=f"Failed to execute tool: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error executing tool {request.tool_name}: {str(e)}")
        return CallToolResponse(
            status=False,
            message=f"Failed to execute tool: {str(e)}"
        )

@router.post("/resources/list")
async def list_mcp_resources(request: ListResourcesRequest):
    """List available resources from an MCP server"""
    try:
        logger.info(f"Listing resources for MCP server: {request.server_params.type}")
        
        client = McpClient()
        resources = await client.list_resources(request.server_params)
        
        # Convert resources to serializable format
        resource_list = [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": getattr(resource, 'mimeType', None)
            }
            for resource in resources
        ]
        
        return {
            "status": True,
            "message": "Resources retrieved successfully",
            "resources": resource_list
        }
    except (McpConnectionError, McpOperationError) as e:
        logger.error(f"MCP error listing resources: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to list resources: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error listing resources: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to list resources: {str(e)}"
        }

@router.post("/resources/get")
async def get_mcp_resource(request: GetResourceRequest):
    """Get a specific resource from an MCP server"""
    try:
        logger.info(f"Getting resource: {request.uri}")
        
        client = McpClient()
        result = await client.get_resource(request.server_params, request.uri)
        
        # Convert result to serializable format
        content_list = []
        for content in result.contents:
            # Handle different content types using isinstance
            if isinstance(content, TextResourceContents):
                content_list.append({"type": "text", "text": content.text})
            elif isinstance(content, BlobResourceContents):
                content_list.append({
                    "type": "blob", 
                    "blob": content.blob,
                    "mimeType": getattr(content, 'mimeType', None)
                })
            else:
                # Fallback for unknown content types
                content_dict = {"type": "unknown"}
                # Try to extract any available content
                if hasattr(content, '__dict__'):
                    content_dict.update(content.__dict__)
                else:
                    content_dict["content"] = str(content)
                content_list.append(content_dict)
        
        return {
            "status": True,
            "message": "Resource retrieved successfully",
            "uri": request.uri,
            "contents": content_list
        }
    except (McpConnectionError, McpOperationError) as e:
        logger.error(f"MCP error getting resource: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to get resource: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error getting resource: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to get resource: {str(e)}"
        }

@router.post("/prompts/list")
async def list_mcp_prompts(request: ListPromptsRequest):
    """List available prompts from an MCP server"""
    try:
        logger.info(f"Listing prompts for MCP server: {request.server_params.type}")
        
        client = McpClient()
        prompts = await client.list_prompts(request.server_params)
        
        # Convert prompts to serializable format
        prompt_list = [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": getattr(prompt, 'arguments', [])
            }
            for prompt in prompts
        ]
        
        return {
            "status": True,
            "message": "Prompts retrieved successfully",
            "prompts": prompt_list
        }
    except (McpConnectionError, McpOperationError) as e:
        logger.error(f"MCP error listing prompts: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to list prompts: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error listing prompts: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to list prompts: {str(e)}"
        }

@router.post("/prompts/get")
async def get_mcp_prompt(request: GetPromptRequest):
    """Get a specific prompt from an MCP server"""
    try:
        logger.info(f"Getting prompt: {request.name}")
        
        client = McpClient()
        result = await client.get_prompt(
            request.server_params, 
            request.name, 
            request.arguments
        )
        
        # Convert result to serializable format
        messages = []
        for message in result.messages:
            messages.append({
                "role": message.role,
                "content": message.content
            })
        
        return {
            "status": True,
            "message": "Prompt retrieved successfully",
            "name": request.name,
            "description": result.description,
            "messages": messages
        }
    except (McpConnectionError, McpOperationError) as e:
        logger.error(f"MCP error getting prompt: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to get prompt: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error getting prompt: {str(e)}")
        return {
            "status": False,
            "message": f"Failed to get prompt: {str(e)}"
        }

# Future capability endpoints (placeholder)

@router.post("/sampling/text")
async def sample_text(request: dict):
    """Sample text from an MCP server (future capability)"""
    return {
        "status": False,
        "message": "Sampling capability not yet implemented in MCP spec"
    }

@router.post("/elicitation/input")
async def elicit_input(request: dict):
    """Elicit input from user via MCP server (future capability)"""
    return {
        "status": False,
        "message": "Elicitation capability not yet implemented in MCP spec"
    }

@router.get("/health")
async def mcp_health_check():
    """Health check endpoint for MCP functionality"""
    return {
        "status": True,
        "message": "MCP service is healthy",
    }
