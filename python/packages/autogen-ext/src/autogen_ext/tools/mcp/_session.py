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


class McpSessionActorConfig(BaseModel):
    server_params: McpServerParams


class McpSessionActor(ComponentBase[BaseModel], Component[McpSessionActorConfig]):
    component_type = "mcp_session_actor"
    component_config_schema = McpSessionActorConfig
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

    async def _close(self) -> None:
        if not self._active or self._actor_task is None:
            return
        self._shutdown_future: asyncio.Future[Any] = asyncio.Future()
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
        finally:
            self._active = False
            self._actor_task = None
            self._shutdown_future = None

    def _sync_shutdown(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            loop.create_task(self._close())
        else:
            loop.run_until_complete(self._close())
    

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


class McpSessionConfig(BaseModel):
    """Configuration for the MCP session actor."""
    session_id: int = 0
    server_params: McpServerParams


class McpSession(ComponentBase[BaseModel], Component[McpSessionConfig]):
    """MCP session component.

    This component is used to manage the MCP session and provide access to the MCP server.
    It is used internally by the MCP tool adapters.

    Args:
        session_id (int, optional): Session ID. If 0 or do not insert, a new session will be created.
        server_params (McpServerParams): Parameters for the MCP server connection.
    """

    component_type = "mcp_session"
    component_config_schema = McpSessionConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSession"

    __sessions:Dict[int, McpSessionActor] = {}  # singleton instance
    __session_ref_count:Dict[int, int] = {}  # reference count for each session

    def __init__(self, server_params: McpServerParams, session_id:int = 0) -> None:
        """Initialize the MCP session.
        Args:
            session_id (int): Session ID. If 0, a new session will be created.
            server_params (McpServerParams): Parameters for the MCP server connection.
        """
        if server_params is None:
            raise ValueError("Server params cannot be None")
        self._server_params: McpServerParams = server_params
        if session_id == 0:
            self._session_id = max(self.__sessions.keys(), default=0) + 1
        if session_id != 0:
            if session_id not in self.__sessions:
                self._session_id = session_id
            else:
                self._session_id = session_id

    @property
    def id(self) -> int:
        """Get the session ID."""
        return self._session_id

    def initialize(self) -> None:
        """Initialize the MCP session."""
        if self._session_id == 0:
            raise ValueError("Session ID cannot be 0")
        if self._session_id not in self.__sessions:
            self.__sessions[self._session_id] = McpSessionActor(self._server_params)
            self.__session_ref_count[self._session_id] = 0
        self.__session_ref_count[self._session_id] += 1

    async def close(self) -> None:
        """Close the MCP session."""
        if self._session_id == 0:
            raise ValueError("Session ID cannot be 0")
        if self._session_id not in self.__sessions:
            raise ValueError(f"Session ID {self._session_id} not found")
        self.__session_ref_count[self._session_id] -= 1
        if self.__session_ref_count[self._session_id] == 0:
            await self.__sessions[self._session_id]._close()
            del self.__sessions[self._session_id]
            del self.__session_ref_count[self._session_id]
        

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[McpSessionActor, None]:
        """Create a new MCP session."""
        if self._session_id == 0:
            raise ValueError("Session ID cannot be 0")
        """
        if session_id not in self.__sessions:
            self.__sessions[session_id] = McpSessionActor(server_params)
        """
        await self.__sessions[self._session_id].initialize()
        yield self.__sessions[self._session_id]
        # do not close the session here, cause all of MCP tools share the same session

    def _to_config(self):
        return McpSessionConfig(session_id=self._session_id, server_params=self._server_params)
    
    @classmethod
    def _from_config(cls, config: McpSessionConfig) -> Self:
        return cls(session_id=config.session_id, server_params=config.server_params)