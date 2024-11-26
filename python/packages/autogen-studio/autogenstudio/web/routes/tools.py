# api/routes/tools.py
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...datamodel import Tool
from ..deps import get_db

router = APIRouter()


@router.get("/")
async def list_tools(user_id: str, db=Depends(get_db)) -> Dict:
    """List all tools for a user"""
    response = db.get(Tool, filters={"user_id": user_id})
    return {"status": True, "data": response.data}


@router.get("/{tool_id}")
async def get_tool(tool_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Get a specific tool"""
    response = db.get(Tool, filters={"id": tool_id, "user_id": user_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"status": True, "data": response.data[0]}


@router.post("/")
async def create_tool(tool: Tool, db=Depends(get_db)) -> Dict:
    """Create a new tool"""
    response = db.upsert(tool)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.delete("/{tool_id}")
async def delete_tool(tool_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Delete a tool"""
    db.delete(filters={"id": tool_id, "user_id": user_id}, model_class=Tool)
    return {"status": True, "message": "Tool deleted successfully"}
