import asyncio
import atexit
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, AsyncGenerator, Dict

from autogen_core import Component, ComponentBase
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, ConfigDict, PrivateAttr
from typing_extensions import Self

from ._config import McpServerParams, SseServerParams, StdioServerParams


@asynccontextmanager
async def create_mcp_server_session(
    server_params: McpServerParams,
) -> AsyncGenerator[ClientSession, None]:
    """Create an MCP client session for the given server parameters."""
    if isinstance(server_params, StdioServerParams):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.read_timeout_seconds),
            ) as session:
                yield session
    elif isinstance(server_params, SseServerParams):
        async with sse_client(**server_params.model_dump()) as (read, write):
            async with ClientSession(read_stream=read, write_stream=write) as session:
                yield session


class McpSessionConfig(BaseModel):
    server_params: McpServerParams


class McpSessionActor(ComponentBase[BaseModel], Component[McpSessionConfig]):
    component_type = "mcp_session_actor"
    component_config_schema = McpSessionConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSessionActor"

    server_params: McpServerParams
    _actor: Any = PrivateAttr(default=None)
    # actor: Any = PrivateAttr(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

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

    async def call(self, name: str, kwargs: Dict[str, Any]) -> Any:
        if not self._active:
            raise RuntimeError("MCP Actor not running, call initialize() first")
        if self._actor_task and self._actor_task.done():
            raise RuntimeError("MCP actor task crashed", self._actor_task.exception())
        fut: asyncio.Future[Any] = asyncio.Future()
        await self._command_queue.put({"type": "call", "name": name, "args": kwargs, "future": fut})
        res = await fut
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
        try:
            async with create_mcp_server_session(self.server_params) as session:
                await session.initialize()
                while True:
                    cmd = await self._command_queue.get()
                    if cmd["type"] == "shutdown":
                        cmd["future"].set_result("ok")
                        break
                    elif cmd["type"] == "call":
                        try:
                            result = session.call_tool(name=cmd["name"], arguments=cmd["args"])
                            cmd["future"].set_result(result)
                        except Exception as e:
                            cmd["future"].set_exception(e)
        except Exception as e:
            if self._shutdown_future and not self._shutdown_future.done():
                self._shutdown_future.set_exception(e)

    def _sync_shutdown(self) -> None:
        # Attempt to close the actor synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except Exception:
            pass

    def _to_config(self) -> McpSessionConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            McpSessionConfig: The configuration of the adapter.
        """
        return McpSessionConfig(server_params=self.server_params)

    @classmethod
    def _from_config(cls, config: McpSessionConfig) -> Self:
        """
        Create an instance of McpSessionActor from its configuration.

        Args:
            config (McpSessionConfig): The configuration of the adapter.

        Returns:
            McpSessionActor: An instance of SseMcpToolAdapter.
        """
        return cls(server_params=config.server_params)
