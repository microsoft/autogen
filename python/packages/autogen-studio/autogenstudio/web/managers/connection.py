from fastapi import WebSocket
from typing import Dict, Optional
import asyncio
from datetime import datetime
import logging
from uuid import UUID

from ...datamodel import Run, RunStatus
from ...database.dbmanager import DBManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, db_manager: DBManager, cleanup_interval: int = 300):  # 5 min cleanup
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.db_manager = db_manager
        self._lock = asyncio.Lock()

        # Start cleanup task
        asyncio.create_task(self._cleanup_stale_runs())
        self.cleanup_interval = cleanup_interval

    async def create_run(self, session_id: int) -> Run:
        """Create a new run for a session"""
        run = Run(session_id=session_id)
        response = self.db_manager.upsert(run)
        if not response.status:
            raise Exception(f"Failed to create run: {response.message}")
        return response.data

    async def connect(self, run_id: UUID, websocket: WebSocket) -> bool:
        """Connect a WebSocket to a run"""
        async with self._lock:
            # Get run from database
            run_response = self.db_manager.get(
                Run,
                filters={"id": run_id},
                return_json=False
            )
            if not run_response.status or not run_response.data:
                return False

            run = run_response.data[0]

            # Only allow connection if run is in valid state
            if run.status not in [RunStatus.CREATED, RunStatus.ACTIVE]:
                return False

            # Accept the WebSocket connection
            await websocket.accept()

            # Store connection
            self.active_connections[run_id] = websocket

            # Update run status
            run.status = RunStatus.ACTIVE
            self.db_manager.upsert(run)

            return True

    async def disconnect(self, run_id: UUID) -> None:
        """Disconnect and cleanup a run's WebSocket"""
        async with self._lock:
            if run_id in self.active_connections:
                websocket = self.active_connections[run_id]
                try:
                    await websocket.close()
                except Exception:
                    pass
                finally:
                    del self.active_connections[run_id]

    async def send_message(self, run_id: UUID, message: str) -> bool:
        """Send a message to a run's WebSocket if connected"""
        async with self._lock:
            if run_id in self.active_connections:
                try:
                    await self.active_connections[run_id].send_text(message)
                    return True
                except Exception as e:
                    logger.error(
                        f"Error sending message to run {run_id}: {str(e)}")
                    await self.disconnect(run_id)
            return False

    async def complete_run(self, run_id: UUID, error: Optional[str] = None) -> None:
        """Mark a run as complete or error and cleanup"""
        async with self._lock:
            run_response = self.db_manager.get(
                Run,
                filters={"id": run_id},
                return_json=False
            )
            if run_response.status and run_response.data:
                run = run_response.data[0]
                run.status = RunStatus.ERROR if error else RunStatus.COMPLETE
                run.error_message = error
                self.db_manager.upsert(run)

            await self.disconnect(run_id)

    async def _cleanup_stale_runs(self) -> None:
        """Periodically clean up stale runs"""
        while True:
            try:
                async with self._lock:
                    # Get all active runs
                    active_runs_response = self.db_manager.get(
                        Run,
                        filters={"status": RunStatus.ACTIVE},
                        return_json=False
                    )

                    if active_runs_response.status and active_runs_response.data:
                        for run in active_runs_response.data:
                            # If run is active but has no connection
                            if run.id not in self.active_connections:
                                # Mark as error
                                run.status = RunStatus.ERROR
                                run.error_message = "Connection lost"
                                self.db_manager.upsert(run)

                    # Cleanup disconnected websockets
                    disconnected_runs = [
                        run_id for run_id, ws in self.active_connections.items()
                        if ws.client_state.DISCONNECTED
                    ]
                    for run_id in disconnected_runs:
                        await self.disconnect(run_id)

            except Exception as e:
                logger.error(f"Error in run cleanup: {str(e)}")

            await asyncio.sleep(self.cleanup_interval)
