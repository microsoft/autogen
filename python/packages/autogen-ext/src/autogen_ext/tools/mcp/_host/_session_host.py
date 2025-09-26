from typing import Any, Dict

from autogen_core import Component, ComponentBase, ComponentModel
from pydantic import BaseModel

from mcp import types as mcp_types

from ._elicitation import Elicitor
from ._roots import RootsProvider
from ._sampling import Sampler


class McpSessionHostConfig(BaseModel):
    """Configuration for MCP session host components.

    Args:
        model_client: Optional chat completion client for sampling requests
        elicitor: Optional elicitor component for handling elicitation requests
        roots: Optional list of file system roots or roots provider
    """

    sampler: ComponentModel | Dict[str, Any] | None
    elicitor: ComponentModel | Dict[str, Any] | None
    roots: ComponentModel | Dict[str, Any] | None


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
            from autogen_ext.tools.mcp import (
                ChatCompletionClientSampler,
                McpSessionHost,
                McpWorkbench,
                StaticRootsProvider,
                StdioElicitor,
                StdioServerParams,
            )
            from pydantic import FileUrl

            from mcp.types import Root

            # Setup model client for sampling
            model_client = OpenAIChatCompletionClient(model="gpt-4o")
            sampler = ChatCompletionClientSampler(model_client)

            # Create elicitor that prompts for user input over stdio
            elicitor = StdioElicitor()

            # Provide static roots in the host system
            roots = StaticRootsProvider(
                [Root(uri=FileUrl("file:///home"), name="Home"), Root(uri=FileUrl("file:///tmp"), name="Tmp")]
            )

            # Create MCP session host with sampling, elicitation, and list_roots capabilities
            # If you want to support roots, import or define Root and FileUrl, then uncomment the roots line below
            host = McpSessionHost(
                sampler=sampler,  # Support sampling via model client
                elicitor=elicitor,  # Support elicitation via user_proxy
                roots=roots,
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

            # Now the AssistantAgent can support MCP servers that request sampling, elicitation, and roots!
    """

    component_type = "mcp_session_host"
    component_config_schema = McpSessionHostConfig
    component_provider_override = "autogen_ext.tools.mcp.McpSessionHost"

    def __init__(
        self,
        sampler: Sampler | None = None,
        roots: RootsProvider | None = None,
        elicitor: Elicitor | None = None,
    ):
        """Initialize the MCP session host.

        Args:
            sampler: Optional sampler handling sampling requests.
            roots: Optional roots provider for returning roots for file system access.
            elicitor: Optional elicitor for handling elicitation requests.
        """
        self._sampler = sampler
        self._roots = roots
        self._elicitor = elicitor

    async def handle_sampling_request(
        self, params: mcp_types.CreateMessageRequestParams
    ) -> mcp_types.CreateMessageResult | mcp_types.ErrorData:
        """Handle a sampling request from MCP servers.

        Converts MCP messages to AutoGen format and uses the configured sampler (if any)
        to generate a response.

        Args:
            params: The sampling request containing message creation parameters.

        Returns:
            A sampling response with the generated message or error data.
        """
        if self._sampler is None:
            return mcp_types.ErrorData(
                code=mcp_types.INVALID_REQUEST,
                message="No model client available for sampling requests",
            )

        try:
            response = await self._sampler.sample(params)
            return response
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
            return await self._elicitor.elicit(params)
        except Exception as e:
            return mcp_types.ErrorData(
                code=mcp_types.INTERNAL_ERROR,
                message=f"Elicitation request failed: {str(e)}",
            )

    async def handle_list_roots_request(self) -> mcp_types.ListRootsResult | mcp_types.ErrorData:
        """Handle a list roots request from MCP servers.

        Returns the configured file system roots that are available for server access.

        Returns:
            A list roots response containing available roots or error data.
        """
        if self._roots is None:
            return mcp_types.ErrorData(code=mcp_types.INVALID_REQUEST, message="Host does not support listing roots")
        else:
            try:
                return await self._roots.list_roots()
            except Exception as e:
                return mcp_types.ErrorData(code=mcp_types.INTERNAL_ERROR, message=f"Caught error listing roots: {e}")

    def _to_config(self) -> BaseModel:
        return McpSessionHostConfig(
            sampler=self._sampler.dump_component() if self._sampler else None,
            elicitor=self._elicitor.dump_component() if self._elicitor else None,
            roots=self._roots.dump_component() if self._roots else None,
        )

    @classmethod
    def _from_config(cls, config: McpSessionHostConfig) -> "McpSessionHost":
        return cls(
            sampler=Sampler.load_component(config.sampler) if config.sampler else None,
            elicitor=Elicitor.load_component(config.elicitor) if config.elicitor else None,
            roots=RootsProvider.load_component(config.roots) if config.roots else None,
        )
