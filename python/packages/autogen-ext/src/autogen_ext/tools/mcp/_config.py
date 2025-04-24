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


McpServerParams = Annotated[StdioServerParams | SseServerParams, Field(discriminator="type")]
