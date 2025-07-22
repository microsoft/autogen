import inspect
from typing import Any, Callable, Dict, Sequence

from autogen_core import Component, ComponentBase, ComponentModel
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
)
from pydantic import BaseModel

from mcp import types as mcp_types

from ._elicitors import Elicitor
from ._utils import (
    create_request_params_to_extra_create_args,
    finish_reason_to_stop_reason,
    parse_sampling_message,
)

RootsType = Sequence[mcp_types.Root] | Callable[[], Sequence[mcp_types.Root]]


class McpSessionHostConfig(BaseModel):
    """Configuration for MCP session host components.

    Args:
        model_client: Optional chat completion client for sampling requests
        elicitor: Optional elicitor component for handling elicitation requests
        roots: Optional list of file system roots (callable serialization not yet supported)
    """

    model_client: ComponentModel | Dict[str, Any] | None
    elicitor: ComponentModel | Dict[str, Any] | None
    # TODO: How to support callable serialization?
    roots: list[mcp_types.Root] | None

class McpSessionHost(ComponentBase[BaseModel], Component[McpSessionHostConfig]):
    """Host component that provides MCP server capabilities.

    This host acts as the client-side Host for MCP sessions, handling requests
    from MCP servers for text generation (sampling), user prompting (elicitation),
    and file system root listing. It coordinates with model clients and elicitors
    to provide these capabilities.

    The host supports three main MCP server capabilities:
    - Sampling: Text generation using a language model via chat completion client
    - Elicitation: Structured prompting and response collection via elicitors
    - Roots: Listing available file system roots for server access

    Args:
        model_client: Optional chat completion client for handling sampling requests
        roots: Optional sequence of roots or callable returning roots for file system access
        elicitor: Optional elicitor for handling elicitation requests

    Example:
        Complete setup with MCP capabilities including sampling and elicitation::

            from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import GroupChatAgentElicitor, McpSessionHost, McpWorkbench, StdioServerParams

            # Setup model client for sampling and elicitation formatting
            model_client = OpenAIChatCompletionClient(model="gpt-4o")

            # Create user proxy
            user_proxy = UserProxyAgent("user_proxy")

            # Create elicitor targeting the user proxy for elicitation handling (could be any other agent)
            elicitor = GroupChatAgentElicitor("user_proxy", model_client=model_client)

            # Create MCP session host with sampling, elicitation, and list_roots capabilities
            # If you want to support roots, import or define Root and FileUrl, then uncomment the roots line below
            host = McpSessionHost(
                model_client=model_client,  # Support sampling via model client
                elicitor=elicitor,  # Support elicitation via user_proxy
                # roots=[Root(uri=FileUrl("file:///home"), name="Home"), Root(uri=FileUrl("file:///tmp"), name="Tmp")],
            )

            # Setup MCP workbench with your server
            mcp_workbench = McpWorkbench(
                server_params=StdioServerParams(command="python", args=["your_mcp_server.py"]),
                host=host,  # Add the host here
            )

            # Create MCP-enabled assistant
            mcp_assistant = AssistantAgent(
                "mcp_assistant",
                model_client=model_client,
                workbench=mcp_workbench,
            )

            # Create team and link elicitor
            team = RoundRobinGroupChat([mcp_assistant, user_proxy])
            elicitor.set_group_chat(team)  # Required for elicitation to work

            # Now the MCP server can request sampling and elicitation from the host
    """

    component_type = "mcp_session_host"
    component_config_schema = McpSessionHostConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSessionHost"

    def __init__(
        self,
        model_client: ChatCompletionClient | None = None,
        roots: RootsType | None = None,
        elicitor: Elicitor | None = None,
    ):
        """Initialize the MCP session host.

        Args:
            model_client: Optional chat completion client for handling sampling requests.
            roots: Optional sequence of roots or callable returning roots for file system access.
            elicitor: Optional elicitor for handling elicitation requests.
        """
        self._model_client = model_client
        self._roots = list(roots) if isinstance(roots, Sequence) else roots
        self._elicitor = elicitor

    async def handle_sampling_request(
        self, params: mcp_types.CreateMessageRequestParams
    ) -> mcp_types.CreateMessageResult | mcp_types.ErrorData:
        """Handle a sampling request from MCP servers.

        Converts MCP messages to AutoGen format and uses the configured model client
        to generate a response. Handles both text and function call responses.

        Args:
            params: The sampling request containing message creation parameters.

        Returns:
            A sampling response with the generated message or error data.
        """
        if self._model_client is None:
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No model client available for sampling requests",
            )

        try:
            # Convert MCP messages to AutoGen format using existing parser
            autogen_messages: list[LLMMessage] = []

            # Add system prompt if provided
            if params.systemPrompt:
                autogen_messages.append(SystemMessage(content=params.systemPrompt))

            # Parse sampling messages
            for msg in params.messages:
                autogen_messages.append(parse_sampling_message(msg, model_info=self._model_client.model_info))

            # Use the model client to generate a response
            extra_create_args = create_request_params_to_extra_create_args(params)

            response = await self._model_client.create(messages=autogen_messages, extra_create_args=extra_create_args)

            # Extract text content from response
            if isinstance(response.content, str):
                response_text = response.content
            else:
                from pydantic_core import to_json

                # Handle function calls - convert to string representation
                response_text = to_json(response.content).decode()

            return mcp_types.CreateMessageResult(
                role="assistant",
                content=mcp_types.TextContent(type="text", text=response_text),
                model=self._model_client.model_info["family"],
                stopReason=finish_reason_to_stop_reason(response.finish_reason),
            )
        except Exception as e:
            return mcp_types.ErrorData(
                code=mcp_types.INTERNAL_ERROR,
                message=f"Sampling request failed: {str(e)}",
            )

    async def handle_elicit_request(
        self, params: mcp_types.ElicitRequestParams
    ) -> mcp_types.ElicitResult | mcp_types.ErrorData:
        """Handle an elicitation request from MCP servers.

        Forwards the elicitation request to the configured elicitor for processing.
        The elicitor handles the structured prompting and response collection.

        Args:
            params: The elicitation request containing prompts and parameters.

        Returns:
            An elicitation response with the structured result or error data.
        """
        if self._elicitor is None:
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No elicitor configured for this host",
            )

        try:
            response = await self._elicitor.elicit(params)
            return mcp_types.ElicitResult.model_validate(response)
        except Exception as e:
            return mcp_types.ErrorData(
                code=mcp_types.INTERNAL_ERROR,
                message=f"Elicitation request failed: {str(e)}",
            )

    async def handle_list_roots_request(self) -> mcp_types.ListRootsResult | mcp_types.ErrorData:
        """Handle a list roots request from MCP servers.

        Returns the configured file system roots that are available for server access.
        Supports both static root lists and callable root providers.

        Returns:
            A list roots response containing available roots or error data.
        """
        if self._roots is None:
            return mcp_types.ErrorData(code=mcp_types.INVALID_REQUEST, message="Host does not support listing roots")
        else:
            try:
                if callable(self._roots):
                    roots = self._roots()
                    if inspect.isawaitable(roots):
                        roots = await roots
                else:
                    roots = self._roots

                return mcp_types.ListRootsResult(roots=list(roots))
            except Exception as e:
                return mcp_types.ErrorData(code=mcp_types.INTERNAL_ERROR, message=f"Caught error listing roots: {e}")

    def _to_config(self) -> BaseModel:
        return McpSessionHostConfig(
            model_client=self._model_client.dump_component() if self._model_client else None,
            elicitor=self._elicitor.dump_component() if self._elicitor else None,
            roots=list(self._roots) if (self._roots and not callable(self._roots)) else None,
        )

    @classmethod
    def _from_config(cls, config: McpSessionHostConfig) -> "McpSessionHost":
        return cls(
            model_client=ChatCompletionClient.load_component(config.model_client) if config.model_client else None,
            elicitor=Elicitor.load_component(config.elicitor) if config.elicitor else None,
            roots=config.roots,
        )
