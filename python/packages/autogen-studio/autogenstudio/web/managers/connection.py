import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Union
from uuid import UUID

from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.messages import AgentMessage, ChatMessage, MultiModalMessage, TextMessage
from autogen_core import CancellationToken
from autogen_core import Image as AGImage
from fastapi import WebSocket, WebSocketDisconnect

from ...database import DatabaseManager
from ...datamodel import Message, MessageConfig, Run, RunStatus, TeamResult
from ...teammanager import TeamManager

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message streaming for team task execution"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._connections: Dict[UUID, WebSocket] = {}
        self._cancellation_tokens: Dict[UUID, CancellationToken] = {}
        # Track explicitly closed connections
        self._closed_connections: set[UUID] = set()
        self._input_responses: Dict[UUID, asyncio.Queue] = {}

        self._cancel_message = TeamResult(
            task_result=TaskResult(
                messages=[TextMessage(source="user", content="Run cancelled by user")], stop_reason="cancelled by user"
            ),
            usage="",
            duration=0,
        ).model_dump()

    def _get_stop_message(self, reason: str) -> dict:
        return TeamResult(
            task_result=TaskResult(messages=[TextMessage(source="user", content=reason)], stop_reason=reason),
            usage="",
            duration=0,
        ).model_dump()

    async def connect(self, websocket: WebSocket, run_id: UUID) -> bool:
        try:
            await websocket.accept()
            self._connections[run_id] = websocket
            self._closed_connections.discard(run_id)
            # Initialize input queue for this connection
            self._input_responses[run_id] = asyncio.Queue()

            await self._send_message(
                run_id, {"type": "system", "status": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
            )

            return True
        except Exception as e:
            logger.error(f"Connection error for run {run_id}: {e}")
            return False

    async def start_stream(self, run_id: UUID, task: str, team_config: dict) -> None:
        """Start streaming task execution with proper run management"""
        if run_id not in self._connections or run_id in self._closed_connections:
            raise ValueError(f"No active connection for run {run_id}")

        team_manager = TeamManager()
        cancellation_token = CancellationToken()
        self._cancellation_tokens[run_id] = cancellation_token
        final_result = None

        try:
            # Update run with task and status
            run = await self._get_run(run_id)
            if run:
                run.task = MessageConfig(content=task, source="user").model_dump()
                run.status = RunStatus.ACTIVE
                self.db_manager.upsert(run)

            input_func = self.create_input_func(run_id)

            async for message in team_manager.run_stream(
                task=task, team_config=team_config, input_func=input_func, cancellation_token=cancellation_token
            ):
                if cancellation_token.is_cancelled() or run_id in self._closed_connections:
                    logger.info(f"Stream cancelled or connection closed for run {run_id}")
                    break

                formatted_message = self._format_message(message)
                if formatted_message:
                    await self._send_message(run_id, formatted_message)

                    # Save message if it's a content message
                    if isinstance(message, (AgentMessage, ChatMessage)):
                        await self._save_message(run_id, message)
                    # Capture final result if it's a TeamResult
                    elif isinstance(message, TeamResult):
                        final_result = message.model_dump()

            if not cancellation_token.is_cancelled() and run_id not in self._closed_connections:
                if final_result:
                    await self._update_run(run_id, RunStatus.COMPLETE, team_result=final_result)
                else:
                    logger.warning(f"No final result captured for completed run {run_id}")
                    await self._update_run_status(run_id, RunStatus.COMPLETE)
            else:
                await self._send_message(
                    run_id,
                    {
                        "type": "completion",
                        "status": "cancelled",
                        "data": self._cancel_message,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                # Update run with cancellation result
                await self._update_run(run_id, RunStatus.STOPPED, team_result=self._cancel_message)

        except Exception as e:
            logger.error(f"Stream error for run {run_id}: {e}")
            await self._handle_stream_error(run_id, e)
        finally:
            self._cancellation_tokens.pop(run_id, None)

    async def _save_message(self, run_id: UUID, message: Union[AgentMessage, ChatMessage]) -> None:
        """Save a message to the database"""
        run = await self._get_run(run_id)
        if run:
            db_message = Message(
                session_id=run.session_id,
                run_id=run_id,
                config=message.model_dump(),
                user_id=None,  # You might want to pass this from somewhere
            )
            self.db_manager.upsert(db_message)

    async def _update_run(
        self, run_id: UUID, status: RunStatus, team_result: Optional[dict] = None, error: Optional[str] = None
    ) -> None:
        """Update run status and result"""
        run = await self._get_run(run_id)
        if run:
            run.status = status
            if team_result:
                run.team_result = team_result
            if error:
                run.error_message = error
            self.db_manager.upsert(run)

    def create_input_func(self, run_id: UUID) -> Callable:
        """Creates an input function for a specific run"""

        async def input_handler(prompt: str = "", cancellation_token: Optional[CancellationToken] = None) -> str:
            try:
                # Send input request to client
                await self._send_message(
                    run_id,
                    {
                        "type": "input_request",
                        "prompt": prompt,
                        "data": {"source": "system", "content": prompt},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                # Wait for response
                if run_id in self._input_responses:
                    response = await self._input_responses[run_id].get()
                    return response
                else:
                    raise ValueError(f"No input queue for run {run_id}")

            except Exception as e:
                logger.error(f"Error handling input for run {run_id}: {e}")
                raise

        return input_handler

    async def handle_input_response(self, run_id: UUID, response: str) -> None:
        """Handle input response from client"""
        if run_id in self._input_responses:
            await self._input_responses[run_id].put(response)
        else:
            logger.warning(f"Received input response for inactive run {run_id}")

    async def stop_run(self, run_id: UUID, reason: str) -> None:
        if run_id in self._cancellation_tokens:
            logger.info(f"Stopping run {run_id}")

            stop_message = self._get_stop_message(reason)

            try:
                # Update run record first
                await self._update_run(run_id, status=RunStatus.STOPPED, team_result=stop_message)

                # Then handle websocket communication if connection is active
                if run_id in self._connections and run_id not in self._closed_connections:
                    await self._send_message(
                        run_id,
                        {
                            "type": "completion",
                            "status": "cancelled",
                            "data": stop_message,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                # Finally cancel the token
                self._cancellation_tokens[run_id].cancel()

            except Exception as e:
                logger.error(f"Error stopping run {run_id}: {e}")
                # We might want to force disconnect here if db update failed
                # await self.disconnect(run_id)  # Optional

    async def disconnect(self, run_id: UUID) -> None:
        """Clean up connection and associated resources"""
        logger.info(f"Disconnecting run {run_id}")

        # Mark as closed before cleanup to prevent any new messages
        self._closed_connections.add(run_id)

        # Cancel any running tasks
        await self.stop_run(run_id, "Connection closed")

        # Clean up resources
        self._connections.pop(run_id, None)
        self._cancellation_tokens.pop(run_id, None)
        self._input_responses.pop(run_id, None)

    async def _send_message(self, run_id: UUID, message: dict) -> None:
        """Send a message through the WebSocket with connection state checking

        Args:
            run_id: UUID of the run
            message: Message dictionary to send
        """
        if run_id in self._closed_connections:
            logger.warning(f"Attempted to send message to closed connection for run {run_id}")
            return

        try:
            if run_id in self._connections:
                websocket = self._connections[run_id]
                await websocket.send_json(message)
        except WebSocketDisconnect:
            logger.warning(f"WebSocket disconnected while sending message for run {run_id}")
            await self.disconnect(run_id)
        except Exception as e:
            logger.error(f"Error sending message for run {run_id}: {e}, {message}")
            # Don't try to send error message here to avoid potential recursive loop
            await self._update_run_status(run_id, RunStatus.ERROR, str(e))
            await self.disconnect(run_id)

    async def _handle_stream_error(self, run_id: UUID, error: Exception) -> None:
        """Handle stream errors with proper run updates"""
        if run_id not in self._closed_connections:
            error_result = TeamResult(
                task_result=TaskResult(
                    messages=[TextMessage(source="system", content=str(error))], stop_reason="error"
                ),
                usage="",
                duration=0,
            ).model_dump()

            await self._send_message(
                run_id,
                {
                    "type": "completion",
                    "status": "error",
                    "data": error_result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await self._update_run(run_id, RunStatus.ERROR, team_result=error_result, error=str(error))

    def _format_message(self, message: Any) -> Optional[dict]:
        """Format message for WebSocket transmission

        Args:
            message: Message to format

        Returns:
            Optional[dict]: Formatted message or None if formatting fails
        """
        try:
            if isinstance(message, MultiModalMessage):
                message_dump = message.model_dump()
                message_dump["content"] = [
                    message_dump["content"][0],
                    {
                        "url": f"data:image/png;base64,{message_dump['content'][1]['data']}",
                        "alt": "WebSurfer Screenshot",
                    },
                ]
                return {"type": "message", "data": message_dump}
            elif isinstance(message, (AgentMessage, ChatMessage)):
                return {"type": "message", "data": message.model_dump()}

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
        response = self.db_manager.get(Run, filters={"id": run_id}, return_json=False)
        return response.data[0] if response.status and response.data else None

    async def _update_run_status(self, run_id: UUID, status: RunStatus, error: Optional[str] = None) -> None:
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

    async def cleanup(self) -> None:
        """Clean up all active connections and resources when server is shutting down"""
        logger.info(f"Cleaning up {len(self.active_connections)} active connections")

        try:
            # First cancel all running tasks
            for run_id in self.active_runs.copy():
                if run_id in self._cancellation_tokens:
                    self._cancellation_tokens[run_id].cancel()
                run = await self._get_run(run_id)
                if run and run.status == RunStatus.ACTIVE:
                    interrupted_result = TeamResult(
                        task_result=TaskResult(
                            messages=[TextMessage(source="system", content="Run interrupted by server shutdown")],
                            stop_reason="server_shutdown",
                        ),
                        usage="",
                        duration=0,
                    ).model_dump()

                    run.status = RunStatus.STOPPED
                    run.team_result = interrupted_result
                    self.db_manager.upsert(run)

            # Then disconnect all websockets with timeout
            # 10 second timeout for entire cleanup
            async with asyncio.timeout(10):
                for run_id in self.active_connections.copy():
                    try:
                        # Give each disconnect operation 2 seconds
                        async with asyncio.timeout(2):
                            await self.disconnect(run_id)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout disconnecting run {run_id}")
                    except Exception as e:
                        logger.error(f"Error disconnecting run {run_id}: {e}")

        except asyncio.TimeoutError:
            logger.warning("WebSocketManager cleanup timed out")
        except Exception as e:
            logger.error(f"Error during WebSocketManager cleanup: {e}")
        finally:
            # Always clear internal state, even if cleanup had errors
            self._connections.clear()
            self._cancellation_tokens.clear()
            self._closed_connections.clear()
            self._input_responses.clear()

    @property
    def active_connections(self) -> set[UUID]:
        """Get set of active run IDs"""
        return set(self._connections.keys()) - self._closed_connections

    @property
    def active_runs(self) -> set[UUID]:
        """Get set of runs with active cancellation tokens"""
        return set(self._cancellation_tokens.keys())
