from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff as HandoffBase
from autogen_core.memory import Memory
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import BaseTool, Workbench
from pydantic import BaseModel

from mcp import types as mcp_types

from ...tools.mcp._base import ElicitorTypes
from ...tools.mcp._host import McpWorkbenchHost


class McpAssistantAgent(AssistantAgent, McpWorkbenchHost):
    """An assistant agent that combines AssistantAgent functionality with MCP workbench hosting.

    This agent inherits from both AssistantAgent and McpWorkbenchHost, providing:
    - Full AssistantAgent capabilities (chat, tools, handoffs, memory, etc.)
    - MCP workbench hosting (sampling, elicitation, listing roots)

    The agent can serve as an MCP workbench host while maintaining all the standard
    assistant agent functionality.
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        workbench: Workbench | Sequence[Workbench] | None = None,
        handoffs: List[HandoffBase | str] | None = None,
        model_context: ChatCompletionContext | None = None,
        description: str = "An MCP-enabled assistant agent that provides assistance with ability to use tools and host MCP workbenches.",
        system_message: str
        | None = "You are a helpful AI assistant with MCP capabilities. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
        model_client_stream: bool = False,
        reflect_on_tool_use: bool | None = None,
        max_tool_iterations: int = 1,
        tool_call_summary_format: str = "{result}",
        tool_call_summary_formatter: Callable[[Any, Any], str] | None = None,
        output_content_type: type[BaseModel] | None = None,
        output_content_type_format: str | None = None,
        memory: Sequence[Memory] | None = None,
        metadata: Dict[str, str] | None = None,
        # MCP-specific parameters
        roots: Sequence[mcp_types.Root] | Callable[[], Sequence[mcp_types.Root]] | None = None,
        elicitor: ElicitorTypes | None = None,
    ):
        """Initialize the MCP Assistant Agent.

        Args:
            name: The name of the agent.
            model_client: The model client to use for inference.
            tools: The tools to register with the agent.
            workbench: The workbench or list of workbenches to use for the agent.
            handoffs: The handoff configurations for the agent.
            model_context: The model context for storing and retrieving messages.
            description: The description of the agent.
            system_message: The system message for the model.
            model_client_stream: If True, the model client will be used in streaming mode.
            reflect_on_tool_use: If True, the agent will reflect on tool use.
            max_tool_iterations: The maximum number of tool iterations.
            tool_call_summary_format: Static format string for tool call summaries.
            tool_call_summary_formatter: Callable for formatting tool call summaries.
            output_content_type: The output content type for structured messages.
            output_content_type_format: The format string for structured message content.
            memory: The memory store to use for the agent.
            metadata: Optional metadata for tracking.
            roots: MCP roots for the workbench host.
            elicitor: The elicitor function or agent ID for handling input elicitation.
        """
        # Initialize McpWorkbenchHost before AssistantAgent
        McpWorkbenchHost.__init__(self, model_client=model_client, roots=roots, elicitor=elicitor)

        # Initialize AssistantAgent
        super().__init__(
            name=name,
            model_client=model_client,
            tools=tools,
            workbench=workbench,
            handoffs=handoffs,
            model_context=model_context,
            description=description,
            system_message=system_message,
            model_client_stream=model_client_stream,
            reflect_on_tool_use=reflect_on_tool_use,
            max_tool_iterations=max_tool_iterations,
            tool_call_summary_format=tool_call_summary_format,
            tool_call_summary_formatter=tool_call_summary_formatter,
            output_content_type=output_content_type,
            output_content_type_format=output_content_type_format,
            memory=memory,
            metadata=metadata,
        )
