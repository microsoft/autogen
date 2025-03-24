from typing import Any, TypeAlias

from mcp import StdioServerParameters
from pydantic import BaseModel
from datetime import timedelta


class StdioServerParams(StdioServerParameters):
    """Parameters for connecting to an MCP server over STDIO."""

    stdio_read_timeout: timedelta = timedelta(seconds=10)


class SseServerParams(BaseModel):
    """Parameters for connecting to an MCP server over SSE."""

    url: str
    headers: dict[str, Any] | None = None
    timeout: float = 5
    sse_read_timeout: float = 60 * 5


McpServerParams: TypeAlias = StdioServerParams | SseServerParams
