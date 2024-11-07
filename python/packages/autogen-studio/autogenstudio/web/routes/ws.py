# api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict
from uuid import UUID
import logging
import json
from datetime import datetime

from ..deps import get_websocket_manager, get_db, get_team_manager
from ...datamodel import Run, RunStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/runs/{run_id}")
async def run_websocket(
    websocket: WebSocket,
    run_id: UUID,
    ws_manager=Depends(get_websocket_manager),
    db=Depends(get_db),
    team_manager=Depends(get_team_manager)
):
    """WebSocket endpoint for run communication"""
    # Verify run exists and is in valid state
    run_response = db.get(Run, filters={"id": run_id}, return_json=False)
    if not run_response.status or not run_response.data:
        await websocket.close(code=4004, reason="Run not found")
        return

    run = run_response.data[0]
    if run.status not in [RunStatus.CREATED, RunStatus.ACTIVE]:
        await websocket.close(code=4003, reason="Run not in valid state")
        return

    # Connect websocket
    connected = await ws_manager.connect(websocket, run_id)
    if not connected:
        await websocket.close(code=4002, reason="Failed to establish connection")
        return

    try:
        logger.info(f"WebSocket connection established for run {run_id}")

        while True:
            try:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)

                if message.get("type") == "stop":
                    logger.info(f"Received stop request for run {run_id}")
                    await ws_manager.stop_run(run_id)
                    break

                elif message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {raw_message}")
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid message format",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await ws_manager.disconnect(run_id)
