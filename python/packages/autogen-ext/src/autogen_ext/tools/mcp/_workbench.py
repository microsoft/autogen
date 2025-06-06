import asyncio
import builtins
import warnings
from typing import Any, List, Literal, Mapping

from autogen_core import CancellationToken, Component, Image
from autogen_core.tools import (
    ImageResultContent,
    ParametersSchema,
    TextResultContent,
    ToolResult,
    ToolSchema,
    Workbench,
)
from mcp.types import CallToolResult, EmbeddedResource, ImageContent, ListToolsResult, TextContent
from pydantic import BaseModel
from typing_extensions import Self

from ._actor import McpSessionActor
from ._config import McpServerParams, SseServerParams, StdioServerParams, StreamableHttpServerParams


class McpWorkbenchConfig(BaseModel):
    server_params: McpServerParams


class McpWorkbenchState(BaseModel):
    type: Literal["McpWorkBenchState"] = "McpWorkBenchState"


class McpWorkbench(Workbench, Component[McpWorkbenchConfig]):
    """
    A workbench that wraps an MCP server and provides an interface
    to list and call tools provided by the server.

    Args:
        server_params (McpServerParams): The parameters to connect to the MCP server.
            This can be either a :class:`StdioServerParams` or :class:`SseServerParams`.

    Examples:

        Here is a simple example of how to use the workbench with a `mcp-server-fetch` server:

        .. code-block:: python

            import asyncio

            from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


            async def main() -> None:
                params = StdioServerParams(
                    command="uvx",
                    args=["mcp-server-fetch"],
                    read_timeout_seconds=60,
                )

                # You can also use `start()` and `stop()` to manage the session.
                async with McpWorkbench(server_params=params) as workbench:
                    tools = await workbench.list_tools()
                    print(tools)
                    result = await workbench.call_tool(tools[0]["name"], {"url": "https://github.com/"})
                    print(result)


            asyncio.run(main())

        Example of using the workbench with the `GitHub MCP Server <https://github.com/github/github-mcp-server>`_:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
                server_params = StdioServerParams(
                    command="docker",
                    args=[
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        "GITHUB_PERSONAL_ACCESS_TOKEN",
                        "ghcr.io/github/github-mcp-server",
                    ],
                    env={
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                    },
                )
                async with McpWorkbench(server_params) as mcp:
                    agent = AssistantAgent(
                        "github_assistant",
                        model_client=model_client,
                        workbench=mcp,
                        reflect_on_tool_use=True,
                        model_client_stream=True,
                    )
                    await Console(agent.run_stream(task="Is there a repository named Autogen"))


            asyncio.run(main())

        Example of using the workbench with the `Playwright MCP Server <https://github.com/microsoft/playwright-mcp>`_:

        .. code-block:: python

            # First run `npm install -g @playwright/mcp@latest` to install the MCP server.
            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.conditions import TextMessageTermination
            from autogen_agentchat.ui import Console
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
                server_params = StdioServerParams(
                    command="npx",
                    args=[
                        "@playwright/mcp@latest",
                        "--headless",
                    ],
                )
                async with McpWorkbench(server_params) as mcp:
                    agent = AssistantAgent(
                        "web_browsing_assistant",
                        model_client=model_client,
                        workbench=mcp,
                        model_client_stream=True,
                    )
                    team = RoundRobinGroupChat(
                        [agent],
                        termination_condition=TextMessageTermination(source="web_browsing_assistant"),
                    )
                    await Console(team.run_stream(task="Find out how many contributors for the microsoft/autogen repository"))


            asyncio.run(main())

    """

    component_provider_override = "autogen_ext.tools.mcp.McpWorkbench"
    component_config_schema = McpWorkbenchConfig

    def __init__(self, server_params: McpServerParams) -> None:
        self._server_params = server_params
        # self._session: ClientSession | None = None
        self._actor: McpSessionActor | None = None
        self._actor_loop: asyncio.AbstractEventLoop | None = None
        self._read = None
        self._write = None

    @property
    def server_params(self) -> McpServerParams:
        return self._server_params

    async def list_tools(self) -> List[ToolSchema]:
        if not self._actor:
            await self.start()  # fallback to start the actor if not initialized instead of raising an error
            # Why? Because when deserializing the workbench, the actor might not be initialized yet.
            # raise RuntimeError("Actor is not initialized. Call start() first.")
        if self._actor is None:
            raise RuntimeError("Actor is not initialized. Please check the server connection.")
        result_future = await self._actor.call("list_tools", None)
        list_tool_result = await result_future
        assert isinstance(
            list_tool_result, ListToolsResult
        ), f"list_tools must return a CallToolResult, instead of : {str(type(list_tool_result))}"
        schema: List[ToolSchema] = []
        for tool in list_tool_result.tools:
            name = tool.name
            description = tool.description or ""
            parameters = ParametersSchema(
                type="object",
                properties=tool.inputSchema.get("properties", {}),
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
        if not self._actor:
            await self.start()  # fallback to start the actor if not initialized instead of raising an error
            # Why? Because when deserializing the workbench, the actor might not be initialized yet.
            # raise RuntimeError("Actor is not initialized. Call start() first.")
        if self._actor is None:
            raise RuntimeError("Actor is not initialized. Please check the server connection.")
        if not cancellation_token:
            cancellation_token = CancellationToken()
        if not arguments:
            arguments = {}
        try:
            result_future = await self._actor.call("call_tool", {"name": name, "kargs": arguments})
            cancellation_token.link_future(result_future)
            result = await result_future
            assert isinstance(
                result, CallToolResult
            ), f"call_tool must return a CallToolResult, instead of : {str(type(result))}"
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
        if self._actor:
            warnings.warn(
                "McpWorkbench is already started. No need to start again.",
                UserWarning,
                stacklevel=2,
            )
            return  # Already initialized, no need to start again

        if isinstance(self._server_params, (StdioServerParams, SseServerParams, StreamableHttpServerParams)):
            self._actor = McpSessionActor(self._server_params)
            await self._actor.initialize()
            self._actor_loop = asyncio.get_event_loop()
        else:
            raise ValueError(f"Unsupported server params type: {type(self._server_params)}")

    async def stop(self) -> None:
        if self._actor:
            # Close the actor
            await self._actor.close()
            self._actor = None
        else:
            raise RuntimeError("McpWorkbench is not started. Call start() first.")

    async def reset(self) -> None:
        pass

    async def save_state(self) -> Mapping[str, Any]:
        return McpWorkbenchState().model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        pass

    def _to_config(self) -> McpWorkbenchConfig:
        return McpWorkbenchConfig(server_params=self._server_params)

    @classmethod
    def _from_config(cls, config: McpWorkbenchConfig) -> Self:
        return cls(server_params=config.server_params)

    def __del__(self) -> None:
        # Ensure the actor is stopped when the workbench is deleted
        if self._actor and self._actor_loop:
            loop = self._actor_loop
            if loop.is_running() and not loop.is_closed():
                loop.call_soon_threadsafe(lambda: asyncio.create_task(self.stop()))
            else:
                msg = "Cannot safely stop actor at [McpWorkbench.__del__]: loop is closed or not running"
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
