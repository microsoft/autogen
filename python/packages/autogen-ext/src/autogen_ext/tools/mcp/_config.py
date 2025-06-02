from datetime import timedelta
from typing import Any, Literal

from mcp import StdioServerParameters
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class StdioServerParams(StdioServerParameters):
    """Parameters for connecting to an MCP server over STDIO."""

    type: Literal["StdioServerParams"] = "StdioServerParams"

    read_timeout_seconds: float = 5


class SseServerParams(BaseModel):
    """Parameters for connecting to an MCP server over SSE."""

    type: Literal["SseServerParams"] = "SseServerParams"

    url: str
    headers: dict[str, Any] | None = None
    timeout: float = 5
    sse_read_timeout: float = 60 * 5


class StreamableHttpServerParams(BaseModel):
    """Parameters for connecting to an MCP server over Streamable HTTP."""

    type: Literal["StreamableHttpServerParams"] = "StreamableHttpServerParams"

    url: str
    headers: dict[str, Any] | None = None
    timeout: timedelta = timedelta(seconds=30)
    sse_read_timeout: timedelta = timedelta(seconds=60 * 5)
    terminate_on_close: bool = True


McpServerParams = Annotated[
    StdioServerParams | SseServerParams | StreamableHttpServerParams, Field(discriminator="type")
]
