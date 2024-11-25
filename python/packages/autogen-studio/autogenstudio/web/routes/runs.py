# /api/runs routes
from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from ...datamodel import Message, MessageConfig, Run, RunStatus, Session, Team
from ..deps import get_db, get_team_manager, get_websocket_manager

router = APIRouter()


class CreateRunRequest(BaseModel):
    session_id: int
    user_id: str


@router.post("/")
async def create_run(
    request: CreateRunRequest,
    db=Depends(get_db),
) -> Dict:
    """Create a new run with initial state"""
    session_response = db.get(
        Session, filters={"id": request.session_id, "user_id": request.user_id}, return_json=False
    )
    if not session_response.status or not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Create run with default state
        run = db.upsert(
            Run(
                session_id=request.session_id,
                status=RunStatus.CREATED,
                task=None,  # Will be set when run starts
                team_result=None,
            ),
            return_json=False,
        )
        return {"status": run.status, "data": {"run_id": str(run.data.id)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{run_id}/start")
async def start_run(
    run_id: UUID,
    message: Message = Body(...),
    ws_manager=Depends(get_websocket_manager),
    team_manager=Depends(get_team_manager),
    db=Depends(get_db),
) -> Dict:
    """Start run with task message"""
    if isinstance(message.config, dict):
        message.config = MessageConfig(**message.config)

    # Get session and team
    session = db.get(Session, filters={"id": message.session_id}, return_json=False)
    if not session.status or not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    team = db.get(Team, filters={"id": session.data[0].team_id}, return_json=False)
    if not team.status or not team.data:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        # Update run with task message
        run = db.get(Run, filters={"id": run_id}, return_json=False)
        if not run.status or not run.data:
            raise HTTPException(status_code=404, detail="Run not found")

        run = run.data[0]
        run.task = message.config.model_dump()  # Set the task
        run.status = RunStatus.ACTIVE
        db.upsert(run)

        # Start stream
        await ws_manager.start_stream(run_id, team_manager, message.config.content, team.data[0].config)

        return {"status": True, "message": "Stream started successfully", "data": {"run_id": str(run_id)}}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# We might want to add these endpoints:


@router.get("/{run_id}")
async def get_run(run_id: UUID, db=Depends(get_db)) -> Dict:
    """Get run details including task and result"""
    run = db.get(Run, filters={"id": run_id}, return_json=False)
    if not run.status or not run.data:
        raise HTTPException(status_code=404, detail="Run not found")

    return {"status": True, "data": run.data[0]}


@router.get("/{run_id}/messages")
async def get_run_messages(run_id: UUID, db=Depends(get_db)) -> Dict:
    """Get all messages for a run"""
    messages = db.get(Message, filters={"run_id": run_id}, order="created_at asc", return_json=False)

    return {"status": True, "data": messages.data}
