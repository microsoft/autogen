import asyncio
import atexit
import logging
from typing import Any, Coroutine, Dict, Mapping, TypedDict

from autogen_core import Component, ComponentBase
from pydantic import BaseModel
from typing_extensions import Self

from mcp import types as mcp_types
from mcp.client.session import ClientSession
from mcp.shared.context import RequestContext

from ._config import McpServerParams
from ._session import create_mcp_server_session
from .host import McpSessionHost

logger = logging.getLogger(__name__)

McpResult = (
    Coroutine[Any, Any, mcp_types.ListToolsResult]
    | Coroutine[Any, Any, mcp_types.CallToolResult]
    | Coroutine[Any, Any, mcp_types.ListPromptsResult]
    | Coroutine[Any, Any, mcp_types.ListResourcesResult]
    | Coroutine[Any, Any, mcp_types.ListResourceTemplatesResult]
    | Coroutine[Any, Any, mcp_types.ReadResourceResult]
    | Coroutine[Any, Any, mcp_types.GetPromptResult]
)
McpFuture = asyncio.Future[McpResult]


class McpActorArgs(TypedDict):
    """Arguments structure for MCP actor command calls.

    Args:
        name: Optional name parameter for operations that require it (e.g., tool calls)
        kargs: Additional keyword arguments for the operation
    """

    name: str | None
    kargs: Mapping[str, Any]


class McpSessionActorConfig(BaseModel):
    """Configuration model for MCP session actor components.

    Args:
        server_params: Parameters for connecting to the MCP server
    """

    server_params: McpServerParams


class McpSessionActor(ComponentBase[BaseModel], Component[McpSessionActorConfig]):
    """Actor that manages an MCP session and handles asynchronous MCP operations.

    This actor runs in a separate asyncio task and processes MCP commands through
    a queue-based system. It handles initialization, tool calls, resource operations,
    prompt operations, and proper cleanup of the MCP session.

    The actor supports callbacks for sampling and elicitation requests from MCP
    servers, delegating these to an optional host component.

    Args:
        server_params: Configuration parameters for the MCP server connection
        host: Optional host component for handling sampling and elicitation requests
    """

    component_type = "mcp_session_actor"
    component_config_schema = McpSessionActorConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSessionActor"

    server_params: McpServerParams

    # model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, server_params: McpServerParams, host: McpSessionHost | None = None) -> None:
        self.server_params: McpServerParams = server_params
        self._host = host
        self.name = "mcp_session_actor"
        self.description = "MCP session actor"
        self._command_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._actor_task: asyncio.Task[Any] | None = None
        self._shutdown_future: asyncio.Future[Any] | None = None
        self._active = False
        self._initialize_result: mcp_types.InitializeResult | None = None
        atexit.register(self._sync_shutdown)

    @property
    def initialize_result(self) -> mcp_types.InitializeResult | None:
        return self._initialize_result

    async def initialize(self) -> None:
        if not self._active:
            self._active = True
            self._actor_task = asyncio.create_task(self._run_actor())

    async def call(self, type: str, args: McpActorArgs | None = None) -> McpFuture:
        if not self._active:
            raise RuntimeError("MCP Actor not running, call initialize() first")
        if self._actor_task and self._actor_task.done():
            raise RuntimeError("MCP actor task crashed", self._actor_task.exception())
        fut: asyncio.Future[McpFuture] = asyncio.Future()
        if type in {"list_tools", "list_prompts", "list_resources", "list_resource_templates", "shutdown"}:
            await self._command_queue.put({"type": type, "future": fut})
            res = await fut
        elif type in {"call_tool", "read_resource", "get_prompt"}:
            if args is None:
                raise ValueError(f"args is required for {type}")
            name = args.get("name", None)
            kwargs = args.get("kargs", {})
            if type == "call_tool" and name is None:
                raise ValueError("name is required for call_tool")
            elif type == "read_resource":
                uri = kwargs.get("uri", None)
                if uri is None:
                    raise ValueError("uri is required for read_resource")
                await self._command_queue.put({"type": type, "uri": uri, "future": fut})
            elif type == "get_prompt":
                if name is None:
                    raise ValueError("name is required for get_prompt")
                prompt_args = kwargs.get("arguments", None)
                await self._command_queue.put({"type": type, "name": name, "args": prompt_args, "future": fut})
            else:  # call_tool
                await self._command_queue.put({"type": type, "name": name, "args": kwargs, "future": fut})
            res = await fut
        else:
            raise ValueError(f"Unknown command type: {type}")
        return res

    async def close(self) -> None:
        if not self._active or self._actor_task is None:
            return
        self._shutdown_future = asyncio.Future()
        await self._command_queue.put({"type": "shutdown", "future": self._shutdown_future})
        await self._shutdown_future
        await self._actor_task
        self._active = False

    async def _sampling_callback(
        self,
        context: RequestContext[ClientSession, Any],
        params: mcp_types.CreateMessageRequestParams,
    ) -> mcp_types.CreateMessageResult | mcp_types.ErrorData:
        """Handle sampling requests using the provided model client."""
        if self._host is None:
            # Return an error when no model client is available
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No host available for sampling.",
                data=None,
            )

        return await self._host.handle_sampling_request(params)

    async def _elicitation_callback(
        self,
        context: RequestContext["ClientSession", Any],
        params: mcp_types.ElicitRequestParams,
    ) -> mcp_types.ElicitResult | mcp_types.ErrorData:
        """Handle elicitation requests using the provided input_func."""
        if self._host is None:
            # Return an error when no model client is available
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No host available for elicitation.",
                data=None,
            )

        return await self._host.handle_elicit_request(params)

    async def _list_roots(
        self, context: RequestContext["ClientSession", Any]
    ) -> mcp_types.ListRootsResult | mcp_types.ErrorData:
        """Handle list_roots requests"""
        if self._host is None:
            # Return an error when no model client is available
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No host available for listing roots.",
                data=None,
            )
        return await self._host.handle_list_roots_request()

    async def _run_actor(self) -> None:
        result: McpResult
        try:
            async with create_mcp_server_session(
                self.server_params,
                sampling_callback=self._sampling_callback,
                elicitation_callback=self._elicitation_callback,
                list_roots_callback=self._list_roots,
            ) as session:
                # Save the initialize result
                self._initialize_result = await session.initialize()
                while True:
                    cmd = await self._command_queue.get()
                    if cmd["type"] == "shutdown":
                        cmd["future"].set_result("ok")
                        break
                    elif cmd["type"] == "call_tool":
                        try:
                            result = session.call_tool(name=cmd["name"], arguments=cmd["args"])
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
                    elif cmd["type"] == "read_resource":
                        try:
                            result = session.read_resource(uri=cmd["uri"])
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
                    elif cmd["type"] == "get_prompt":
                        try:
                            result = session.get_prompt(name=cmd["name"], arguments=cmd["args"])
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
                    elif cmd["type"] == "list_tools":
                        try:
                            result = session.list_tools()
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
                    elif cmd["type"] == "list_prompts":
                        try:
                            result = session.list_prompts()
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
                    elif cmd["type"] == "list_resources":
                        try:
                            result = session.list_resources()
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
                    elif cmd["type"] == "list_resource_templates":
                        try:
                            result = session.list_resource_templates()
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
        except Exception as e:
            if self._shutdown_future and not self._shutdown_future.done():
                self._shutdown_future.set_exception(e)
            else:
                logger.exception("Exception in MCP actor task")
        finally:
            self._active = False
            self._actor_task = None

    def _sync_shutdown(self) -> None:
        if not self._active or self._actor_task is None:
            return
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No loop available — interpreter is likely shutting down
            return

        if loop.is_closed():
            return

        if loop.is_running():
            loop.create_task(self.close())
        else:
            loop.run_until_complete(self.close())

    def _to_config(self) -> McpSessionActorConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            McpSessionConfig: The configuration of the adapter.
        """
        return McpSessionActorConfig(server_params=self.server_params)

    @classmethod
    def _from_config(cls, config: McpSessionActorConfig) -> Self:
        """
        Create an instance of McpSessionActor from its configuration.

        Args:
            config (McpSessionConfig): The configuration of the adapter.

        Returns:
            McpSessionActor: An instance of SseMcpToolAdapter.
        """
        return cls(server_params=config.server_params)
