import json
from typing import Any, Optional, Type

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from json_schema_to_pydantic import create_model
from pydantic import BaseModel


class HttpToolConfig(BaseModel):
    name: str
    """
    The name of the tool.
    """
    description: Optional[str]
    """
    A description of the tool.
    """
    url: str
    """
    The URL to send the request to.
    """
    headers: Optional[dict[str, Any]]
    """
    A dictionary of headers to send with the request.
    """
    json_schema: dict[str, Any]
    """
    A JSON Schema object defining the expected parameters for the tool.
    """


class HttpTool(BaseTool[BaseModel, Any], Component[HttpToolConfig]):
    """Adapter for MCP tools to make them compatible with AutoGen.

    Args:
        server_params (StdioServerParameters): Parameters for the MCP server connection
        tool (Tool): The MCP tool to wrap
    """

    def __init__(self, server_params: HttpToolConfig) -> None:
        self.server_params = server_params

        # Extract name and description
        name = server_params.name
        description = server_params.description or ""

        # Create the input model from the tool's schema
        input_model = create_model(server_params.json_schema)

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

        async with httpx.AsyncClient() as client:
            response = await client.post(self.server_params.url, json=args.model_dump())

        return response.json()
