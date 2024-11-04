# api/routes/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict
from uuid import UUID
import logging
from ..deps import get_connection_manager, get_db
from ...datamodel import Run, RunStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/runs/{run_id}")
async def run_websocket(
    websocket: WebSocket,
    run_id: UUID,
    conn_manager=Depends(get_connection_manager),
    db=Depends(get_db)
):
    """WebSocket endpoint for run communication"""
    # Verify run exists and is in valid state
    run_response = db.get(
        Run,
        filters={"id": run_id},
        return_json=False
    )
    if not run_response.status or not run_response.data:
        await websocket.close(code=4004, reason="Run not found")
        return

    run = run_response.data[0]
    if run.status not in [RunStatus.CREATED, RunStatus.ACTIVE]:
        await websocket.close(code=4003, reason="Run not in valid state")
        return

    # Attempt connection
    connected = await conn_manager.connect(run_id, websocket)
    if not connected:
        await websocket.close(code=4002, reason="Failed to establish connection")
        return

    try:
        logger.info(f"WebSocket connection established for run {run_id}")

        while True:
            # Keep connection alive and handle any client messages
            message = await websocket.receive_text()

            # Handle any specific message types if needed
            # For now, just echo back
            await conn_manager.send_message(run_id, f"Received: {message}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for run {run_id}")
        await conn_manager.disconnect(run_id)
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {str(e)}")
        await conn_manager.complete_run(run_id, error=str(e))
    finally:
        # Ensure cleanup happens
        if run_id in conn_manager.active_connections:
            await conn_manager.disconnect(run_id)


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: UUID,
    db=Depends(get_db)
) -> Dict:
    """Get the current status of a run"""
    run_response = db.get(
        Run,
        filters={"id": run_id},
        return_json=True
    )
    if not run_response.status or not run_response.data:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "status": True,
        "data": {
            "run_id": str(run_id),
            "status": run_response.data[0].status,
            "error": run_response.data[0].error_message
        }
    }
