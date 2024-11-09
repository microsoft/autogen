# managers/connection.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional, Any
from uuid import UUID
import logging
from datetime import datetime, timezone

from ...datamodel import Run, RunStatus, TeamResult
from ...database import DatabaseManager
from autogen_agentchat.messages import InnerMessage, ChatMessage
from autogen_core.base import CancellationToken

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message streaming for team task execution"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._connections: Dict[UUID, WebSocket] = {}
        self._cancellation_tokens: Dict[UUID, CancellationToken] = {}

    async def connect(self, websocket: WebSocket, run_id: UUID) -> bool:
        """Initialize WebSocket connection for a run

        Args:
            websocket: The WebSocket connection to initialize
            run_id: UUID of the run to associate with this connection

        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            await websocket.accept()
            self._connections[run_id] = websocket

            run = await self._get_run(run_id)
            if run:
                run.status = RunStatus.ACTIVE
                self.db_manager.upsert(run)

            await self._send_message(run_id, {
                "type": "system",
                "status": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return True

        except Exception as e:
            logger.error(f"Connection error for run {run_id}: {e}")
            return False

    async def start_stream(
        self,
        run_id: UUID,
        team_manager: Any,
        task: str,
        team_config: dict
    ) -> None:
        """Start streaming task execution

        Args:
            run_id: UUID of the run
            team_manager: Instance of the team manager
            task: Task string to execute
            team_config: Team configuration dictionary
        """
        if run_id not in self._connections:
            raise ValueError(f"No active connection for run {run_id}")

        cancellation_token = CancellationToken()
        self._cancellation_tokens[run_id] = cancellation_token

        try:
            async for message in team_manager.run_stream(
                task=task,
                team_config=team_config,
                cancellation_token=cancellation_token
            ):

                if cancellation_token.is_cancelled():
                    logger.info(f"Stream cancelled for run {run_id}")
                    break

                formatted_message = self._format_message(message)
                if formatted_message:
                    await self._send_message(run_id, formatted_message)

            # Only send completion if not cancelled
            if not cancellation_token.is_cancelled():
                # await self._send_message(run_id, {
                #     "type": "completion",
                #     "status": "complete",
                #     "timestamp": datetime.now(timezone.utc).isoformat()
                # })
                await self._update_run_status(run_id, RunStatus.COMPLETE)
            else:
                await self._send_message(run_id, {
                    "type": "completion",
                    "status": "cancelled",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                await self._update_run_status(run_id, RunStatus.STOPPED)

        except Exception as e:
            logger.error(f"Stream error for run {run_id}: {e}")
            await self._handle_stream_error(run_id, e)

        finally:
            self._cancellation_tokens.pop(run_id, None)

    async def stop_run(self, run_id: UUID) -> None:
        """Stop a running task"""
        if run_id in self._cancellation_tokens:
            logger.info(f"Stopping run {run_id}")
            self._cancellation_tokens[run_id].cancel()

            # Send final message if connection still exists
            if run_id in self._connections:
                try:
                    await self._send_message(run_id, {
                        "type": "completion",
                        "status": "cancelled",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    pass

    async def disconnect(self, run_id: UUID) -> None:
        """Clean up connection and associated resources"""
        logger.info(f"Disconnecting run {run_id}")

        # First cancel any running tasks
        await self.stop_run(run_id)

        # Then clean up resources without trying to close the socket again
        if run_id in self._connections:
            self._connections.pop(run_id, None)
            self._cancellation_tokens.pop(run_id, None)

    async def _send_message(self, run_id: UUID, message: dict) -> None:
        """Send a message through the WebSocket

        Args:
            run_id: UUID of the run
            message: Message dictionary to send
        """
        try:
            if run_id in self._connections:
                await self._connections[run_id].send_json(message)
        except WebSocketDisconnect:
            logger.warning(
                f"WebSocket disconnected while sending message for run {run_id}")
            await self.disconnect(run_id)
        except Exception as e:
            logger.error(f"Error sending message for run {run_id}: {e}")
            await self._handle_stream_error(run_id, e)

    async def _handle_stream_error(self, run_id: UUID, error: Exception) -> None:
        """Handle stream errors consistently

        Args:
            run_id: UUID of the run
            error: Exception that occurred
        """
        try:
            await self._send_message(run_id, {
                "type": "completion",
                "status": "error",
                "error": str(error),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as send_error:
            logger.error(
                f"Failed to send error message for run {run_id}: {send_error}")

        await self._update_run_status(run_id, RunStatus.ERROR, str(error))

    def _format_message(self, message: Any) -> Optional[dict]:
        """Format message for WebSocket transmission

        Args:
            message: Message to format

        Returns:
            Optional[dict]: Formatted message or None if formatting fails
        """
        try:
            if isinstance(message, (InnerMessage, ChatMessage)):
                return {
                    "type": "message",
                    "data": message.model_dump()
                }
            elif isinstance(message, TeamResult):
                return {
                    "type": "result",
                    "data": message.model_dump(),
                    "status": "complete",
                }
            return None
        except Exception as e:
            logger.error(f"Message formatting error: {e}")
            return None

    async def _get_run(self, run_id: UUID) -> Optional[Run]:
        """Get run from database

        Args:
            run_id: UUID of the run to retrieve

        Returns:
            Optional[Run]: Run object if found, None otherwise
        """
        response = self.db_manager.get(
            Run, filters={"id": run_id}, return_json=False)
        return response.data[0] if response.status and response.data else None

    async def _update_run_status(
        self,
        run_id: UUID,
        status: RunStatus,
        error: Optional[str] = None
    ) -> None:
        """Update run status in database

        Args:
            run_id: UUID of the run to update
            status: New status to set
            error: Optional error message
        """
        run = await self._get_run(run_id)
        if run:
            run.status = status
            run.error_message = error
            self.db_manager.upsert(run)

    @property
    def active_connections(self) -> set[UUID]:
        """Get set of active run IDs"""
        return set(self._connections.keys())

    @property
    def active_runs(self) -> set[UUID]:
        """Get set of runs with active cancellation tokens"""
        return set(self._cancellation_tokens.keys())
