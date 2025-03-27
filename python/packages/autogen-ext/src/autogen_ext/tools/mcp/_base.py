import asyncio
import builtins
from abc import ABC
from typing import Any, Generic, Type, TypeVar

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from json_schema_to_pydantic import create_model
from mcp import Tool
from pydantic import BaseModel

from ._config import McpServerParams
from ._session import create_mcp_server_session

TServerParams = TypeVar("TServerParams", bound=McpServerParams)


class McpToolAdapter(BaseTool[BaseModel, Any], ABC, Generic[TServerParams]):
    """
    Base adapter class for MCP tools to make them compatible with AutoGen.

    Args:
        server_params (TServerParams): Parameters for the MCP server connection.
        tool (Tool): The MCP tool to wrap.
    """

    component_type = "tool"

    def __init__(self, server_params: TServerParams, tool: Tool) -> None:
        self._tool = tool
        self._server_params = server_params

        # Extract name and description
        name = tool.name
        description = tool.description or ""

        # Create the input model from the tool's schema
        input_model = create_model(tool.inputSchema)

        # Use Any as return type since MCP tool returns can vary
        return_type: Type[Any] = object

        super().__init__(input_model, return_type, name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        """
        Run the MCP tool with the provided arguments.

        Args:
            args (BaseModel): The arguments to pass to the tool.
            cancellation_token (CancellationToken): Token to signal cancellation.

        Returns:
            Any: The result of the tool execution.

        Raises:
            Exception: If the operation is cancelled or the tool execution fails.
        """
        # Convert the input model to a dictionary
        # Exclude unset values to avoid sending them to the MCP servers which may cause errors
        # for many servers.
        kwargs = args.model_dump(exclude_unset=True)

        try:
            async with create_mcp_server_session(self._server_params) as session:
                await session.initialize()

                if cancellation_token.is_cancelled():
                    raise Exception("Operation cancelled")

                result_future = asyncio.ensure_future(session.call_tool(name=self._tool.name, arguments=kwargs))
                cancellation_token.link_future(result_future)
                result = await result_future

                if result.isError:
                    raise Exception(f"MCP tool execution failed: {result.content}")
                return result.content
        except Exception as e:
            error_message = self._format_errors(e)
            raise Exception(error_message) from e

    @classmethod
    async def from_server_params(cls, server_params: TServerParams, tool_name: str) -> "McpToolAdapter[TServerParams]":
        """
        Create an instance of McpToolAdapter from server parameters and tool name.

        Args:
            server_params (TServerParams): Parameters for the MCP server connection.
            tool_name (str): The name of the tool to wrap.

        Returns:
            McpToolAdapter[TServerParams]: An instance of McpToolAdapter.

        Raises:
            ValueError: If the tool with the specified name is not found.
        """
        async with create_mcp_server_session(server_params) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            matching_tool = next((t for t in tools_response.tools if t.name == tool_name), None)

            if matching_tool is None:
                raise ValueError(
                    f"Tool '{tool_name}' not found, available tools: {', '.join([t.name for t in tools_response.tools])}"
                )

        return cls(server_params=server_params, tool=matching_tool)

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
