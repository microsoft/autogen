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

    url: str  # The SSE endpoint URL.
    headers: dict[str, Any] | None = None  # Optional headers to include in requests.
    timeout: float = 5  # HTTP timeout for regular operations.
    sse_read_timeout: float = 60 * 5  # Timeout for SSE read operations.


class StreamableHttpServerParams(BaseModel):
    """Parameters for connecting to an MCP server over Streamable HTTP."""

    type: Literal["StreamableHttpServerParams"] = "StreamableHttpServerParams"

    url: str  # The endpoint URL.
    headers: dict[str, Any] | None = None  # Optional headers to include in requests.
    timeout: float = 30.0  # HTTP timeout for regular operations in seconds.
    sse_read_timeout: float = 300.0  # Timeout for SSE read operations in seconds.
    terminate_on_close: bool = True


McpServerParams = Annotated[
    StdioServerParams | SseServerParams | StreamableHttpServerParams, Field(discriminator="type")
]
