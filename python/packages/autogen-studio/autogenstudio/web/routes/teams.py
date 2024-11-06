# api/routes/teams.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from ..deps import get_db
from ...datamodel import Team

router = APIRouter()


@router.get("/")
async def list_teams(
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """List all teams for a user"""
    response = db.get(Team, filters={"user_id": user_id})
    return {
        "status": True,
        "data": response.data
    }


@router.get("/{team_id}")
async def get_team(
    team_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Get a specific team"""
    response = db.get(
        Team,
        filters={"id": team_id, "user_id": user_id}
    )
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Team not found")
    return {
        "status": True,
        "data": response.data[0]
    }


@router.post("/")
async def create_team(
    team: Team,
    db=Depends(get_db)
) -> Dict:
    """Create a new team"""
    response = db.upsert(team)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "status": True,
        "data": response.data
    }


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Delete a team"""
    response = db.delete(
        filters={"id": team_id, "user_id": user_id},
        model_class=Team
    )
    return {
        "status": True,
        "message": "Team deleted successfully"
    }

# Team-Agent link endpoints


@router.post("/{team_id}/agents/{agent_id}")
async def link_team_agent(
    team_id: int,
    agent_id: int,
    db=Depends(get_db)
) -> Dict:
    """Link an agent to a team"""
    response = db.link(
        link_type="team_agent",
        primary_id=team_id,
        secondary_id=agent_id
    )
    return {
        "status": True,
        "message": "Agent linked to team successfully"
    }


@router.post("/{team_id}/agents/{agent_id}/{sequence_id}")
async def link_team_agent_sequence(
    team_id: int,
    agent_id: int,
    sequence_id: int,
    db=Depends(get_db)
) -> Dict:
    """Link an agent to a team with sequence"""
    response = db.link(
        link_type="team_agent",
        primary_id=team_id,
        secondary_id=agent_id,
        sequence_id=sequence_id
    )
    return {
        "status": True,
        "message": "Agent linked to team with sequence successfully"
    }


@router.delete("/{team_id}/agents/{agent_id}")
async def unlink_team_agent(
    team_id: int,
    agent_id: int,
    db=Depends(get_db)
) -> Dict:
    """Unlink an agent from a team"""
    response = db.unlink(
        link_type="team_agent",
        primary_id=team_id,
        secondary_id=agent_id
    )
    return {
        "status": True,
        "message": "Agent unlinked from team successfully"
    }


@router.get("/{team_id}/agents")
async def get_team_agents(
    team_id: int,
    db=Depends(get_db)
) -> Dict:
    """Get all agents linked to a team"""
    response = db.get_linked_entities(
        link_type="team_agent",
        primary_id=team_id,
        return_json=True
    )
    return {
        "status": True,
        "data": response.data
    }
