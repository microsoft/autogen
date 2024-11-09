# /api/runs routes
from fastapi import APIRouter, Body, Depends, HTTPException
from uuid import UUID
from typing import Dict

from pydantic import BaseModel
from ..deps import get_db, get_websocket_manager, get_team_manager
from ...datamodel import Run, Session, Message, Team, RunStatus, MessageConfig

from ...teammanager import TeamManager
from autogen_core.base import CancellationToken

router = APIRouter()


class CreateRunRequest(BaseModel):
    session_id: int
    user_id: str


@router.post("/")
async def create_run(
    request: CreateRunRequest,
    db=Depends(get_db),
) -> Dict:
    """Create a new run"""
    session_response = db.get(
        Session,
        filters={"id": request.session_id, "user_id": request.user_id},
        return_json=False
    )
    if not session_response.status or not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    try:

        run = db.upsert(Run(session_id=request.session_id), return_json=False)
        return {
            "status":  run.status,
            "data": {"run_id": str(run.data.id)}
        }

        # }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{run_id}/start")
async def start_run(
    run_id: UUID,
    message: Message = Body(...),
    ws_manager=Depends(get_websocket_manager),
    team_manager=Depends(get_team_manager),
    db=Depends(get_db),
) -> Dict:
    """Start streaming task execution"""

    if isinstance(message.config, dict):
        message.config = MessageConfig(**message.config)

    session = db.get(Session, filters={
                     "id": message.session_id}, return_json=False)

    team = db.get(
        Team, filters={"id": session.data[0].team_id}, return_json=False)

    try:
        await ws_manager.start_stream(run_id, team_manager, message.config.content, team.data[0].config)
        return {
            "status": True,
            "message": "Stream started successfully",
            "data": {"run_id": str(run_id)}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
