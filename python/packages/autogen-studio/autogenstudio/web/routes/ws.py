from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict
from uuid import UUID
import logging
import json
from datetime import datetime

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
            try:
                raw_message = await websocket.receive_text()

                try:
                    message = json.loads(raw_message)

                    # Handle cancel message
                    if message.get("type") == "cancel":
                        logger.info(
                            f"Received cancellation request for run {run_id}")
                        await conn_manager.cancel_run(run_id)
                        await conn_manager.send_message(
                            run_id,
                            json.dumps({
                                "type": "TerminationEvent",
                                "reason": "cancelled",
                                "timestamp": datetime.utcnow().isoformat(),
                                "error": None
                            })
                        )
                        break

                    # Handle ping/heartbeat
                    elif message.get("type") == "ping":
                        await conn_manager.send_message(
                            run_id,
                            json.dumps({
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        )

                    # Unknown message type
                    else:
                        logger.warning(
                            f"Unknown message type for run {run_id}: {message.get('type')}")
                        await conn_manager.send_message(
                            run_id,
                            json.dumps({
                                "type": "error",
                                "error": "Unknown message type",
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        )

                except json.JSONDecodeError:
                    logger.warning(
                        f"Received invalid JSON from client for run {run_id}: {raw_message}")
                    await conn_manager.send_message(
                        run_id,
                        json.dumps({
                            "type": "error",
                            "error": "Invalid message format - expected JSON",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for run {run_id}")
                raise

            except Exception as e:
                logger.error(
                    f"Error processing message for run {run_id}: {str(e)}")
                await conn_manager.send_message(
                    run_id,
                    json.dumps({
                        "type": "error",
                        "error": "Internal server error",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
                raise

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for run {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {str(e)}")
        await conn_manager.complete_run(run_id, error=str(e))
    finally:
        await conn_manager.disconnect(run_id)


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: UUID,
    db=Depends(get_db),
    conn_manager=Depends(get_connection_manager)
) -> Dict:
    """Get the current status of a run"""
    run_response = db.get(
        Run,
        filters={"id": run_id},
        return_json=True
    )
    if not run_response.status or not run_response.data:
        raise HTTPException(status_code=404, detail="Run not found")

    run = run_response.data[0]

    return {
        "status": True,
        "data": {
            "run_id": str(run_id),
            "status": run.status,
            "error": run.error_message,
            "is_connected": run_id in conn_manager.active_connections,
            "has_active_task": run_id in conn_manager.cancellation_tokens
        }
    }
