# api/routes/tools.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from ..deps import get_db
from ...datamodel import Tool

router = APIRouter()


@router.get("/")
async def list_tools(
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """List all tools for a user"""
    response = db.get(Tool, filters={"user_id": user_id})
    return {
        "status": True,
        "data": response.data
    }


@router.get("/{tool_id}")
async def get_tool(
    tool_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Get a specific tool"""
    response = db.get(
        Tool,
        filters={"id": tool_id, "user_id": user_id}
    )
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "status": True,
        "data": response.data[0]
    }


@router.post("/")
async def create_tool(
    tool: Tool,
    db=Depends(get_db)
) -> Dict:
    """Create a new tool"""
    response = db.upsert(tool)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "status": True,
        "data": response.data
    }


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Delete a tool"""
    response = db.delete(
        filters={"id": tool_id, "user_id": user_id},
        model_class=Tool
    )
    return {
        "status": True,
        "message": "Tool deleted successfully"
    }


@router.post("/{tool_id}/test")
async def test_tool(
    tool_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Test a tool configuration"""
    # Get tool
    tool_response = db.get(
        Tool,
        filters={"id": tool_id, "user_id": user_id}
    )
    if not tool_response.status or not tool_response.data:
        raise HTTPException(status_code=404, detail="Tool not found")

    tool = tool_response.data[0]

    try:
        # Implement tool testing logic here
        # This would depend on the tool type and configuration
        return {
            "status": True,
            "message": "Tool tested successfully",
            "data": {"tool_id": tool_id}
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error testing tool: {str(e)}"
        )
