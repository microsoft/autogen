from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...database import DatabaseManager  # Add this import
from ...datamodel import Agent, Model, Tool
from ..deps import get_db

router = APIRouter()


@router.get("/")
async def list_agents(user_id: str, db: DatabaseManager = Depends(get_db)) -> Dict:
    """List all agents for a user"""
    response = db.get(Agent, filters={"user_id": user_id})
    return {"status": True, "data": response.data}


@router.get("/{agent_id}")
async def get_agent(agent_id: int, user_id: str, db: DatabaseManager = Depends(get_db)) -> Dict:
    """Get a specific agent"""
    response = db.get(Agent, filters={"id": agent_id, "user_id": user_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": True, "data": response.data[0]}


@router.post("/")
async def create_agent(agent: Agent, db: DatabaseManager = Depends(get_db)) -> Dict:
    """Create a new agent"""
    response = db.upsert(agent)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, user_id: str, db: DatabaseManager = Depends(get_db)) -> Dict:
    """Delete an agent"""
    db.delete(filters={"id": agent_id, "user_id": user_id}, model_class=Agent)
    return {"status": True, "message": "Agent deleted successfully"}


# Agent-Model link endpoints


@router.post("/{agent_id}/models/{model_id}")
async def link_agent_model(agent_id: int, model_id: int, db: DatabaseManager = Depends(get_db)) -> Dict:
    """Link a model to an agent"""
    db.link(link_type="agent_model", primary_id=agent_id, secondary_id=model_id)
    return {"status": True, "message": "Model linked to agent successfully"}
