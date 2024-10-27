import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tools import FunctionTool, Tool
from pydantic import BaseModel, ConfigDict

from .. import EVENT_LOGGER_NAME
from ..messages import (
    ChatMessage,
    StopMessage,
    TextMessage,
)
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class ToolCallEvent(BaseModel):
    """A tool call event."""

    tool_calls: List[FunctionCall]
    """The tool call message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolCallResultEvent(BaseModel):
    """A tool call result event."""

    tool_call_results: List[FunctionExecutionResult]
    """The tool call result message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AssistantAgent(BaseChatAgent):
    """An agent that provides assistance with tool use.

    It responds with a StopMessage when 'terminate' is detected in the response.

    Args:
        name (str): The name of the agent.
        model_client (ChatCompletionClient): The model client to use for inference.
        tools (List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None, optional): The tools to register with the agent.
        description (str, optional): The description of the agent.
        system_message (str, optional): The system message for the model.
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: str = "You are a helpful AI assistant. Solve tasks using your tools. Reply with 'TERMINATE' when the task has been completed.",
    ):
        super().__init__(name=name, description=description)
        self._model_client = model_client
        self._system_messages = [SystemMessage(content=system_message)]
        self._tools: List[Tool] = []
        if tools is not None:
            for tool in tools:
                if isinstance(tool, Tool):
                    self._tools.append(tool)
                elif callable(tool):
                    if hasattr(tool, "__doc__") and tool.__doc__ is not None:
                        description = tool.__doc__
                    else:
                        description = ""
                    self._tools.append(FunctionTool(tool, description=description))
                else:
                    raise ValueError(f"Unsupported tool type: {type(tool)}")
        self._model_context: List[LLMMessage] = []

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        # Add messages to the model context.
        for msg in messages:
            # TODO: add special handling for handoff messages
            self._model_context.append(UserMessage(content=msg.content, source=msg.source))

        # Generate an inference result based on the current model context.
        llm_messages = self._system_messages + self._model_context
        result = await self._model_client.create(llm_messages, tools=self._tools, cancellation_token=cancellation_token)

        # Add the response to the model context.
        self._model_context.append(AssistantMessage(content=result.content, source=self.name))

        # Run tool calls until the model produces a string response.
        while isinstance(result.content, list) and all(isinstance(item, FunctionCall) for item in result.content):
            event_logger.debug(ToolCallEvent(tool_calls=result.content))
            # Execute the tool calls.
            results = await asyncio.gather(
                *[self._execute_tool_call(call, cancellation_token) for call in result.content]
            )
            event_logger.debug(ToolCallResultEvent(tool_call_results=results))
            self._model_context.append(FunctionExecutionResultMessage(content=results))
            # Generate an inference result based on the current model context.
            result = await self._model_client.create(
                self._model_context, tools=self._tools, cancellation_token=cancellation_token
            )
            self._model_context.append(AssistantMessage(content=result.content, source=self.name))

        assert isinstance(result.content, str)
        # Detect stop request.
        request_stop = "terminate" in result.content.strip().lower()
        if request_stop:
            return StopMessage(content=result.content, source=self.name)

        return TextMessage(content=result.content, source=self.name)

    async def _execute_tool_call(
        self, tool_call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        """Execute a tool call and return the result."""
        try:
            if not self._tools:
                raise ValueError("No tools are available.")
            tool = next((t for t in self._tools if t.name == tool_call.name), None)
            if tool is None:
                raise ValueError(f"The tool '{tool_call.name}' is not available.")
            arguments = json.loads(tool_call.arguments)
            result = await tool.run_json(arguments, cancellation_token)
            result_as_str = tool.return_value_as_string(result)
            return FunctionExecutionResult(content=result_as_str, call_id=tool_call.id)
        except Exception as e:
            return FunctionExecutionResult(content=f"Error: {e}", call_id=tool_call.id)
