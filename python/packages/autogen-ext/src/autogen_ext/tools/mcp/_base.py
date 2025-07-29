import asyncio
import builtins
import json
from abc import ABC
from typing import Any, Dict, Generic, Sequence, Type, TypeVar

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from autogen_core.utils import schema_to_pydantic_model
from pydantic import BaseModel
from pydantic.networks import AnyUrl

from mcp import ClientSession, Tool
from mcp.types import AudioContent, ContentBlock, EmbeddedResource, ImageContent, ResourceLink, TextContent

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

    def __init__(self, server_params: TServerParams, tool: Tool, session: ClientSession | None = None) -> None:
        self._tool = tool
        self._server_params = server_params
        self._session = session

        # Extract name and description
        name = tool.name
        description = tool.description or ""

        # Create the input model from the tool's schema
        input_model = schema_to_pydantic_model(tool.inputSchema)

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

        if self._session is not None:
            # If a session is provided, use it directly.
            session = self._session
            return await self._run(args=kwargs, cancellation_token=cancellation_token, session=session)

        async with create_mcp_server_session(self._server_params) as session:
            await session.initialize()
            return await self._run(args=kwargs, cancellation_token=cancellation_token, session=session)

    def _normalize_payload_to_content_list(self, payload: Sequence[ContentBlock]) -> list[ContentBlock]:
        """
        Normalizes a raw tool output payload into a list of content items.
        - If payload is already a sequence of ContentBlock items, it's converted to a list and returned.
        - If payload is a single ContentBlock item, it's wrapped in a list.
        - If payload is a string, it's wrapped in [TextContent(text=payload)].
        - Otherwise, the payload is stringified and wrapped in [TextContent(text=str(payload))].
        """
        if isinstance(payload, Sequence) and all(
            isinstance(item, (TextContent, ImageContent, EmbeddedResource, AudioContent, ResourceLink))
            for item in payload
        ):
            return list(payload)
        elif isinstance(payload, (TextContent, ImageContent, EmbeddedResource, AudioContent, ResourceLink)):
            return [payload]
        elif isinstance(payload, str):
            return [TextContent(text=payload, type="text")]
        else:
            return [TextContent(text=str(payload), type="text")]

    async def _run(self, args: Dict[str, Any], cancellation_token: CancellationToken, session: ClientSession) -> Any:
        exceptions_to_catch: tuple[Type[BaseException], ...]
        if hasattr(builtins, "ExceptionGroup"):
            exceptions_to_catch = (asyncio.CancelledError, builtins.ExceptionGroup)
        else:
            exceptions_to_catch = (asyncio.CancelledError,)

        try:
            if cancellation_token.is_cancelled():
                raise asyncio.CancelledError("Operation cancelled")

            result_future = asyncio.ensure_future(session.call_tool(name=self._tool.name, arguments=args))
            cancellation_token.link_future(result_future)
            result = await result_future

            normalized_content_list = self._normalize_payload_to_content_list(result.content)

            if result.isError:
                serialized_error_message = self.return_value_as_string(normalized_content_list)
                raise Exception(serialized_error_message)
            return normalized_content_list

        except exceptions_to_catch:
            # Re-raise these specific exception types directly.
            raise

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

    def return_value_as_string(self, value: list[Any]) -> str:
        """Return a string representation of the result."""

        def serialize_item(item: Any) -> dict[str, Any]:
            if isinstance(item, (TextContent, ImageContent, AudioContent)):
                dumped = item.model_dump()
                # Remove the 'meta' field if it exists and is None (for backward compatibility)
                if dumped.get("meta") is None:
                    dumped.pop("meta", None)
                return dumped
            elif isinstance(item, EmbeddedResource):
                type = item.type
                resource = {}
                for key, val in item.resource.model_dump().items():
                    # Skip 'meta' field if it's None (for backward compatibility)
                    if key == "meta" and val is None:
                        continue
                    if isinstance(val, AnyUrl):
                        resource[key] = str(val)
                    else:
                        resource[key] = val
                dumped_annotations = item.annotations.model_dump() if item.annotations else None
                # Remove 'meta' from annotations if it exists and is None
                if dumped_annotations and dumped_annotations.get("meta") is None:
                    dumped_annotations.pop("meta", None)
                return {"type": type, "resource": resource, "annotations": dumped_annotations}
            elif isinstance(item, ResourceLink):
                dumped = item.model_dump()
                # Remove the 'meta' field if it exists and is None (for backward compatibility)
                if dumped.get("meta") is None:
                    dumped.pop("meta", None)
                # Convert AnyUrl to string for JSON serialization
                if "uri" in dumped and isinstance(dumped["uri"], AnyUrl):
                    dumped["uri"] = str(dumped["uri"])
                return dumped
            else:
                return {}

        return json.dumps([serialize_item(item) for item in value])
