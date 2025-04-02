from typing import Any, TypeAlias

from mcp import StdioServerParameters
from pydantic import BaseModel


class StdioServerParams(StdioServerParameters):
    """Parameters for connecting to an MCP server over STDIO."""

    read_timeout_seconds: float = 5


class SseServerParams(BaseModel):
    """Parameters for connecting to an MCP server over SSE."""

    url: str
    headers: dict[str, Any] | None = None
    timeout: float = 5
    sse_read_timeout: float = 60 * 5


McpServerParams: TypeAlias = StdioServerParams | SseServerParams
