import asyncio
import json
import logging
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Sequence,
    Tuple,
)

from autogen_core import CancellationToken, Component, ComponentModel, FunctionCall
from autogen_core.memory import Memory
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import BaseTool, FunctionTool
from pydantic import BaseModel
from typing_extensions import Self

from .. import EVENT_LOGGER_NAME
from ..base import Handoff as HandoffBase
from ..base import Response
from ..messages import (
    AgentEvent,
    ChatMessage,
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from ..state import AssistantAgentState
from ..utils import remove_images
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class AssistantAgentConfig(BaseModel):
    """The declarative configuration for the assistant agent."""

    name: str
    model_client: ComponentModel
    tools: List[ComponentModel] | None
    handoffs: List[HandoffBase | str] | None = None
    model_context: ComponentModel | None = None
    memory: List[ComponentModel] | None = None
    description: str
    system_message: str | None = None
    model_client_stream: bool = False
    reflect_on_tool_use: bool
    tool_call_summary_format: str


class AssistantAgent(BaseChatAgent, Component[AssistantAgentConfig]):
    """An agent that provides assistance with tool use.

    The :meth:`on_messages` returns a :class:`~autogen_agentchat.base.Response`
    in which :attr:`~autogen_agentchat.base.Response.chat_message` is the final
    response message.

    The :meth:`on_messages_stream` creates an async generator that produces
    the inner messages as they are created, and the :class:`~autogen_agentchat.base.Response`
    object as the last item before closing the generator.

    .. attention::

        The caller must only pass the new messages to the agent on each call
        to the :meth:`on_messages` or :meth:`on_messages_stream` method.
        The agent maintains its state between calls to these methods.
        Do not pass the entire conversation history to the agent on each call.

    .. warning::
        The assistant agent is not thread-safe or coroutine-safe.
        It should not be shared between multiple tasks or coroutines, and it should
        not call its methods concurrently.

    The following diagram shows how the assistant agent works:

    .. image:: ../../images/assistant-agent.svg

    Tool call behavior:

    * If the model returns no tool call, then the response is immediately returned as a :class:`~autogen_agentchat.messages.TextMessage` in :attr:`~autogen_agentchat.base.Response.chat_message`.
    * When the model returns tool calls, they will be executed right away:
        - When `reflect_on_tool_use` is False (default), the tool call results are returned as a :class:`~autogen_agentchat.messages.ToolCallSummaryMessage` in :attr:`~autogen_agentchat.base.Response.chat_message`. `tool_call_summary_format` can be used to customize the tool call summary.
        - When `reflect_on_tool_use` is True, the another model inference is made using the tool calls and results, and the text response is returned as a :class:`~autogen_agentchat.messages.TextMessage` in :attr:`~autogen_agentchat.base.Response.chat_message`.
    * If the model returns multiple tool calls, they will be executed concurrently. To disable parallel tool calls you need to configure the model client. For example, set `parallel_tool_calls=False` for :class:`~autogen_ext.models.openai.OpenAIChatCompletionClient` and :class:`~autogen_ext.models.openai.AzureOpenAIChatCompletionClient`.

    .. tip::
        By default, the tool call results are returned as response when tool calls are made.
        So it is recommended to pay attention to the formatting of the tools return values,
        especially if another agent is expecting them in a specific format.
        Use `tool_call_summary_format` to customize the tool call summary, if needed.

    Hand off behavior:

    * If a handoff is triggered, a :class:`~autogen_agentchat.messages.HandoffMessage` will be returned in :attr:`~autogen_agentchat.base.Response.chat_message`.
    * If there are tool calls, they will also be executed right away before returning the handoff.
    * The tool calls and results are passed to the target agent through :attr:`~autogen_agentchat.messages.HandoffMessage.context`.


    .. note::
        If multiple handoffs are detected, only the first handoff is executed.
        To avoid this, disable parallel tool calls in the model client configuration.


    Limit context size sent to the model:

    You can limit the number of messages sent to the model by setting
    the `model_context` parameter to a :class:`~autogen_core.model_context.BufferedChatCompletionContext`.
    This will limit the number of recent messages sent to the model and can be useful
    when the model has a limit on the number of tokens it can process.

    Streaming mode:

    The assistant agent can be used in streaming mode by setting `model_client_stream=True`.
    In this mode, the :meth:`on_messages_stream` and :meth:`BaseChatAgent.run_stream` methods will also yield
    :class:`~autogen_agentchat.messages.ModelClientStreamingChunkEvent`
    messages as the model client produces chunks of response.
    The chunk messages will not be included in the final response's inner messages.


    Args:
        name (str): The name of the agent.
        model_client (ChatCompletionClient): The model client to use for inference.
        tools (List[BaseTool[Any, Any]  | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None, optional): The tools to register with the agent.
        handoffs (List[HandoffBase | str] | None, optional): The handoff configurations for the agent,
            allowing it to transfer to other agents by responding with a :class:`HandoffMessage`.
            The transfer is only executed when the team is in :class:`~autogen_agentchat.teams.Swarm`.
            If a handoff is a string, it should represent the target agent's name.
        model_context (ChatCompletionContext | None, optional): The model context for storing and retrieving :class:`~autogen_core.models.LLMMessage`. It can be preloaded with initial messages. The initial messages will be cleared when the agent is reset.
        description (str, optional): The description of the agent.
        system_message (str, optional): The system message for the model. If provided, it will be prepended to the messages in the model context when making an inference. Set to `None` to disable.
        model_client_stream (bool, optional): If `True`, the model client will be used in streaming mode.
            :meth:`on_messages_stream` and :meth:`BaseChatAgent.run_stream` methods will also yield :class:`~autogen_agentchat.messages.ModelClientStreamingChunkEvent`
            messages as the model client produces chunks of response. Defaults to `False`.
        reflect_on_tool_use (bool, optional): If `True`, the agent will make another model inference using the tool call and result
            to generate a response. If `False`, the tool call result will be returned as the response. Defaults to `False`.
        tool_call_summary_format (str, optional): The format string used to create a tool call summary for every tool call result.
            Defaults to "{result}".
            When `reflect_on_tool_use` is `False`, a concatenation of all the tool call summaries, separated by a new line character ('\\n')
            will be returned as the response.
            Available variables: `{tool_name}`, `{arguments}`, `{result}`.
            For example, `"{tool_name}: {result}"` will create a summary like `"tool_name: result"`.
        memory (Sequence[Memory] | None, optional): The memory store to use for the agent. Defaults to `None`.

    Raises:
        ValueError: If tool names are not unique.
        ValueError: If handoff names are not unique.
        ValueError: If handoff names are not unique from tool names.
        ValueError: If maximum number of tool iterations is less than 1.

    Examples:

        The following example demonstrates how to create an assistant agent with
        a model client and generate a response to a simple task.

        .. code-block:: python

            import asyncio
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )
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
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_agentchat.ui import Console
            from autogen_core import CancellationToken


            async def get_current_time() -> str:
                return "The current time is 12:00 PM."


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )
                agent = AssistantAgent(name="assistant", model_client=model_client, tools=[get_current_time])

                await Console(
                    agent.on_messages_stream(
                        [TextMessage(content="What is the current time?", source="user")], CancellationToken()
                    )
                )


            asyncio.run(main())


        The following example shows how to use `o1-mini` model with the assistant agent.

        .. code-block:: python

            import asyncio
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="o1-mini",
                    # api_key = "your_openai_api_key"
                )
                # The system message is not supported by the o1 series model.
                agent = AssistantAgent(name="assistant", model_client=model_client, system_message=None)

                response = await agent.on_messages(
                    [TextMessage(content="What is the capital of France?", source="user")], CancellationToken()
                )
                print(response)


            asyncio.run(main())

        .. note::

            The `o1-preview` and `o1-mini` models do not support system message and function calling.
            So the `system_message` should be set to `None` and the `tools` and `handoffs` should not be set.
            See `o1 beta limitations <https://platform.openai.com/docs/guides/reasoning#beta-limitations>`_ for more details.
    """

    component_config_schema = AssistantAgentConfig
    component_provider_override = "autogen_agentchat.agents.AssistantAgent"

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        handoffs: List[HandoffBase | str] | None = None,
        model_context: ChatCompletionContext | None = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: (
            str | None
        ) = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
        model_client_stream: bool = False,
        reflect_on_tool_use: bool = False,
        tool_call_summary_format: str = "{result}",
        memory: Sequence[Memory] | None = None,
    ):
        super().__init__(name=name, description=description)
        self._model_client = model_client
        self._model_client_stream = model_client_stream
        self._memory = None
        if memory is not None:
            if isinstance(memory, list):
                self._memory = memory
            else:
                raise TypeError(f"Expected Memory, List[Memory], or None, got {type(memory)}")

        self._system_messages: List[
            SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage
        ] = []
        if system_message is None:
            self._system_messages = []
        else:
            self._system_messages = [SystemMessage(content=system_message)]
        self._tools: List[BaseTool[Any, Any]] = []
        if tools is not None:
            if model_client.model_info["function_calling"] is False:
                raise ValueError("The model does not support function calling.")
            for tool in tools:
                if isinstance(tool, BaseTool):
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
        self._handoff_tools: List[BaseTool[Any, Any]] = []
        self._handoffs: Dict[str, HandoffBase] = {}
        if handoffs is not None:
            if model_client.model_info["function_calling"] is False:
                raise ValueError("The model does not support function calling, which is needed for handoffs.")
            for handoff in handoffs:
                if isinstance(handoff, str):
                    handoff = HandoffBase(target=handoff)
                if isinstance(handoff, HandoffBase):
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
        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()
        self._reflect_on_tool_use = reflect_on_tool_use
        self._tool_call_summary_format = tool_call_summary_format
        self._is_running = False

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of final response messages that the assistant agent produces."""
        message_types: List[type[ChatMessage]] = [TextMessage]
        if self._handoffs:
            message_types.append(HandoffMessage)
        if self._tools:
            message_types.append(ToolCallSummaryMessage)
        return tuple(message_types)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        # Add messages to the model context.
        for msg in messages:
            if isinstance(msg, HandoffMessage):
                # Add handoff context to the model context.
                for context_msg in msg.context:
                    await self._model_context.add_message(context_msg)
            await self._model_context.add_message(UserMessage(content=msg.content, source=msg.source))

        # Inner messages.
        inner_messages: List[AgentEvent | ChatMessage] = []

        # Update the model context with memory content.
        if self._memory:
            for memory in self._memory:
                update_context_result = await memory.update_context(self._model_context)
                if update_context_result and len(update_context_result.memories.results) > 0:
                    memory_query_event_msg = MemoryQueryEvent(
                        content=update_context_result.memories.results, source=self.name
                    )
                    inner_messages.append(memory_query_event_msg)
                    yield memory_query_event_msg

        # Generate an inference result based on the current model context.
        llm_messages = self._get_compatible_context(self._system_messages + await self._model_context.get_messages())
        model_result: CreateResult | None = None
        if self._model_client_stream:
            # Stream the model client.
            async for chunk in self._model_client.create_stream(
                llm_messages, tools=self._tools + self._handoff_tools, cancellation_token=cancellation_token
            ):
                if isinstance(chunk, CreateResult):
                    model_result = chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=self.name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
            assert isinstance(model_result, CreateResult)
        else:
            model_result = await self._model_client.create(
                llm_messages, tools=self._tools + self._handoff_tools, cancellation_token=cancellation_token
            )

        # Add the response to the model context.
        await self._model_context.add_message(AssistantMessage(content=model_result.content, source=self.name))

        # Check if the response is a string and return it.
        if isinstance(model_result.content, str):
            yield Response(
                chat_message=TextMessage(
                    content=model_result.content, source=self.name, models_usage=model_result.usage
                ),
                inner_messages=inner_messages,
            )
            return

        # Process tool calls.
        assert isinstance(model_result.content, list) and all(
            isinstance(item, FunctionCall) for item in model_result.content
        )
        tool_call_msg = ToolCallRequestEvent(
            content=model_result.content, source=self.name, models_usage=model_result.usage
        )
        event_logger.debug(tool_call_msg)
        # Add the tool call message to the output.
        inner_messages.append(tool_call_msg)
        yield tool_call_msg

        # Execute the tool calls and hanoff calls.
        executed_calls_and_results = await asyncio.gather(
            *[self._execute_tool_call(call, cancellation_token) for call in model_result.content]
        )
        # Collect the execution results in a list.
        exec_results = [result for _, result in executed_calls_and_results]
        # Add the execution results to output and model context.
        tool_call_result_msg = ToolCallExecutionEvent(content=exec_results, source=self.name)
        event_logger.debug(tool_call_result_msg)
        await self._model_context.add_message(FunctionExecutionResultMessage(content=exec_results))
        inner_messages.append(tool_call_result_msg)
        yield tool_call_result_msg

        # Separate out tool calls and tool call results from handoff requests.
        tool_calls: List[FunctionCall] = []
        tool_call_results: List[FunctionExecutionResult] = []
        for exec_call, exec_result in executed_calls_and_results:
            if exec_call.name not in self._handoffs:
                tool_calls.append(exec_call)
                tool_call_results.append(exec_result)

        # Detect handoff requests.
        handoff_reqs = [call for call in model_result.content if call.name in self._handoffs]
        if len(handoff_reqs) > 0:
            handoffs = [self._handoffs[call.name] for call in handoff_reqs]
            if len(handoffs) > 1:
                # show warning if multiple handoffs detected
                warnings.warn(
                    (
                        f"Multiple handoffs detected only the first is executed: {[handoff.name for handoff in handoffs]}. "
                        "Disable parallel tool call in the model client to avoid this warning."
                    ),
                    stacklevel=2,
                )
            # Current context for handoff.
            handoff_context: List[LLMMessage] = []
            if len(tool_calls) > 0:
                handoff_context.append(AssistantMessage(content=tool_calls, source=self.name))
                handoff_context.append(FunctionExecutionResultMessage(content=tool_call_results))
            # Return the output messages to signal the handoff.
            yield Response(
                chat_message=HandoffMessage(
                    content=handoffs[0].message, target=handoffs[0].target, source=self.name, context=handoff_context
                ),
                inner_messages=inner_messages,
            )
            return

        if self._reflect_on_tool_use:
            # Generate another inference result based on the tool call and result.
            llm_messages = self._get_compatible_context(
                self._system_messages + await self._model_context.get_messages()
            )
            reflection_model_result: CreateResult | None = None
            if self._model_client_stream:
                # Stream the model client.
                async for chunk in self._model_client.create_stream(
                    llm_messages, cancellation_token=cancellation_token
                ):
                    if isinstance(chunk, CreateResult):
                        reflection_model_result = chunk
                    elif isinstance(chunk, str):
                        yield ModelClientStreamingChunkEvent(content=chunk, source=self.name)
                    else:
                        raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
                assert isinstance(reflection_model_result, CreateResult)
            else:
                reflection_model_result = await self._model_client.create(
                    llm_messages, cancellation_token=cancellation_token
                )
            assert isinstance(reflection_model_result.content, str)
            # Add the response to the model context.
            await self._model_context.add_message(
                AssistantMessage(content=reflection_model_result.content, source=self.name)
            )
            # Yield the response.
            yield Response(
                chat_message=TextMessage(
                    content=reflection_model_result.content,
                    source=self.name,
                    models_usage=reflection_model_result.usage,
                ),
                inner_messages=inner_messages,
            )
        else:
            # Return tool call result as the response.
            tool_call_summaries: List[str] = []
            for tool_call, tool_call_result in zip(tool_calls, tool_call_results, strict=False):
                tool_call_summaries.append(
                    self._tool_call_summary_format.format(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        result=tool_call_result.content,
                    ),
                )
            tool_call_summary = "\n".join(tool_call_summaries)
            yield Response(
                chat_message=ToolCallSummaryMessage(content=tool_call_summary, source=self.name),
                inner_messages=inner_messages,
            )

    async def _execute_tool_call(
        self, tool_call: FunctionCall, cancellation_token: CancellationToken
    ) -> Tuple[FunctionCall, FunctionExecutionResult]:
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
            return (tool_call, FunctionExecutionResult(content=result_as_str, call_id=tool_call.id, is_error=False))
        except Exception as e:
            return (tool_call, FunctionExecutionResult(content=f"Error: {e}", call_id=tool_call.id, is_error=True))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the assistant agent to its initialization state."""
        await self._model_context.clear()

    async def save_state(self) -> Mapping[str, Any]:
        """Save the current state of the assistant agent."""
        model_context_state = await self._model_context.save_state()
        return AssistantAgentState(llm_context=model_context_state).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the state of the assistant agent"""
        assistant_agent_state = AssistantAgentState.model_validate(state)
        # Load the model context state.
        await self._model_context.load_state(assistant_agent_state.llm_context)

    def _get_compatible_context(self, messages: List[LLMMessage]) -> Sequence[LLMMessage]:
        """Ensure that the messages are compatible with the underlying client, by removing images if needed."""
        if self._model_client.model_info["vision"]:
            return messages
        else:
            return remove_images(messages)

    def _to_config(self) -> AssistantAgentConfig:
        """Convert the assistant agent to a declarative config."""

        return AssistantAgentConfig(
            name=self.name,
            model_client=self._model_client.dump_component(),
            tools=[tool.dump_component() for tool in self._tools],
            handoffs=list(self._handoffs.values()),
            model_context=self._model_context.dump_component(),
            memory=[memory.dump_component() for memory in self._memory] if self._memory else None,
            description=self.description,
            system_message=self._system_messages[0].content
            if self._system_messages and isinstance(self._system_messages[0].content, str)
            else None,
            model_client_stream=self._model_client_stream,
            reflect_on_tool_use=self._reflect_on_tool_use,
            tool_call_summary_format=self._tool_call_summary_format,
        )

    @classmethod
    def _from_config(cls, config: AssistantAgentConfig) -> Self:
        """Create an assistant agent from a declarative config."""
        return cls(
            name=config.name,
            model_client=ChatCompletionClient.load_component(config.model_client),
            tools=[BaseTool.load_component(tool) for tool in config.tools] if config.tools else None,
            handoffs=config.handoffs,
            model_context=None,
            memory=[Memory.load_component(memory) for memory in config.memory] if config.memory else None,
            description=config.description,
            system_message=config.system_message,
            model_client_stream=config.model_client_stream,
            reflect_on_tool_use=config.reflect_on_tool_use,
            tool_call_summary_format=config.tool_call_summary_format,
        )
