import datetime
from enum import Enum
from typing import Any, List

from fastapi import WebSocketDisconnect
from pydantic.networks import AnyUrl


class McpOperationError(Exception):
    """Raised when MCP operation fails"""

    pass


def extract_real_error(e: Exception) -> str:
    """Extract the real error message from potentially wrapped exceptions"""
    error_parts: List[str] = []

    # Handle ExceptionGroup (Python 3.11+)
    if hasattr(e, "exceptions") and getattr(e, "exceptions", None):
        exceptions_list = getattr(e, "exceptions", [])
        for sub_exc in exceptions_list:
            error_parts.append(f"{type(sub_exc).__name__}: {str(sub_exc)}")

    # Handle chained exceptions
    elif hasattr(e, "__cause__") and e.__cause__:
        current = e
        while current:
            error_parts.append(f"{type(current).__name__}: {str(current)}")
            current = getattr(current, "__cause__", None)

    # Handle context exceptions
    elif hasattr(e, "__context__") and e.__context__:
        error_parts.append(f"Context: {type(e.__context__).__name__}: {str(e.__context__)}")
        error_parts.append(f"Error: {type(e).__name__}: {str(e)}")

    # Default case
    else:
        error_parts.append(f"{type(e).__name__}: {str(e)}")

    return " | ".join(error_parts)


def serialize_for_json(obj: Any) -> Any:
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, AnyUrl):
        return str(obj)
    elif isinstance(obj, datetime.datetime):  # Fixed: use datetime.datetime class
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {str(k): serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif hasattr(obj, "model_dump"):
        return serialize_for_json(obj.model_dump())
    else:
        return obj


def is_websocket_disconnect(e: Exception) -> bool:
    """Check if an exception (potentially nested) is a WebSocket disconnect"""

    def check_exception(exc: BaseException) -> bool:
        if isinstance(exc, WebSocketDisconnect):
            return True

        exc_name = type(exc).__name__
        exc_str = str(exc)

        if "WebSocketDisconnect" in exc_name or "NO_STATUS_RCVD" in exc_str:
            return True

        # Recursively check ExceptionGroup
        if hasattr(exc, "exceptions") and getattr(exc, "exceptions", None):
            exceptions_list = getattr(exc, "exceptions", [])
            for sub_exc in exceptions_list:
                if check_exception(sub_exc):
                    return True

        # Check chained exceptions
        if hasattr(exc, "__cause__") and exc.__cause__:
            if check_exception(exc.__cause__):
                return True

        # Check context exceptions
        if hasattr(exc, "__context__") and exc.__context__:
            if check_exception(exc.__context__):
                return True

        return False

    return check_exception(e)
