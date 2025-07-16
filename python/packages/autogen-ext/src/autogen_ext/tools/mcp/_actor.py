import asyncio
import atexit
import base64
import io
import logging
from typing import Any, Coroutine, Dict, Mapping, TypedDict

from autogen_core import Component, ComponentBase, ComponentModel, Image
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    ModelInfo,
    SystemMessage,
    UserMessage,
)
from PIL import Image as PILImage
from pydantic import BaseModel
from typing_extensions import Self

from mcp import types as mcp_types
from mcp.client.session import ClientSession
from mcp.shared.context import RequestContext

from ._config import McpServerParams
from ._session import create_mcp_server_session

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


def _parse_sampling_content(
    content: mcp_types.TextContent | mcp_types.ImageContent | mcp_types.AudioContent, model_info: ModelInfo
) -> str | Image:
    """Convert MCP content types to Autogen content types."""
    if content.type == "text":
        return content.text
    elif content.type == "image":
        if not model_info["vision"]:
            raise ValueError("Sampling model does not support image content.")
        # Decode base64 image data and create PIL Image
        image_data = base64.b64decode(content.data)
        pil_image = PILImage.open(io.BytesIO(image_data))
        return Image.from_pil(pil_image)
    else:
        raise ValueError(f"Unsupported content type: {content.type}")


def _parse_sampling_message(message: mcp_types.SamplingMessage, model_info: ModelInfo) -> LLMMessage:
    """Convert MCP sampling messages to Autogen messages."""
    content = _parse_sampling_content(message.content, model_info=model_info)
    if message.role == "user":
        return UserMessage(
            source="user",
            content=[content],
        )
    elif message.role == "assistant":
        assert isinstance(content, str), "Assistant messages only support string content."
        return AssistantMessage(
            source="assistant",
            content=content,
        )
    else:
        raise ValueError(f"Unrecognized message role: {message.role}")


class McpActorArgs(TypedDict):
    name: str | None
    kargs: Mapping[str, Any]


class McpSessionActorConfig(BaseModel):
    server_params: McpServerParams
    model_client: ComponentModel | Dict[str, Any] | None = None


class McpSessionActor(ComponentBase[BaseModel], Component[McpSessionActorConfig]):
    component_type = "mcp_session_actor"
    component_config_schema = McpSessionActorConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSessionActor"

    server_params: McpServerParams

    # model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, server_params: McpServerParams, model_client: ChatCompletionClient | None = None) -> None:
        self.server_params: McpServerParams = server_params
        self._model_client = model_client
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
        if self._model_client is None:
            # Return an error when no model client is available
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No model client available for sampling.",
                data=None,
            )

        llm_messages: list[LLMMessage] = []

        try:
            if params.systemPrompt:
                llm_messages.append(SystemMessage(content=params.systemPrompt))

            for mcp_message in params.messages:
                llm_messages.append(_parse_sampling_message(mcp_message, model_info=self._model_client.model_info))

        except Exception as e:
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_PARAMS,
                message="Error processing sampling messages.",
                data=f"{type(e).__name__}: {e}",
            )

        try:
            result = await self._model_client.create(messages=llm_messages)

            content = result.content
            if not isinstance(content, str):
                content = str(content)

            return mcp_types.CreateMessageResult(
                role="assistant",
                content=mcp_types.TextContent(type="text", text=content),
                model=self._model_client.model_info["family"],
                stopReason=result.finish_reason,
            )
        except Exception as e:
            return mcp_types.ErrorData(
                code=mcp_types.INTERNAL_ERROR,
                message="Error sampling from model client.",
                data=f"{type(e).__name__}: {e}",
            )

    async def _run_actor(self) -> None:
        result: McpResult
        try:
            async with create_mcp_server_session(
                self.server_params, sampling_callback=self._sampling_callback
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
