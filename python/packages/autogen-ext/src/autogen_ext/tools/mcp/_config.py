from typing import Any, TypeAlias

from mcp import StdioServerParameters
from pydantic import BaseModel


class StdioServerParams(StdioServerParameters):
    """Parameters for connecting to an MCP server over STDIO."""

    pass


class SseServerParams(BaseModel):
    """Parameters for connecting to an MCP server over SSE."""

    url: str
    headers: dict[str, Any] | None = None
    timeout: float = 5
    sse_read_timeout: float = 60 * 5


McpServerParams: TypeAlias = StdioServerParams | SseServerParams
