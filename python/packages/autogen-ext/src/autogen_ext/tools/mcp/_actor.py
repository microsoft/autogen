import asyncio
import atexit
from typing import Any, Coroutine, Dict, Mapping, TypedDict

from autogen_core import Component, ComponentBase
from pydantic import BaseModel
from typing_extensions import Self

from mcp.types import CallToolResult, ListToolsResult

from ._config import McpServerParams
from ._session import create_mcp_server_session

McpResult = Coroutine[Any, Any, ListToolsResult] | Coroutine[Any, Any, CallToolResult]
McpFuture = asyncio.Future[McpResult]


class McpActorArgs(TypedDict):
    name: str | None
    kargs: Mapping[str, Any]


class McpSessionActorConfig(BaseModel):
    server_params: McpServerParams


class McpSessionActor(ComponentBase[BaseModel], Component[McpSessionActorConfig]):
    component_type = "mcp_session_actor"
    component_config_schema = McpSessionActorConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSessionActor"

    server_params: McpServerParams

    # model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, server_params: McpServerParams) -> None:
        self.server_params: McpServerParams = server_params
        self.name = "mcp_session_actor"
        self.description = "MCP session actor"
        self._command_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._actor_task: asyncio.Task[Any] | None = None
        self._shutdown_future: asyncio.Future[Any] | None = None
        self._active = False
        atexit.register(self._sync_shutdown)

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
        if type in {"list_tools", "shutdown"}:
            await self._command_queue.put({"type": type, "future": fut})
            res = await fut
        elif type == "call_tool":
            if args is None:
                raise ValueError("args is required for call_tool")
            name = args.get("name", None)
            kwargs = args.get("kargs", {})
            if name is None:
                raise ValueError("name is required for call_tool")
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

    async def _run_actor(self) -> None:
        result: McpResult
        try:
            async with create_mcp_server_session(self.server_params) as session:
                await session.initialize()
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
                    elif cmd["type"] == "list_tools":
                        try:
                            result = session.list_tools()
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
        except Exception as e:
            if self._shutdown_future and not self._shutdown_future.done():
                self._shutdown_future.set_exception(e)
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
