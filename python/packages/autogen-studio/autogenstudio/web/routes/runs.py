# api/routes/runs.py
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import Dict
import asyncio
from ..deps import get_db, get_connection_manager, get_team_manager
from ...datamodel import Run, Session, Message, Team, MessageConfig, RunStatus

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


@router.get("/runs/{run_id}")
async def get_run(
    run_id: UUID,
    db=Depends(get_db)
) -> Dict:
    """Get run status and details"""
    response = db.get(Run, filters={"id": run_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "status": True,
        "data": response.data[0]
    }


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

    # Start async execution
    async def execute_team():
        try:
            # Save incoming message
            message_response = db.upsert(message)
            if not message_response.status:
                raise Exception(message_response.message)

            # Run the team task
            team_result = await team_manager.run(
                task=message.config.content,
                team_config=team.config
            )

            # Create and save response message
            response_message = Message(
                user_id=message.user_id,
                session_id=run.session_id,
                config=MessageConfig(
                    content=team_result.task_result.messages[-1].content,
                    source=team_result.task_result.messages[-1].source,
                ),
                message_meta={
                    "usage": team_result,
                    "duration": team_result.duration,
                    "team_id": team.id,
                    "run_id": str(run_id)
                }
            )
            db.upsert(response_message)

            # Complete run
            await conn_manager.complete_run(run_id)

        except Exception as e:
            await conn_manager.complete_run(run_id, error=str(e))

    # Start execution in background
    asyncio.create_task(execute_team())

    return {
        "status": True,
        "message": "Run started successfully",
        "data": {"run_id": str(run_id)}
    }


@router.delete("/runs/{run_id}")
async def cancel_run(
    run_id: UUID,
    conn_manager=Depends(get_connection_manager)
) -> Dict:
    """Cancel a running task"""
    await conn_manager.complete_run(run_id, error="Run cancelled by user")
    return {
        "status": True,
        "message": "Run cancelled successfully"
    }
