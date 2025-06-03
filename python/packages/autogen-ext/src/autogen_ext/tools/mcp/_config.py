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
    timeout: timedelta = timedelta(seconds=30)  # HTTP timeout for regular operations.
    sse_read_timeout: timedelta = timedelta(seconds=60 * 5)  # Timeout for SSE read operations.
    terminate_on_close: bool = True


McpServerParams = Annotated[
    StdioServerParams | SseServerParams | StreamableHttpServerParams, Field(discriminator="type")
]
