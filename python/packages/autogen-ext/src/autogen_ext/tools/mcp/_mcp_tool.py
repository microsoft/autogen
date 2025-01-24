from abc import ABC, abstractmethod
from typing import Any, Type

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from json_schema_to_pydantic import create_model
from mcp import ClientSession, StdioServerParameters, Tool, stdio_client
from mcp.client.sse import sse_client
from pydantic import BaseModel


class StdioMcpTool(BaseTool[BaseModel, Any]):
    """Adapter for MCP tools to make them compatible with AutoGen.

    Args:
        server_params (StdioServerParameters): Parameters for the MCP server connection
        tool (Tool): The MCP tool to wrap
    """

    def __init__(self, server_params: StdioServerParameters, tool: Tool) -> None:
        self._tool = tool
        self.server_params = server_params

        # Extract name and description
        name = tool.name
        description = tool.description or ""

        # Validate and extract schema information with detailed errors
        if tool.inputSchema is None:
            raise ValueError(f"Tool {name} has no input schema defined")

        if not isinstance(tool.inputSchema, dict):
            raise ValueError(f"Invalid input schema for tool {name}: expected dictionary, got {type(tool.inputSchema)}")

        # Create the input model from the tool's schema
        input_model = create_model(tool.inputSchema)

        # Use Any as return type since MCP tool returns can vary
        return_type: Type[Any] = object

        super().__init__(input_model, return_type, name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        """Execute the MCP tool with the given arguments.

        Args:
            args: The validated input arguments
            cancellation_token: Token for cancelling the operation

        Returns:
            The result from the MCP tool

        Raises:
            Exception: If tool execution fails
        """
        kwargs = args.model_dump()

        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    if cancellation_token.is_cancelled():
                        raise Exception("Operation cancelled")

                    result = await session.call_tool(self._tool.name, kwargs)

                    if result.isError:
                        raise Exception(f"MCP tool execution failed: {result.content}")
                    return result.content
        except Exception as e:
            raise Exception(str(e)) from e

class StdioMcpToolBuilder:
    def __init__(self, server_params: StdioServerParameters, tool_name: str) -> None:
        self.server_params: StdioServerParameters = server_params
        self.tool_name: str = tool_name

    async def build(self) -> StdioMcpTool:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_list = await session.list_tools()
                for tool in tools_list.tools:
                    if tool.name == self.tool_name:
                        return StdioMcpTool(self.server_params, tool)
        raise ValueError(f"Tool {self.tool_name} not found")

class SseServerParameters(BaseModel):
    url: str
    headers: dict[str, Any]


class SseMcpTool(BaseTool[BaseModel, Any]):
    """Adapter for MCP tools to make them compatible with AutoGen.

    Args:
        server_params (SseServerParameters): Parameters for the MCP server connection
        tool (Tool): The MCP tool to wrap
    """

    def __init__(self, server_params: SseServerParameters, tool: Tool) -> None:
        self._tool = tool
        self.server_params = server_params

        # Extract name and description
        name = tool.name
        description = tool.description or ""

        # Validate and extract schema information with detailed errors
        if tool.inputSchema is None:
            raise ValueError(f"Tool {name} has no input schema defined")

        if not isinstance(tool.inputSchema, dict):
            raise ValueError(f"Invalid input schema for tool {name}: expected dictionary, got {type(tool.inputSchema)}")

        # Create the input model from the tool's schema
        input_model = create_model(tool.inputSchema)

        # Use Any as return type since MCP tool returns can vary
        return_type: Type[Any] = object

        super().__init__(input_model, return_type, name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        """Execute the MCP tool with the given arguments.

        Args:
            args: The validated input arguments
            cancellation_token: Token for cancelling the operation

        Returns:
            The result from the MCP tool

        Raises:
            Exception: If tool execution fails
        """
        kwargs = args.model_dump()

        try:
            async with sse_client(self.server_params.url, headers=self.server_params.headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    if cancellation_token.is_cancelled():
                        raise Exception("Operation cancelled")

                    result = await session.call_tool(self._tool.name, kwargs)

                    if result.isError:
                        raise Exception(f"MCP tool execution failed: {result.content}")
            return result.content
        except Exception as e:
            raise Exception(str(e)) from e


class SseMcpToolBuilder:
    def __init__(self, server_params: SseServerParameters, tool_name: str) -> None:
        self.server_params = server_params
        self.tool_name = tool_name

    async def build(self) -> SseMcpTool:
        async with sse_client(self.server_params.url, headers=self.server_params.headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_list = await session.list_tools()
                for tool in tools_list.tools:
                    if tool.name == self.tool_name:
                        return SseMcpTool(self.server_params, tool)

                raise ValueError(f"Tool {self.tool_name} not found")
        pass