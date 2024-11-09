# api/routes/agents.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from ..deps import get_db
from ...datamodel import Agent, Model, Tool

router = APIRouter()


@router.get("/")
async def list_agents(
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """List all agents for a user"""
    response = db.get(Agent, filters={"user_id": user_id})
    return {
        "status": True,
        "data": response.data
    }


@router.get("/{agent_id}")
async def get_agent(
    agent_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Get a specific agent"""
    response = db.get(
        Agent,
        filters={"id": agent_id, "user_id": user_id}
    )
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "status": True,
        "data": response.data[0]
    }


@router.post("/")
async def create_agent(
    agent: Agent,
    db=Depends(get_db)
) -> Dict:
    """Create a new agent"""
    response = db.upsert(agent)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "status": True,
        "data": response.data
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Delete an agent"""
    response = db.delete(
        filters={"id": agent_id, "user_id": user_id},
        model_class=Agent
    )
    return {
        "status": True,
        "message": "Agent deleted successfully"
    }

# Agent-Model link endpoints


@router.post("/{agent_id}/models/{model_id}")
async def link_agent_model(
    agent_id: int,
    model_id: int,
    db=Depends(get_db)
) -> Dict:
    """Link a model to an agent"""
    response = db.link(
        link_type="agent_model",
        primary_id=agent_id,
        secondary_id=model_id
    )
    return {
        "status": True,
        "message": "Model linked to agent successfully"
    }


@router.delete("/{agent_id}/models/{model_id}")
async def unlink_agent_model(
    agent_id: int,
    model_id: int,
    db=Depends(get_db)
) -> Dict:
    """Unlink a model from an agent"""
    response = db.unlink(
        link_type="agent_model",
        primary_id=agent_id,
        secondary_id=model_id
    )
    return {
        "status": True,
        "message": "Model unlinked from agent successfully"
    }


@router.get("/{agent_id}/models")
async def get_agent_models(
    agent_id: int,
    db=Depends(get_db)
) -> Dict:
    """Get all models linked to an agent"""
    response = db.get_linked_entities(
        link_type="agent_model",
        primary_id=agent_id,
        return_json=True
    )
    return {
        "status": True,
        "data": response.data
    }

# Agent-Tool link endpoints


@router.post("/{agent_id}/tools/{tool_id}")
async def link_agent_tool(
    agent_id: int,
    tool_id: int,
    db=Depends(get_db)
) -> Dict:
    """Link a tool to an agent"""
    response = db.link(
        link_type="agent_tool",
        primary_id=agent_id,
        secondary_id=tool_id
    )
    return {
        "status": True,
        "message": "Tool linked to agent successfully"
    }


@router.delete("/{agent_id}/tools/{tool_id}")
async def unlink_agent_tool(
    agent_id: int,
    tool_id: int,
    db=Depends(get_db)
) -> Dict:
    """Unlink a tool from an agent"""
    response = db.unlink(
        link_type="agent_tool",
        primary_id=agent_id,
        secondary_id=tool_id
    )
    return {
        "status": True,
        "message": "Tool unlinked from agent successfully"
    }


@router.get("/{agent_id}/tools")
async def get_agent_tools(
    agent_id: int,
    db=Depends(get_db)
) -> Dict:
    """Get all tools linked to an agent"""
    response = db.get_linked_entities(
        link_type="agent_tool",
        primary_id=agent_id,
        return_json=True
    )
    return {
        "status": True,
        "data": response.data
    }
