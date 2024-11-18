import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Sequence

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
from pydantic import BaseModel, Field, model_validator

from .. import EVENT_LOGGER_NAME
from ..base import Response
from ..messages import (
    AgentMessage,
    ChatMessage,
    HandoffMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class Handoff(BaseModel):
    """Handoff configuration for :class:`AssistantAgent`."""

    target: str
    """The name of the target agent to handoff to."""

    description: str = Field(default=None)
    """The description of the handoff such as the condition under which it should happen and the target agent's ability.
    If not provided, it is generated from the target agent's name."""

    name: str = Field(default=None)
    """The name of this handoff configuration. If not provided, it is generated from the target agent's name."""

    message: str = Field(default=None)
    """The message to the target agent.
    If not provided, it is generated from the target agent's name."""

    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get("description") is None:
            values["description"] = f"Handoff to {values['target']}."
        if values.get("name") is None:
            values["name"] = f"transfer_to_{values['target']}".lower()
        else:
            name = values["name"]
            if not isinstance(name, str):
                raise ValueError(f"Handoff name must be a string: {values['name']}")
            # Check if name is a valid identifier.
            if not name.isidentifier():
                raise ValueError(f"Handoff name must be a valid identifier: {values['name']}")
        if values.get("message") is None:
            values["message"] = (
                f"Transferred to {values['target']}, adopting the role of {values['target']} immediately."
            )
        return values

    @property
    def handoff_tool(self) -> Tool:
        """Create a handoff tool from this handoff configuration."""

        def _handoff_tool() -> str:
            return self.message

        return FunctionTool(_handoff_tool, name=self.name, description=self.description)


class AssistantAgent(BaseChatAgent):
    """An agent that provides assistance with tool use.

    It responds with a StopMessage when 'terminate' is detected in the response.

    Args:
        name (str): The name of the agent.
        model_client (ChatCompletionClient): The model client to use for inference.
        tools (List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None, optional): The tools to register with the agent.
        handoffs (List[Handoff | str] | None, optional): The handoff configurations for the agent, allowing it to transfer to other agents by responding with a HandoffMessage.
            If a handoff is a string, it should represent the target agent's name.
        description (str, optional): The description of the agent.
        system_message (str, optional): The system message for the model.

    Raises:
        ValueError: If tool names are not unique.
        ValueError: If handoff names are not unique.
        ValueError: If handoff names are not unique from tool names.

    Examples:

        The following example demonstrates how to create an assistant agent with
        a model client and generate a response to a simple task.

        .. code-block:: python

            import asyncio
            from autogen_core.base import CancellationToken
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")
                agent = AssistantAgent(name="assistant", model_client=model_client)

                response = await agent.on_messages(
                    [TextMessage(content="What is the capital of France?", source="user")], CancellationToken()
                )
                print(response)


            asyncio.run(main())


        The following example demonstrates how to create an assistant agent with
        a model client and a tool, generate a stream of messages for a task, and
        print the messages to the console.

        .. code-block:: python

            import asyncio
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_agentchat.task import Console
            from autogen_core.base import CancellationToken


            async def get_current_time() -> str:
                return "The current time is 12:00 PM."


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")
                agent = AssistantAgent(name="assistant", model_client=model_client, tools=[get_current_time])

                await Console(
                    agent.on_messages_stream(
                        [TextMessage(content="What is the current time?", source="user")], CancellationToken()
                    )
                )


            asyncio.run(main())

    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        handoffs: List[Handoff | str] | None = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: str = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
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
        # Check if tool names are unique.
        tool_names = [tool.name for tool in self._tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError(f"Tool names must be unique: {tool_names}")
        # Handoff tools.
        self._handoff_tools: List[Tool] = []
        self._handoffs: Dict[str, Handoff] = {}
        if handoffs is not None:
            for handoff in handoffs:
                if isinstance(handoff, str):
                    handoff = Handoff(target=handoff)
                if isinstance(handoff, Handoff):
                    self._handoff_tools.append(handoff.handoff_tool)
                    self._handoffs[handoff.name] = handoff
                else:
                    raise ValueError(f"Unsupported handoff type: {type(handoff)}")
        # Check if handoff tool names are unique.
        handoff_tool_names = [tool.name for tool in self._handoff_tools]
        if len(handoff_tool_names) != len(set(handoff_tool_names)):
            raise ValueError(f"Handoff names must be unique: {handoff_tool_names}")
        # Check if handoff tool names not in tool names.
        if any(name in tool_names for name in handoff_tool_names):
            raise ValueError(
                f"Handoff names must be unique from tool names. Handoff names: {handoff_tool_names}; tool names: {tool_names}"
            )
        self._model_context: List[LLMMessage] = []

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        """The types of messages that the assistant agent produces."""
        if self._handoffs:
            return [TextMessage, HandoffMessage]
        return [TextMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentMessage | Response, None]:
        # Add messages to the model context.
        for msg in messages:
            self._model_context.append(UserMessage(content=msg.content, source=msg.source))

        # Inner messages.
        inner_messages: List[AgentMessage] = []

        # Generate an inference result based on the current model context.
        llm_messages = self._system_messages + self._model_context
        result = await self._model_client.create(
            llm_messages, tools=self._tools + self._handoff_tools, cancellation_token=cancellation_token
        )

        # Add the response to the model context.
        self._model_context.append(AssistantMessage(content=result.content, source=self.name))

        # Run tool calls until the model produces a string response.
        while isinstance(result.content, list) and all(isinstance(item, FunctionCall) for item in result.content):
            tool_call_msg = ToolCallMessage(content=result.content, source=self.name, models_usage=result.usage)
            event_logger.debug(tool_call_msg)
            # Add the tool call message to the output.
            inner_messages.append(tool_call_msg)
            yield tool_call_msg

            # Execute the tool calls.
            results = await asyncio.gather(
                *[self._execute_tool_call(call, cancellation_token) for call in result.content]
            )
            tool_call_result_msg = ToolCallResultMessage(content=results, source=self.name)
            event_logger.debug(tool_call_result_msg)
            self._model_context.append(FunctionExecutionResultMessage(content=results))
            inner_messages.append(tool_call_result_msg)
            yield tool_call_result_msg

            # Detect handoff requests.
            handoffs: List[Handoff] = []
            for call in result.content:
                if call.name in self._handoffs:
                    handoffs.append(self._handoffs[call.name])
            if len(handoffs) > 0:
                if len(handoffs) > 1:
                    raise ValueError(f"Multiple handoffs detected: {[handoff.name for handoff in handoffs]}")
                # Return the output messages to signal the handoff.
                yield Response(
                    chat_message=HandoffMessage(
                        content=handoffs[0].message, target=handoffs[0].target, source=self.name
                    ),
                    inner_messages=inner_messages,
                )
                return

            # Generate an inference result based on the current model context.
            result = await self._model_client.create(
                self._model_context, tools=self._tools + self._handoff_tools, cancellation_token=cancellation_token
            )
            self._model_context.append(AssistantMessage(content=result.content, source=self.name))

        assert isinstance(result.content, str)
        yield Response(
            chat_message=TextMessage(content=result.content, source=self.name, models_usage=result.usage),
            inner_messages=inner_messages,
        )

    async def _execute_tool_call(
        self, tool_call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        """Execute a tool call and return the result."""
        try:
            if not self._tools + self._handoff_tools:
                raise ValueError("No tools are available.")
            tool = next((t for t in self._tools + self._handoff_tools if t.name == tool_call.name), None)
            if tool is None:
                raise ValueError(f"The tool '{tool_call.name}' is not available.")
            arguments = json.loads(tool_call.arguments)
            result = await tool.run_json(arguments, cancellation_token)
            result_as_str = tool.return_value_as_string(result)
            return FunctionExecutionResult(content=result_as_str, call_id=tool_call.id)
        except Exception as e:
            return FunctionExecutionResult(content=f"Error: {e}", call_id=tool_call.id)

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the assistant agent to its initialization state."""
        self._model_context.clear()
