import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from loguru import logger
from mcp.shared.context import RequestContext
from mcp.shared.session import RequestResponder
from mcp.types import (
    ClientResult,
    CreateMessageRequestParams,
    CreateMessageResult,
    ElicitRequestParams,
    ElicitResult,
    ErrorData,
    ServerNotification,
    ServerRequest,
    TextContent,
)

from .utils import extract_real_error, serialize_for_json
from .wsbridge import MCPWebSocketBridge


def create_message_handler(bridge: MCPWebSocketBridge):
    """Create a message handler callback that streams MCP protocol messages to the UI"""

    async def message_handler(
        message: RequestResponder[ServerRequest, ClientResult] | ServerNotification | Exception,
    ) -> None:
        try:
            if isinstance(message, Exception):
                await bridge.on_mcp_activity(
                    "error", f"Protocol error: {str(message)}", {"details": extract_real_error(message)}
                )

            elif hasattr(message, "method"):
                method = getattr(message, "method", "unknown")
                params = getattr(message, "params", None)

                await bridge.on_mcp_activity(
                    "protocol",
                    f"MCP {method}",
                    {
                        "method": method,
                        "params": serialize_for_json(params) if params else None,
                        "message_type": type(message).__name__,
                    },
                )

            else:
                await bridge.on_mcp_activity(
                    "protocol",
                    f"{type(message).__name__}",
                    {
                        "message_type": type(message).__name__,
                        "content": serialize_for_json(message) if hasattr(message, "model_dump") else str(message),
                    },
                )

        except Exception as e:
            logger.error(f"Error in message handler: {extract_real_error(e)}")

    return message_handler


def create_sampling_callback(bridge: MCPWebSocketBridge):
    """Create a sampling callback that handles AI sampling requests from tools"""

    async def sampling_callback(
        context: RequestContext[Any, Any, Any],
        params: CreateMessageRequestParams,
    ) -> CreateMessageResult | ErrorData:
        try:
            request_id = str(uuid.uuid4())

            await bridge.on_mcp_activity(
                "sampling",
                f"Tool requested AI sampling for {len(params.messages)} message(s)",
                {
                    "request_id": request_id,
                    "params": serialize_for_json(params.model_dump()),
                    "context": "Tool is requesting AI to generate a response",
                },
            )

            dummy_response = CreateMessageResult(
                role="assistant",
                content=TextContent(
                    type="text",
                    text="[AutoGen Studio Default Sampling Response - This is a placeholder response for AI sampling requests. In a production setup, this would be handled by your configured LLM.]",
                ),
                model="autogen-studio-default",
            )

            await bridge.on_mcp_activity(
                "sampling",
                "Provided default sampling response to tool",
                {
                    "request_id": request_id,
                    "response": serialize_for_json(dummy_response.model_dump()),
                    "note": "This is a placeholder response - configure an LLM for real sampling",
                },
            )

            logger.info("Handled sampling request with default response")
            return dummy_response

        except Exception as e:
            error_msg = extract_real_error(e)
            logger.error(f"Error in sampling callback: {error_msg}")

            await bridge.on_mcp_activity("error", f"Sampling callback error: {error_msg}", {"error": error_msg})

            return ErrorData(code=-32603, message=f"Sampling failed: {error_msg}")

    return sampling_callback


def create_elicitation_callback(
    bridge: MCPWebSocketBridge,
) -> Tuple[Any, Dict[str, asyncio.Future[ElicitResult | ErrorData]]]:
    """Create an elicitation callback that handles user input requests from tools"""

    async def elicitation_callback(
        context: RequestContext[Any, Any, Any],
        params: ElicitRequestParams,
    ) -> ElicitResult | ErrorData:
        try:
            request_id = str(uuid.uuid4())

            await bridge.on_mcp_activity(
                "elicitation",
                f"Tool requesting user input: {params.message}",
                {
                    "request_id": request_id,
                    "message": params.message,
                    "requestedSchema": serialize_for_json(params.requestedSchema) if params.requestedSchema else None,
                    "context": "Tool is requesting additional information from user",
                },
            )

            await bridge.on_elicitation_request(
                request_id,
                params.message,
                serialize_for_json(params.requestedSchema) if params.requestedSchema else None,
            )

            response_future: asyncio.Future[ElicitResult | ErrorData] = asyncio.Future()
            bridge.pending_elicitations[request_id] = response_future

            try:
                user_response = await asyncio.wait_for(response_future, timeout=60.0)

                await bridge.on_mcp_activity(
                    "elicitation",
                    "User responded to elicitation request",
                    {"request_id": request_id, "response": serialize_for_json(user_response), "status": "completed"},
                )

                return user_response

            except asyncio.TimeoutError:
                logger.warning(f"User did not respond to elicitation request {request_id} within 60 seconds")
                error_msg = "User did not respond to elicitation request within 60 seconds"

                await bridge.on_mcp_activity(
                    "error",
                    f"Elicitation timeout: {error_msg}",
                    {"request_id": request_id, "error": error_msg, "timeout": 60},
                )

                return ErrorData(code=-32603, message=error_msg)

            finally:
                bridge.pending_elicitations.pop(request_id, None)

        except Exception as e:
            error_msg = extract_real_error(e)
            logger.error(f"Error in elicitation callback: {error_msg}")

            await bridge.on_mcp_activity("error", f"Elicitation callback error: {error_msg}", {"error": error_msg})

            return ErrorData(code=-32603, message=f"Elicitation failed: {error_msg}")

    return elicitation_callback, bridge.pending_elicitations
