import json
from typing import Dict, Literal

from autogen_ext.tools.mcp._config import SseServerParams, StdioServerParams
from autogen_ext.tools.mcp._factory import mcp_server_tools
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...datamodel import McpServer, Tool
from ..deps import get_db

router = APIRouter()


class McpToolParams(BaseModel):
    type: Literal["stdio", "sse"]
    server_params: SseServerParams | StdioServerParams


@router.get("/")
async def list_servers(user_id: str, db=Depends(get_db)) -> Dict:
    response = db.get(McpServer, filters={"user_id": user_id})
    return {"status": True, "data": response.data}


@router.get("/{server_id}")
async def get_server(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    response = db.get(McpServer, filters={"id": server_id, "user_id": user_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": True, "data": response.data[0]}


@router.post("/")
async def create_server(server: McpServer, db=Depends(get_db)) -> Dict:
    response = db.upsert(server)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.put("/{server_id}")
async def update_server(server_id: int, server: McpServer, user_id: str, db=Depends(get_db)) -> Dict:
    # Ensure the server exists and belongs to the user
    check_response = db.get(McpServer, filters={"id": server_id, "user_id": user_id})
    if not check_response.status or not check_response.data:
        raise HTTPException(status_code=404, detail="Server not found")

    # Update the server
    server.id = server_id  # Ensure the ID is set correctly
    server.user_id = user_id  # Ensure the user_id is set correctly
    response = db.upsert(server)

    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.delete("/{server_id}")
async def delete_server(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    # Get all tools associated with this server
    tools_response = db.get(Tool, filters={"server_id": server_id, "user_id": user_id})

    # Delete the tools first
    if tools_response.status and tools_response.data:
        for tool in tools_response.data:
            db.delete(filters={"id": tool.id}, model_class=Tool)

    # Then delete the server
    db.delete(filters={"id": server_id, "user_id": user_id}, model_class=McpServer)
    return {"status": True, "message": "Server and associated tools deleted successfully"}


@router.get("/{server_id}/tools")
async def get_server_tools(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    # First check if server exists
    server_response = db.get(McpServer, filters={"id": server_id, "user_id": user_id})
    if not server_response.status or not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")

    tools_response = db.get(Tool, filters={"server_id": server_id, "user_id": user_id})
    return {"status": True, "data": tools_response.data}


@router.post("/discover")
async def discover_server_tools(params: McpToolParams):
    """Discover tools from an MCP server without storing them"""
    try:
        tools = await mcp_server_tools(params.server_params)
        if not tools:
            raise HTTPException(status_code=400, detail="Failed to retrieve tools")
        return [tool.dump_component() for tool in tools]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{server_id}/refresh")
async def refresh_server_tools(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Refresh tools for an existing server"""
    # Get the server
    server_response = db.get(McpServer, filters={"id": server_id, "user_id": user_id})
    if not server_response.status or not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = server_response.data[0]
    params = None
    
    config = server.component.get("config", {})
    server_params = config.get("server_params", {})
    if "command" in server_params:
        params = McpToolParams(
            type="stdio",
            server_params=StdioServerParams(
                command=server_params["command"],
                args=server_params["args"],
                env=server_params["env"]
            )
        )
    elif "url" in server_params:
        params = McpToolParams(
            type="sse",
            server_params=SseServerParams(
                url=server_params["url"]
            )
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid server configuration")

    try:
        # Use the same discovery logic as the tools endpoint
        tools_components = await discover_server_tools(params)

        # Update server last_connected timestamp
        from datetime import datetime
        server.last_connected = datetime.now()
        db.upsert(server)

        # Get existing tools for this server
        existing_tools_response = db.get(Tool, filters={"server_id": server_id, "user_id": user_id})
        existing_tools = existing_tools_response.data if existing_tools_response.status else []

        # Create a set of existing tool identifiers for quick lookup
        existing_tool_ids = {tool.component['provider'] for tool in existing_tools}
        
        # Add new tools that don't already exist
        new_tools_count = 0
        for tool_component in tools_components:
            provider = tool_component.provider
            if provider not in existing_tool_ids:
                new_tool = Tool(
                    user_id=user_id,
                    server_id=server_id,
                    component=tool_component.dict()
                )
                db.upsert(new_tool)
                new_tools_count += 1
        
        return {
            "status": True, 
            "message": f"Server refreshed successfully. Added {new_tools_count} new tools.",
            "data": {
                "new_tools_count": new_tools_count,
                "total_tools_count": len(existing_tools) + new_tools_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to refresh server: {str(e)}")