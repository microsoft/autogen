from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...datamodel import Tool, ToolServer
from ...toolservermanager import ToolServerManager
from ..deps import get_db

router = APIRouter()


@router.get("/")
async def list_servers(user_id: str, db=Depends(get_db)) -> Dict:
    response = db.get(ToolServer, filters={"user_id": user_id})
    return {"status": True, "data": response.data}


@router.get("/{server_id}")
async def get_server(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    response = db.get(ToolServer, filters={"id": server_id, "user_id": user_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": True, "data": response.data[0]}


@router.post("/")
async def create_server(server: ToolServer, db=Depends(get_db)) -> Dict:
    response = db.upsert(server)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.put("/{server_id}")
async def update_server(server_id: int, server: ToolServer, user_id: str, db=Depends(get_db)) -> Dict:
    # Ensure the server exists and belongs to the user
    check_response = db.get(ToolServer, filters={"id": server_id, "user_id": user_id})
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
    db.delete(filters={"id": server_id, "user_id": user_id}, model_class=ToolServer)
    return {"status": True, "message": "Server and associated tools deleted successfully"}


@router.get("/{server_id}/tools")
async def get_server_tools(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    # First check if server exists
    server_response = db.get(ToolServer, filters={"id": server_id, "user_id": user_id})
    if not server_response.status or not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")

    tools_response = db.get(Tool, filters={"server_id": server_id, "user_id": user_id})
    return {"status": True, "data": tools_response.data}


@router.post("/{server_id}/refresh")
async def refresh_server_tools(server_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Refresh tools for an existing server"""

    server_response = db.get(ToolServer, filters={"id": server_id, "user_id": user_id})
    if not server_response.status or not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")

    server = server_response.data[0]
    tsm = ToolServerManager()

    try:
        # Use the same discovery logic as the tools endpoint
        tools_components = await tsm.discover_tools(server.component)

        # Update server last_connected timestamp
        from datetime import datetime

        server.last_connected = datetime.now()
        db.upsert(server)

        updated_count = 0
        created_count = 0

        for tool_component in tools_components:
            # Generate a unique identifier for the tool from its component
            component_data = tool_component.dump_component().model_dump()

            # Check if the tool already exists based on id/name
            component_config = component_data.get("config", {})
            tool_config = component_config.get("tool", {})
            tool_name = tool_config.get("name", None)

            # First get all tools for this server and user
            existing_tool_response = db.get(Tool, filters={"server_id": server_id, "user_id": user_id})

            matching_tools = []
            if existing_tool_response.status and existing_tool_response.data:
                for tool in existing_tool_response.data:
                    try:
                        tool_comp = tool.component
                        if tool_comp.get("config", {}).get("tool", {}).get("name") == tool_name:
                            matching_tools.append(tool)
                    except Exception:
                        pass

            # Update existing_tool_response to use our filtered results
            existing_tool_response.data = matching_tools

            if existing_tool_response.status and existing_tool_response.data:
                # Tool exists, update it
                existing_tool = existing_tool_response.data[0]
                existing_tool.component = component_data
                db.upsert(existing_tool)
                updated_count += 1
            else:
                # Tool does not exist, create new
                new_tool = Tool(user_id=user_id, server_id=server_id, component=component_data)
                # print(f"Creating new tool: {new_tool}")
                db.upsert(new_tool)
                created_count += 1

        return {
            "status": True,
            "message": "Server refreshed successfully.",
            "data": {
                "total_count": len(tools_components),
                "updated_count": updated_count,
                "created_count": created_count,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to refresh server: {str(e)}") from e
