import asyncio
import builtins
from datetime import timedelta
from typing import Any, Dict, List, Literal, Mapping, Optional

from autogen_core import CancellationToken, Component, ComponentModel, Image
from autogen_core.tools import (
    ImageResultContent,
    ParametersSchema,
    TextResultContent,
    ToolResult,
    ToolSchema,
    WorkBench,
)
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel
from typing_extensions import Annotated, Self

from ._config import McpServerParams, SseServerParams, StdioServerParams


class McpWorkBenchConfig(BaseModel):
    server_params: McpServerParams


class McpWorkBenchState(BaseModel):
    type: Literal["McpWorkBenchState"] = "McpWorkBenchState"


class McpWorkBench(WorkBench, Component[McpWorkBenchConfig]):
    """
    A workbench that wraps an MCP server and provides an interface
    to list and call tools provided by the server.
    """

    def __init__(self, server_params: McpServerParams) -> None:
        self._server_params = server_params
        self._session: ClientSession | None = None
        self._read = None
        self._write = None

    async def list_tools(self) -> List[ToolSchema]:
        if not self._session:
            raise RuntimeError("Session is not initialized. Call start() first.")
        list_tool_result = await self._session.list_tools()
        schema = []
        for tool in list_tool_result.tools:
            name = tool.name
            description = tool.description or ""
            parameters = ParametersSchema(
                type="object",
                properties=tool.inputSchema["properties"],
                required=tool.inputSchema.get("required", []),
                additionalProperties=tool.inputSchema.get("additionalProperties", False),
            )
            tool_schema = ToolSchema(
                name=name,
                description=description,
                parameters=parameters,
            )
            schema.append(tool_schema)
        return schema

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any] | None = None, cancellation_token: CancellationToken | None = None
    ) -> ToolResult:
        if not self._session:
            raise RuntimeError("Session is not initialized. Call start() first.")
        if not cancellation_token:
            cancellation_token = CancellationToken()
        if not arguments:
            arguments = {}
        try:
            result_future = asyncio.ensure_future(self._session.call_tool(name=name, arguments=dict(arguments)))
            cancellation_token.link_future(result_future)
            result = await result_future
            result_parts: List[TextResultContent | ImageResultContent] = []
            is_error = result.isError
            for content in result.content:
                if isinstance(content, TextContent):
                    result_parts.append(TextResultContent(content=content.text))
                elif isinstance(content, ImageContent):
                    result_parts.append(ImageResultContent(content=Image.from_base64(content.data)))
                elif isinstance(content, EmbeddedResource):
                    # TODO: how to handle embedded resources?
                    # For now we just use text representation.
                    result_parts.append(TextResultContent(content=content.model_dump_json()))
                else:
                    raise ValueError(f"Unknown content type from server: {type(content)}")
        except Exception as e:
            error_message = self._format_errors(e)
            is_error = True
            result_parts = [TextResultContent(content=error_message)]
        return ToolResult(name=name, result=result_parts, is_error=is_error)

    def _format_errors(self, error: Exception) -> str:
        """Recursively format errors into a string."""

        error_message = ""
        if hasattr(builtins, "ExceptionGroup") and isinstance(error, builtins.ExceptionGroup):
            # ExceptionGroup is available in Python 3.11+.
            # TODO: how to make this compatible with Python 3.10?
            for sub_exception in error.exceptions:  # type: ignore
                error_message += self._format_errors(sub_exception)  # type: ignore
        else:
            error_message += f"{str(error)}\n"
        return error_message

    async def start(self) -> None:
        if self._session:
            raise RuntimeError("Session is already initialized. Call stop() first.")

        if isinstance(self._server_params, StdioServerParams):
            read, write = await stdio_client(self._server_params).__aenter__()
            self._read = read
            self._write = write
            session = await ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=self._server_params.read_timeout_seconds),
            ).__aenter__()
            self._session = session
        elif isinstance(self._server_params, SseServerParams):
            read, write = await sse_client(**self._server_params.model_dump()).__aenter__()
            self._read = read
            self._write = write
            session = await ClientSession(read_stream=read, write_stream=write).__aenter__()
            self._session = session
        else:
            raise ValueError(f"Unsupported server params type: {type(self._server_params)}")

    async def stop(self) -> None:
        if self._session:
            # Close the session and streams in reverse order
            await self._session.__aexit__(None, None, None)
            self._session = None

            # If streams exist, close them
            if hasattr(self, "_write") and self._write:
                # Determine the context manager based on the server params type
                if isinstance(self._server_params, StdioServerParams):
                    cm = stdio_client(self._server_params)
                elif isinstance(self._server_params, SseServerParams):
                    cm = sse_client(**self._server_params.model_dump())
                else:
                    raise ValueError(f"Unsupported server params type: {type(self._server_params)}")

                # Exit the context manager to properly close streams
                await cm.__aexit__(None, None, None)
                self._read = None
                self._write = None
        else:
            raise RuntimeError("Session is not initialized. Call start() first.")

    async def reset(self) -> None:
        pass

    async def save_state(self) -> Mapping[str, Any]:
        return McpWorkBenchState().model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        pass

    def _to_config(self) -> McpWorkBenchConfig:
        return McpWorkBenchConfig(server_params=self._server_params)

    @classmethod
    def from_config(cls, config: McpWorkBenchConfig) -> Self:
        return cls(server_params=config.server_params)
