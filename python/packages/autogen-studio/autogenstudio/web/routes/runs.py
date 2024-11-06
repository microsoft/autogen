# api/routes/runs.py
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import Dict
import asyncio
from ..deps import get_db, get_connection_manager, get_team_manager
from ...datamodel import Run, Session, Message, Team, RunStatus

router = APIRouter()


@router.post("/sessions/{session_id}/runs")
async def create_run(
    session_id: int,
    user_id: str,
    db=Depends(get_db),
    conn_manager=Depends(get_connection_manager)
) -> Dict:
    """Create a new run for a session"""
    session_response = db.get(
        Session,
        filters={"id": session_id, "user_id": user_id},
        return_json=False
    )
    if not session_response.status or not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        run = await conn_manager.create_run(session_id)
        return {
            "status": True,
            "data": {"run_id": str(run.id)}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs/{run_id}/start")
async def start_run(
    run_id: UUID,
    message: Message,
    db=Depends(get_db),
    conn_manager=Depends(get_connection_manager),
    team_manager=Depends(get_team_manager)
) -> Dict:
    """Start a run with a team task"""
    # Get run and verify status
    run_response = db.get(Run, filters={"id": run_id}, return_json=False)
    if not run_response.status or not run_response.data:
        raise HTTPException(status_code=404, detail="Run not found")

    run = run_response.data[0]
    if run.status != RunStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Run not in active state")

    # Get team
    team_response = db.get(
        Team,
        filters={"id": message.message_meta.get("team_id")},
        return_json=False
    )
    if not team_response.status or not team_response.data:
        raise HTTPException(status_code=404, detail="Team not found")

    team = team_response.data[0]

    # Start streaming task in background
    asyncio.create_task(conn_manager.start_streaming_task(
        run_id=run_id,
        team_manager=team_manager,
        task=message.config.content,
        team_config=team.config
    ))

    return {
        "status": True,
        "message": "Run started successfully",
        "data": {"run_id": str(run_id)}
    }
