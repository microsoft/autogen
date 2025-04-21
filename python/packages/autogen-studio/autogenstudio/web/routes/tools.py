from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...datamodel import Tool
from ..deps import get_db

router = APIRouter()


@router.get("/")
async def list_tools(user_id: str, db=Depends(get_db)) -> Dict:
    response = db.get(Tool, filters={"user_id": user_id})
    return {"status": True, "data": response.data}


@router.get("/{tool_id}")
async def get_tool(tool_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    response = db.get(Tool, filters={"id": tool_id, "user_id": user_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"status": True, "data": response.data[0]}


@router.post("/")
async def create_tool(tool: Tool, db=Depends(get_db)) -> Dict:
    response = db.upsert(tool)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.post("/bulk")
async def create_tools(tools: list[Tool], db=Depends(get_db)) -> Dict:
    for tool in tools:
        db.upsert(tool)
    return {"status": True, "data": tools}


@router.delete("/{tool_id}")
async def delete_tool(tool_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    db.delete(filters={"id": tool_id, "user_id": user_id}, model_class=Tool)
    return {"status": True, "message": "Tool deleted successfully"}
