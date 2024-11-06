from fastapi import WebSocket
from typing import Dict, Optional, Union
import asyncio
import logging
import json
from uuid import UUID

from ...datamodel import Run, RunStatus, TeamResult
from ...database import DatabaseManager
from autogen_core.base import CancellationToken
from autogen_agentchat.messages import InnerMessage, ChatMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, db_manager: DatabaseManager, cleanup_interval: int = 300):  # 5 min cleanup
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.cancellation_tokens: Dict[UUID, CancellationToken] = {}
        self.db_manager = db_manager
        self._lock = asyncio.Lock()
        self.cleanup_interval = cleanup_interval

        # Store the cleanup task reference
        self.cleanup_task = asyncio.create_task(self._cleanup_stale_runs())

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

            # Cleanup cancellation token if exists
            if run_id in self.cancellation_tokens:
                self.cancellation_tokens[run_id].cancel()
                del self.cancellation_tokens[run_id]

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

    async def start_streaming_task(
        self,
        run_id: UUID,
        team_manager,  # TeamManager instance
        task: str,
        team_config: dict
    ) -> None:
        """Start a streaming task and send updates via WebSocket"""
        # Create cancellation token for this run
        cancellation_token = CancellationToken()
        self.cancellation_tokens[run_id] = cancellation_token

        try:
            async for message in team_manager.run_stream(
                task=task,
                team_config=team_config,
                cancellation_token=cancellation_token
            ):
                if not await self._stream_message(run_id, message):
                    break  # Stop if we can't send messages

            await self.complete_run(run_id)

        except asyncio.CancelledError:
            await self.complete_run(run_id, error="Task cancelled by user")
        except Exception as e:
            logger.error(f"Task error for run {run_id}: {str(e)}")
            await self.complete_run(run_id, error=str(e))
        finally:
            if run_id in self.cancellation_tokens:
                del self.cancellation_tokens[run_id]

    async def _stream_message(
        self,
        run_id: UUID,
        message: Union[InnerMessage, ChatMessage, TeamResult]
    ) -> bool:
        """Format and send a streaming message"""
        try:
            if isinstance(message, (InnerMessage, ChatMessage)):
                payload = {
                    "type": "StreamEvent",
                    "event_type": "message",
                    "data": {
                        "role": message.role if hasattr(message, 'role') else "system",
                        "content": message.content,
                        "name": message.name if hasattr(message, 'name') else None
                    }
                }
            elif isinstance(message, TeamResult):
                payload = {
                    "type": "StreamEvent",
                    "event_type": "completion",
                    "data": {
                        "duration": message.duration,
                        "usage": message.usage,
                        "final_message": message.task_result.messages[-1].content
                            if message.task_result.messages else None
                    }
                }
            else:
                logger.warning(
                    f"Unknown message type for run {run_id}: {type(message)}")
                return True  # Continue streaming even if we don't understand a message

            return await self.send_message(run_id, json.dumps(payload))

        except Exception as e:
            logger.error(f"Error streaming message for run {run_id}: {str(e)}")
            return False

    async def cancel_run(self, run_id: UUID) -> None:
        """Cancel a running task"""
        if run_id in self.cancellation_tokens:
            self.cancellation_tokens[run_id].cancel()

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

                # Send completion/error message to client
                completion_message = {
                    "type": "TerminationEvent",
                    "reason": "cancelled" if error == "Task cancelled by user" else "error" if error else "complete",
                    "error": error
                }
                await self.send_message(run_id, json.dumps(completion_message))

            # Cancel task if still running
            if run_id in self.cancellation_tokens:
                self.cancellation_tokens[run_id].cancel()
                del self.cancellation_tokens[run_id]

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

                    # Cleanup disconnected websockets and cancellation tokens
                    disconnected_runs = [
                        run_id for run_id, ws in self.active_connections.items()
                        if ws.client_state.DISCONNECTED
                    ]
                    for run_id in disconnected_runs:
                        await self.complete_run(run_id, error="Connection lost")

            except Exception as e:
                logger.error(f"Error in run cleanup: {str(e)}")

            await asyncio.sleep(self.cleanup_interval)

    async def cleanup(self) -> None:
        """Cleanup all manager resources during shutdown"""
        logger.info("Starting ConnectionManager cleanup...")

        try:
            # Cancel the background cleanup task
            if hasattr(self, 'cleanup_task'):
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass

            # Close all active connections and mark runs as ERROR
            async with self._lock:
                for run_id in list(self.active_connections.keys()):
                    await self.complete_run(run_id, error="Server shutdown")

                self.active_connections.clear()
                self.cancellation_tokens.clear()

            logger.info("ConnectionManager cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during connection manager cleanup: {str(e)}")
            raise  # Re-raise to let caller handle it
