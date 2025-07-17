import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from autogen_ext.tools.mcp._config import (
    McpServerParams,
    SseServerParams,
    StdioServerParams,
    StreamableHttpServerParams,
)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from pydantic import BaseModel

from ...mcp.callbacks import (
    create_elicitation_callback,
    create_message_handler,
    create_sampling_callback,
)
from ...mcp.client import MCPClient
from ...mcp.utils import extract_real_error, is_websocket_disconnect, serialize_for_json
from ...mcp.wsbridge import MCPWebSocketBridge

router = APIRouter()

# Global session tracking for status endpoint
active_sessions: Dict[str, Dict[str, Any]] = {}


class CreateWebSocketConnectionRequest(BaseModel):
    server_params: McpServerParams


async def create_mcp_session(bridge: MCPWebSocketBridge, server_params: McpServerParams, session_id: str):
    """Create MCP session based on server parameters"""

    # Create callbacks using the bridge
    message_handler = create_message_handler(bridge)
    sampling_callback = create_sampling_callback(bridge)
    elicitation_callback, _ = create_elicitation_callback(bridge)

    if isinstance(server_params, StdioServerParams):
        stdio_params = StdioServerParameters(
            command=server_params.command, args=server_params.args, env=server_params.env
        )
        async with stdio_client(stdio_params) as (read, write):
            async with ClientSession(
                read,
                write,
                message_handler=message_handler,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
            ) as session:
                mcp_client = MCPClient(session, session_id, bridge)
                bridge.set_mcp_client(mcp_client)

                # Initialize and run
                await mcp_client.initialize()

                # Store session info
                active_sessions[session_id] = {
                    "created_at": datetime.now(timezone.utc),
                    "last_activity": datetime.now(timezone.utc),
                    "capabilities": serialize_for_json(mcp_client.capabilities.model_dump())
                    if mcp_client.capabilities
                    else None,
                }

                # Run the bridge message loop
                await bridge.run()

    elif isinstance(server_params, SseServerParams):
        async with sse_client(server_params.url) as (read, write):
            async with ClientSession(
                read,
                write,
                message_handler=message_handler,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
            ) as session:
                mcp_client = MCPClient(session, session_id, bridge)
                bridge.set_mcp_client(mcp_client)

                await mcp_client.initialize()

                active_sessions[session_id] = {
                    "created_at": datetime.now(timezone.utc),
                    "last_activity": datetime.now(timezone.utc),
                    "capabilities": serialize_for_json(mcp_client.capabilities.model_dump())
                    if mcp_client.capabilities
                    else None,
                }

                await bridge.run()

    elif isinstance(server_params, StreamableHttpServerParams):
        async with streamablehttp_client(server_params.url) as (read, write, _):
            async with ClientSession(
                read,
                write,
                message_handler=message_handler,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
            ) as session:
                mcp_client = MCPClient(session, session_id, bridge)
                bridge.set_mcp_client(mcp_client)

                await mcp_client.initialize()

                active_sessions[session_id] = {
                    "created_at": datetime.now(timezone.utc),
                    "last_activity": datetime.now(timezone.utc),
                    "capabilities": serialize_for_json(mcp_client.capabilities.model_dump())
                    if mcp_client.capabilities
                    else None,
                }

                await bridge.run()

    else:
        raise ValueError(f"Unsupported server params type: {type(server_params)}")


@router.websocket("/ws/{session_id}")
async def mcp_websocket(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint - now a thin layer"""
    await websocket.accept()
    logger.info(f"MCP WebSocket connection established for session {session_id}")

    bridge = None

    try:
        # Parse server parameters
        query_params = dict(websocket.query_params)
        server_params_encoded = query_params.get("server_params")

        if not server_params_encoded:
            await websocket.close(code=4000, reason="Missing server_params")
            return

        decoded_params = base64.b64decode(server_params_encoded).decode("utf-8")
        server_params_dict = json.loads(decoded_params)

        # Create appropriate server params object
        if server_params_dict.get("type") == "StdioServerParams":
            server_params = StdioServerParams(**server_params_dict)
        elif server_params_dict.get("type") == "SseServerParams":
            server_params = SseServerParams(**server_params_dict)
        elif server_params_dict.get("type") == "StreamableHttpServerParams":
            server_params = StreamableHttpServerParams(**server_params_dict)
        else:
            await websocket.close(code=4000, reason="Invalid server parameters")
            return

        # Create bridge and run MCP session
        bridge = MCPWebSocketBridge(websocket, session_id)
        await create_mcp_session(bridge, server_params, session_id)

    except WebSocketDisconnect:
        logger.info(f"MCP WebSocket session {session_id} disconnected normally")
    except Exception as e:
        real_error = extract_real_error(e)

        if is_websocket_disconnect(e):
            logger.info(f"MCP WebSocket session {session_id} disconnected (wrapped)")
        else:
            logger.error(f"MCP WebSocket error for session {session_id}: {real_error}")

            if bridge and not is_websocket_disconnect(e):
                try:
                    await bridge.send_message(
                        {
                            "type": "error",
                            "error": f"Connection error: {real_error}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except Exception:
                    pass
    finally:
        # Cleanup
        if session_id in active_sessions:
            session_info = active_sessions.pop(session_id, None)
            if session_info:
                duration = datetime.now(timezone.utc) - session_info["created_at"]
                logger.info(f"MCP session {session_id} ended after {duration.total_seconds():.2f} seconds")

        if bridge:
            bridge.stop()


@router.post("/ws/connect")
async def create_mcp_websocket_connection(request: CreateWebSocketConnectionRequest):
    """Create WebSocket connection URL"""
    try:
        session_id = str(uuid.uuid4())

        server_params_json = json.dumps(serialize_for_json(request.server_params.model_dump()))
        server_params_encoded = base64.b64encode(server_params_json.encode("utf-8")).decode("utf-8")

        return {
            "status": True,
            "message": "WebSocket connection URL created",
            "session_id": session_id,
            "websocket_url": f"/api/mcp/ws/{session_id}?server_params={server_params_encoded}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        real_error = extract_real_error(e)
        logger.error(f"Error creating WebSocket connection: {real_error}")
        return {"status": False, "message": "An internal error occurred while creating the WebSocket connection."}


@router.get("/ws/status/{session_id}")
async def get_mcp_session_status(session_id: str):
    """Get MCP session status"""
    session_info = active_sessions.get(session_id)

    if not session_info:
        return {"status": False, "message": "Session not found", "session_id": session_id}

    # Update last activity
    active_sessions[session_id]["last_activity"] = datetime.now(timezone.utc)

    return {
        "status": True,
        "message": "Session active",
        "session_id": session_id,
        "connected": True,
        "capabilities": session_info.get("capabilities"),
        "created_at": session_info["created_at"].isoformat(),
        "last_activity": session_info["last_activity"].isoformat(),
    }
