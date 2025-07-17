import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import WebSocket
from loguru import logger
from mcp import ClientSession
from mcp.types import ElicitResult, ErrorData

from .client import MCPClient, MCPEventHandler
from .utils import extract_real_error, is_websocket_disconnect, serialize_for_json


class MCPWebSocketBridge(MCPEventHandler):
    """Bridges WebSocket connections to MCP operations"""

    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.mcp_client: Optional[MCPClient] = None
        self.pending_elicitations: Dict[str, asyncio.Future[ElicitResult | ErrorData]] = {}
        self._running = True

    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message through the WebSocket"""
        try:
            from fastapi.websockets import WebSocketState

            if self.websocket.client_state == WebSocketState.CONNECTED:
                serialized_message = serialize_for_json(message)
                await self.websocket.send_json(serialized_message)
        except Exception as e:
            real_error = extract_real_error(e)
            logger.error(f"Error sending WebSocket message: {real_error}")

    # Implement MCPEventHandler interface
    async def on_initialized(self, session_id: str, capabilities: Any) -> None:
        await self.send_message(
            {
                "type": "initialized",
                "session_id": session_id,
                "capabilities": capabilities,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def on_operation_result(self, operation: str, data: Dict[str, Any]) -> None:
        await self.send_message(
            {
                "type": "operation_result",
                "operation": operation,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def on_operation_error(self, operation: str, error: str) -> None:
        await self.send_message(
            {
                "type": "operation_error",
                "operation": operation,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def on_mcp_activity(self, activity_type: str, message: str, details: Dict[str, Any]) -> None:
        await self.send_message(
            {
                "type": "mcp_activity",
                "activity_type": activity_type,
                "message": message,
                "details": details,
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def on_elicitation_request(self, request_id: str, message: str, requested_schema: Any) -> None:
        await self.send_message(
            {
                "type": "elicitation_request",
                "request_id": request_id,
                "message": message,
                "requestedSchema": requested_schema,
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def set_mcp_client(self, mcp_client: MCPClient) -> None:
        """Set the MCP client after initialization"""
        self.mcp_client = mcp_client

    async def handle_websocket_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages"""
        message_type = message.get("type")

        # Update last activity for session tracking
        from datetime import datetime, timezone

        from ..web.routes.mcp import active_sessions

        if self.session_id in active_sessions:
            active_sessions[self.session_id]["last_activity"] = datetime.now(timezone.utc)

        if message_type == "operation":
            # CRITICAL: Run in background task to avoid blocking message loop
            # This preserves the exact behavior from the original code
            if self.mcp_client:
                asyncio.create_task(self.mcp_client.handle_operation(message))
            else:
                await self.send_message(
                    {
                        "type": "error",
                        "error": "MCP client not initialized",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        elif message_type == "ping":
            await self.send_message({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

        elif message_type == "elicitation_response":
            await self._handle_elicitation_response(message)

        else:
            await self.send_message(
                {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    async def _handle_elicitation_response(self, message: Dict[str, Any]) -> None:
        """Handle user response to elicitation request"""
        request_id = message.get("request_id")

        if not request_id:
            await self.send_message(
                {
                    "type": "error",
                    "error": "Missing request_id in elicitation response",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return

        if request_id in self.pending_elicitations:
            try:
                action = message.get("action", "cancel")
                data = message.get("data", {})

                if action == "accept":
                    result = ElicitResult(action="accept", content=data)
                elif action == "decline":
                    result = ElicitResult(action="decline")
                else:
                    result = ElicitResult(action="cancel")

                future = self.pending_elicitations[request_id]
                if not future.done():
                    future.set_result(result)
                else:
                    logger.warning(f"Future for elicitation request {request_id} was already done")

            except Exception as e:
                error_msg = extract_real_error(e)
                logger.error(f"Error processing elicitation response: {error_msg}")

                future = self.pending_elicitations.get(request_id)
                if future and not future.done():
                    future.set_result(
                        ErrorData(code=-32603, message=f"Error processing elicitation response: {error_msg}")
                    )
        else:
            logger.warning(f"Unknown elicitation request_id: {request_id}")
            await self.send_message(
                {
                    "type": "operation_error",
                    "error": f"Unknown elicitation request_id: {request_id}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    async def run(self) -> None:
        """Main message loop"""
        try:
            while self._running:
                try:
                    raw_message = await self.websocket.receive_text()
                    message = json.loads(raw_message)
                    await self.handle_websocket_message(message)

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from session {self.session_id}")
                    await self.send_message(
                        {
                            "type": "error",
                            "error": "Invalid message format",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        except Exception as e:
            if not is_websocket_disconnect(e):
                real_error = extract_real_error(e)
                logger.error(f"Error in message loop: {real_error}")
                raise

    def stop(self) -> None:
        """Stop the bridge"""
        self._running = False
