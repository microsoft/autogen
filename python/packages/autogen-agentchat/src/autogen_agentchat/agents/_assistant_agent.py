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
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
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
    ModelFamily,
    SystemMessage,
)
from autogen_core.tools import BaseTool, FunctionTool, StaticWorkbench, Workbench
from pydantic import BaseModel
from typing_extensions import Self

from .. import EVENT_LOGGER_NAME
from ..base import Handoff as HandoffBase
from ..base import Response
from ..messages import (
    BaseAgentEvent,
    BaseChatMessage,
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    StructuredMessage,
    StructuredMessageFactory,
    TextMessage,
    ThoughtEvent,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from ..state import AssistantAgentState
from ..utils import remove_images
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)

# Add type variables for more specific typing
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


class ToolCallConfig(BaseModel):
    """Configuration for tool call behavior in AssistantAgent.

    .. versionadded:: v0.4.1

       Added for future extensibility of tool call loop functionality.
    """

    max_iterations: int = 10
    """Maximum number of tool call iterations to prevent infinite loops."""


class AssistantAgentConfig(BaseModel):
    """The declarative configuration for the assistant agent."""

    name: str
    model_client: ComponentModel
    tools: List[ComponentModel] | None = None
    workbench: List[ComponentModel] | None = None
    handoffs: List[HandoffBase | str] | None = None
    model_context: ComponentModel | None = None
    memory: List[ComponentModel] | None = None
    description: str
    system_message: str | None = None
    model_client_stream: bool = False
    reflect_on_tool_use: bool
    tool_call_summary_format: str
    tool_call_loop_config: ToolCallConfig | None = None
    """Configuration for tool call loop behavior.

    .. versionadded:: v0.4.1
    """
    metadata: Dict[str, str] | None = None
    structured_message_factory: ComponentModel | None = None


class AssistantAgent(BaseChatAgent, Component[AssistantAgentConfig]):
    """An agent that provides assistance with tool use.

    The agent processes messages and returns responses, with capabilities for tool execution,
    handoffs to other agents, memory management, and real-time streaming.

    Key Features:
    - Tool execution with reflection
    - Structured output support
    - Memory integration
    - Streaming capabilities
    - Model context management

    Args:
        name: The name of the agent
        model_client: Model client for inference
        tools: Optional list of tools to register
        workbench: Optional workbench(s) (mutually exclusive with tools)
        handoffs: Optional handoff configurations
        model_context: Optional context for LLM messages
        description: Optional agent description
        system_message: Optional system message
        model_client_stream: Enable streaming mode
        reflect_on_tool_use: Enable tool usage reflection
        tool_call_loop_config: Tool call loop settings
        tool_call_summary_format: Tool call summary format
        tool_call_summary_formatter: Custom formatter
        output_content_type: Structured output type
        output_content_type_format: Structured output format
        memory: Optional memory stores
        metadata: Optional metadata

    Raises:
        ValueError: For invalid configurations:
            - Non-unique tool names
            - Non-unique handoff names
            - Tool/handoff name conflicts
            - Invalid iteration count

    For detailed examples and usage, see the Examples section below.
    """

    component_version = 2
    component_config_schema = AssistantAgentConfig
    component_provider_override = "autogen_agentchat.agents.AssistantAgent"

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: Optional[List[Union[BaseTool[Any, Any], Callable[..., Awaitable[Any]], Callable[..., Any]]]] = None,
        workbench: Optional[Union[Workbench, Sequence[Workbench]]] = None,
        handoffs: Optional[List[Union[HandoffBase, str]]] = None,
        model_context: Optional[ChatCompletionContext] = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: Optional[
            str
        ] = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
        model_client_stream: bool = False,
        reflect_on_tool_use: Optional[bool] = None,
        tool_call_loop_config: Optional[ToolCallConfig] = None,
        tool_call_summary_format: str = "{result}",
        tool_call_summary_formatter: Optional[Callable[[FunctionCall, FunctionExecutionResult], str]] = None,
        output_content_type: Optional[type[BaseModel]] = None,
        output_content_type_format: Optional[str] = None,
        memory: Optional[Sequence[Memory]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(name=name, description=description)
        self._metadata = metadata or {}
        self._model_client = model_client
        self._model_client_stream = model_client_stream
        self._output_content_type: type[BaseModel] | None = output_content_type
        self._output_content_type_format = output_content_type_format
        self._structured_message_factory: StructuredMessageFactory | None = None
        if output_content_type is not None:
            self._structured_message_factory = StructuredMessageFactory(
                input_model=output_content_type, format_string=output_content_type_format
            )

        self._memory = None
        if memory is not None:
            if isinstance(memory, list):
                self._memory = memory
            else:
                raise TypeError(f"Expected Memory, List[Memory], or None, got {type(memory)}")

        self._system_messages: List[SystemMessage] = []
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
                f"Handoff names must be unique from tool names. "
                f"Handoff names: {handoff_tool_names}; tool names: {tool_names}"
            )

        if workbench is not None:
            if self._tools:
                raise ValueError("Tools cannot be used with a workbench.")
            if isinstance(workbench, Sequence):
                self._workbench = workbench
            else:
                self._workbench = [workbench]
        else:
            self._workbench = [StaticWorkbench(self._tools)]

        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()

        if self._output_content_type is not None and reflect_on_tool_use is None:
            # If output_content_type is set, we need to reflect on tool use by default.
            self._reflect_on_tool_use = True
        elif reflect_on_tool_use is None:
            self._reflect_on_tool_use = False
        else:
            self._reflect_on_tool_use = reflect_on_tool_use
        if self._reflect_on_tool_use and ModelFamily.is_claude(model_client.model_info["family"]):
            warnings.warn(
                "Claude models may not work with reflection on tool use because Claude requires that any requests including a previous tool use or tool result must include the original tools definition."
                "Consider setting reflect_on_tool_use to False. "
                "As an alternative, consider calling the agent in a loop until it stops producing tool calls. "
                "See [Single-Agent Team](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html#single-agent-team) "
                "for more details.",
                UserWarning,
                stacklevel=2,
            )

        # Tool call loop configuration
        self._tool_call_loop_config = tool_call_loop_config

        # Validate tool call configuration
        if self._tool_call_loop_config and self._tool_call_loop_config.max_iterations < 1:
            raise ValueError("Maximum number of tool iterations must be at least 1")

        self._tool_call_summary_format = tool_call_summary_format
        self._tool_call_summary_formatter = tool_call_summary_formatter
        self._is_running = False

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        """Get the types of messages this agent can produce.

        Returns:
            Sequence of message types this agent can generate
        """
        types: List[type[BaseChatMessage]] = [TextMessage, ToolCallSummaryMessage, HandoffMessage]
        if self._structured_message_factory is not None:
            types.append(StructuredMessage)
        return types

    @property
    def model_context(self) -> ChatCompletionContext:
        """Get the model context used by this agent.

        Returns:
            The chat completion context for this agent
        """
        return self._model_context

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        """Process incoming messages and generate a response.

        Args:
            messages: Sequence of messages to process
            cancellation_token: Token for cancelling operation

        Returns:
            Response containing the agent's reply
        """
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[Union[BaseAgentEvent, BaseChatMessage, Response], None]:
        """Process messages and stream the response.

        Args:
            messages: Sequence of messages to process
            cancellation_token: Token for cancelling operation

        Yields:
            Events, messages and final response during processing
        """

        # Gather all relevant state here
        agent_name = self.name
        model_context = self._model_context
        memory = self._memory
        system_messages = self._system_messages
        workbench = self._workbench
        handoff_tools = self._handoff_tools
        handoffs = self._handoffs
        model_client = self._model_client
        model_client_stream = self._model_client_stream
        reflect_on_tool_use = self._reflect_on_tool_use
        tool_call_loop_config = self._tool_call_loop_config
        tool_call_summary_format = self._tool_call_summary_format
        tool_call_summary_formatter = self._tool_call_summary_formatter
        output_content_type = self._output_content_type

        # STEP 1: Add new user/handoff messages to the model context
        await self._add_messages_to_context(
            model_context=model_context,
            messages=messages,
        )

        # STEP 2: Update model context with any relevant memory
        inner_messages: List[BaseAgentEvent | BaseChatMessage] = []
        for event_msg in await self._update_model_context_with_memory(
            memory=memory,
            model_context=model_context,
            agent_name=agent_name,
        ):
            inner_messages.append(event_msg)
            yield event_msg

        # STEP 3: Run the first inference
        model_result = None
        async for inference_output in self._call_llm(
            model_client=model_client,
            model_client_stream=model_client_stream,
            system_messages=system_messages,
            model_context=model_context,
            workbench=workbench,
            handoff_tools=handoff_tools,
            agent_name=agent_name,
            cancellation_token=cancellation_token,
            output_content_type=output_content_type,
        ):
            if isinstance(inference_output, CreateResult):
                model_result = inference_output
            else:
                # Streaming chunk event
                yield inference_output

        assert model_result is not None, "No model result was produced."

        # --- NEW: If the model produced a hidden "thought," yield it as an event ---
        if model_result.thought:
            thought_event = ThoughtEvent(content=model_result.thought, source=agent_name)
            yield thought_event
            inner_messages.append(thought_event)

        # Add the assistant message to the model context (including thought if present)
        await model_context.add_message(
            AssistantMessage(
                content=model_result.content,
                source=agent_name,
                thought=getattr(model_result, "thought", None),
            )
        )

        # STEP 4: Process the model output
        async for output_event in self._process_model_result(
            model_result=model_result,
            inner_messages=inner_messages,
            cancellation_token=cancellation_token,
            agent_name=agent_name,
            system_messages=system_messages,
            model_context=model_context,
            workbench=workbench,
            handoff_tools=handoff_tools,
            handoffs=handoffs,
            model_client=model_client,
            model_client_stream=model_client_stream,
            reflect_on_tool_use=reflect_on_tool_use,
            tool_call_loop_config=tool_call_loop_config,
            tool_call_summary_format=tool_call_summary_format,
            tool_call_summary_formatter=tool_call_summary_formatter,
            output_content_type=output_content_type,
            format_string=self._output_content_type_format,
        ):
            yield output_event

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext,
        messages: Sequence[BaseChatMessage],
    ) -> None:
        """
        Add incoming messages to the model context.
        """
        for msg in messages:
            if isinstance(msg, HandoffMessage):
                for llm_msg in msg.context:
                    await model_context.add_message(llm_msg)
            await model_context.add_message(msg.to_model_message())

    @staticmethod
    async def _update_model_context_with_memory(
        memory: Optional[Sequence[Memory]],
        model_context: ChatCompletionContext,
        agent_name: str,
    ) -> List[MemoryQueryEvent]:
        """Update model context with memory content.

        Args:
            memory: Optional sequence of memory stores to query
            model_context: Context to update with memory content
            agent_name: Name of the agent for event tracking

        Returns:
            List of memory query events generated during update
        """
        events: List[MemoryQueryEvent] = []
        if memory:
            for mem in memory:
                update_context_result = await mem.update_context(model_context)
                if update_context_result and len(update_context_result.memories.results) > 0:
                    memory_query_event_msg = MemoryQueryEvent(
                        content=update_context_result.memories.results,
                        source=agent_name,
                    )
                    events.append(memory_query_event_msg)
        return events

    @classmethod
    async def _call_llm(
        cls,
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        system_messages: List[SystemMessage],
        model_context: ChatCompletionContext,
        workbench: Sequence[Workbench],
        handoff_tools: List[BaseTool[Any, Any]],
        agent_name: str,
        cancellation_token: CancellationToken,
        output_content_type: Optional[type[BaseModel]] = None,
    ) -> AsyncGenerator[Union[CreateResult, ModelClientStreamingChunkEvent], None]:
        """Call the language model with given context and configuration.

        Args:
            model_client: Client for model inference
            model_client_stream: Whether to stream responses
            system_messages: System messages to include
            model_context: Context containing message history
            workbench: Available workbenches
            handoff_tools: Tools for handling handoffs
            agent_name: Name of the agent
            cancellation_token: Token for cancelling operation
            output_content_type: Optional type for structured output

        Returns:
            Generator yielding model results or streaming chunks
        """
        all_messages = await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=system_messages + all_messages)

        tools = [tool for wb in workbench for tool in await wb.list_tools()] + handoff_tools

        if model_client_stream:
            model_result: Optional[CreateResult] = None
            async for chunk in model_client.create_stream(
                llm_messages,
                tools=tools,
                json_output=output_content_type,
                cancellation_token=cancellation_token,
            ):
                if isinstance(chunk, CreateResult):
                    model_result = chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
            if model_result is None:
                raise RuntimeError("No final model result in streaming mode.")
            yield model_result
        else:
            model_result = await model_client.create(
                llm_messages,
                tools=tools,
                cancellation_token=cancellation_token,
                json_output=output_content_type,
            )
            yield model_result

    @classmethod
    async def _process_model_result(
        cls,
        model_result: CreateResult,
        inner_messages: List[BaseAgentEvent | BaseChatMessage],
        cancellation_token: CancellationToken,
        agent_name: str,
        system_messages: List[SystemMessage],
        model_context: ChatCompletionContext,
        workbench: Sequence[Workbench],
        handoff_tools: List[BaseTool[Any, Any]],
        handoffs: Dict[str, HandoffBase],
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        reflect_on_tool_use: bool,
        tool_call_loop_config: ToolCallConfig | None,
        tool_call_summary_format: str,
        tool_call_summary_formatter: Callable[[FunctionCall, FunctionExecutionResult], str] | None,
        output_content_type: type[BaseModel] | None,
        format_string: str | None = None,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """
        Handle final or partial responses from model_result, including tool calls, handoffs,
        and reflection if needed. Supports tool call loops when enabled.
        """

        # Tool call loop implementation
        current_model_result = model_result
        tool_call_loop_enabled = tool_call_loop_config is not None
        max_iterations = tool_call_loop_config.max_iterations if tool_call_loop_config is not None else 1
        # This variable is needed for the final summary/reflection step
        executed_calls_and_results: List[Tuple[FunctionCall, FunctionExecutionResult]] = []

        for loop_iteration in range(max_iterations):
            # If direct text response (string), we're done
            if isinstance(current_model_result.content, str):
                if output_content_type:
                    content = output_content_type.model_validate_json(current_model_result.content)
                    yield Response(
                        chat_message=StructuredMessage[output_content_type](  # type: ignore[valid-type]
                            content=content,
                            source=agent_name,
                            models_usage=current_model_result.usage,
                            format_string=format_string,
                        ),
                        inner_messages=inner_messages,
                    )
                else:
                    yield Response(
                        chat_message=TextMessage(
                            content=current_model_result.content,
                            source=agent_name,
                            models_usage=current_model_result.usage,
                        ),
                        inner_messages=inner_messages,
                    )
                return

            # Otherwise, we have function calls
            assert isinstance(current_model_result.content, list) and all(
                isinstance(item, FunctionCall) for item in current_model_result.content
            )

            # STEP 4A: Yield ToolCallRequestEvent
            tool_call_msg = ToolCallRequestEvent(
                content=current_model_result.content,
                source=agent_name,
                models_usage=current_model_result.usage,
            )
            event_logger.debug(tool_call_msg)
            inner_messages.append(tool_call_msg)
            yield tool_call_msg

            # STEP 4B: Execute tool calls
            executed_calls_and_results = await asyncio.gather(
                *[
                    cls._execute_tool_call(
                        tool_call=call,
                        workbench=workbench,
                        handoff_tools=handoff_tools,
                        agent_name=agent_name,
                        cancellation_token=cancellation_token,
                    )
                    for call in current_model_result.content
                ]
            )
            exec_results = [result for _, result in executed_calls_and_results]

            # Yield ToolCallExecutionEvent
            tool_call_result_msg = ToolCallExecutionEvent(
                content=exec_results,
                source=agent_name,
            )
            event_logger.debug(tool_call_result_msg)
            await model_context.add_message(FunctionExecutionResultMessage(content=exec_results))
            inner_messages.append(tool_call_result_msg)
            yield tool_call_result_msg

            # STEP 4C: Check for handoff
            handoff_output = cls._check_and_handle_handoff(
                model_result=current_model_result,
                executed_calls_and_results=executed_calls_and_results,
                inner_messages=inner_messages,
                handoffs=handoffs,
                agent_name=agent_name,
            )
            if handoff_output:
                yield handoff_output
                return

            # STEP 4D: Check if we should continue the loop.
            # If the loop is disabled, or we are on the last iteration, break to the summary/reflection step.
            if not tool_call_loop_enabled or loop_iteration == max_iterations - 1:
                break

            # Continue the loop: make another model call
            # Get tools for the next iteration
            all_messages = system_messages + await model_context.get_messages()
            llm_messages = cls._get_compatible_context(model_client=model_client, messages=all_messages)

            # Make another model call
            if model_client_stream:
                next_model_result: Optional[CreateResult] = None
                async for chunk in model_client.create_stream(
                    llm_messages,
                    json_output=output_content_type,
                    cancellation_token=cancellation_token,
                ):
                    if isinstance(chunk, CreateResult):
                        next_model_result = chunk
                    elif isinstance(chunk, str):
                        yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                    else:
                        raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
                if next_model_result is None:
                    raise RuntimeError("No final model result in streaming mode.")
                current_model_result = next_model_result
            else:
                current_model_result = await model_client.create(
                    llm_messages, json_output=output_content_type, cancellation_token=cancellation_token
                )

            # Add the assistant message to the model context (including thought if present)
            await model_context.add_message(
                AssistantMessage(
                    content=current_model_result.content,
                    source=agent_name,
                    thought=getattr(current_model_result, "thought", None),
                )
            )

            # Yield thought event if present
            if current_model_result.thought:
                thought_event = ThoughtEvent(content=current_model_result.thought, source=agent_name)
                yield thought_event
                inner_messages.append(thought_event)

        # After the loop, reflect or summarize tool results
        if reflect_on_tool_use:
            async for reflection_response in cls._reflect_on_tool_use_flow(
                system_messages=system_messages,
                model_client=model_client,
                model_client_stream=model_client_stream,
                model_context=model_context,
                workbench=workbench,
                handoff_tools=handoff_tools,
                agent_name=agent_name,
                inner_messages=inner_messages,
                output_content_type=output_content_type,
                cancellation_token=cancellation_token,
            ):
                yield reflection_response
        else:
            yield cls._summarize_tool_use(
                executed_calls_and_results=executed_calls_and_results,
                inner_messages=inner_messages,
                handoffs=handoffs,
                tool_call_summary_format=tool_call_summary_format,
                tool_call_summary_formatter=tool_call_summary_formatter,
                agent_name=agent_name,
            )
        return

    @staticmethod
    def _check_and_handle_handoff(
        model_result: CreateResult,
        executed_calls_and_results: List[Tuple[FunctionCall, FunctionExecutionResult]],
        inner_messages: List[BaseAgentEvent | BaseChatMessage],
        handoffs: Dict[str, HandoffBase],
        agent_name: str,
    ) -> Optional[Response]:
        """Check for and handle any handoff requests in the model result.

        Args:
            model_result: Result from model inference
            executed_calls_and_results: List of executed tool calls and their results
            inner_messages: List of messages generated during processing
            handoffs: Dictionary of available handoff configurations
            agent_name: Name of the agent

        Returns:
            Optional response containing handoff message if handoff detected
        """
        handoff_reqs = [
            call for call in model_result.content if isinstance(call, FunctionCall) and call.name in handoffs
        ]
        if len(handoff_reqs) > 0:
            # We have at least one handoff function call
            selected_handoff = handoffs[handoff_reqs[0].name]

            if len(handoff_reqs) > 1:
                warnings.warn(
                    (
                        f"Multiple handoffs detected. Only the first is executed: "
                        f"{[handoffs[c.name].name for c in handoff_reqs]}. "
                        "Disable parallel tool calls in the model client to avoid this warning."
                    ),
                    stacklevel=2,
                )

            # Collect normal tool calls (not handoff) into the handoff context
            tool_calls: List[FunctionCall] = []
            tool_call_results: List[FunctionExecutionResult] = []
            # Collect the results returned by handoff_tool. By default, the message attribute will returned.
            selected_handoff_message = selected_handoff.message
            for exec_call, exec_result in executed_calls_and_results:
                if exec_call.name not in handoffs:
                    tool_calls.append(exec_call)
                    tool_call_results.append(exec_result)
                elif exec_call.name == selected_handoff.name:
                    selected_handoff_message = exec_result.content

            handoff_context: List[LLMMessage] = []
            if len(tool_calls) > 0:
                # Include the thought in the AssistantMessage if model_result has it
                handoff_context.append(
                    AssistantMessage(
                        content=tool_calls,
                        source=agent_name,
                        thought=getattr(model_result, "thought", None),
                    )
                )
                handoff_context.append(FunctionExecutionResultMessage(content=tool_call_results))
            elif model_result.thought:
                # If no tool calls, but a thought exists, include it in the context
                handoff_context.append(
                    AssistantMessage(
                        content=model_result.thought,
                        source=agent_name,
                    )
                )

            # Return response for the first handoff
            return Response(
                chat_message=HandoffMessage(
                    content=selected_handoff_message,
                    target=selected_handoff.target,
                    source=agent_name,
                    context=handoff_context,
                ),
                inner_messages=inner_messages,
            )
        return None

    @classmethod
    async def _reflect_on_tool_use_flow(
        cls,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        model_context: ChatCompletionContext,
        workbench: Sequence[Workbench],
        handoff_tools: List[BaseTool[Any, Any]],
        agent_name: str,
        inner_messages: List[BaseAgentEvent | BaseChatMessage],
        output_content_type: type[BaseModel] | None,
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[Response | ModelClientStreamingChunkEvent | ThoughtEvent, None]:
        """
        If reflect_on_tool_use=True, we do another inference based on tool results
        and yield the final text response (or streaming chunks).
        """
        all_messages = system_messages + await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=all_messages)

        reflection_result: Optional[CreateResult] = None

        if model_client_stream:
            async for chunk in model_client.create_stream(
                llm_messages,
                json_output=output_content_type,
                cancellation_token=cancellation_token,
            ):
                if isinstance(chunk, CreateResult):
                    reflection_result = chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
        else:
            reflection_result = await model_client.create(
                llm_messages, json_output=output_content_type, cancellation_token=cancellation_token
            )

        if not reflection_result or not isinstance(reflection_result.content, str):
            raise RuntimeError("Reflect on tool use produced no valid text response.")

        # --- NEW: If the reflection produced a thought, yield it ---
        if reflection_result.thought:
            thought_event = ThoughtEvent(content=reflection_result.thought, source=agent_name)
            yield thought_event
            inner_messages.append(thought_event)

        # Add to context (including thought if present)
        await model_context.add_message(
            AssistantMessage(
                content=reflection_result.content,
                source=agent_name,
                thought=getattr(reflection_result, "thought", None),
            )
        )

        if output_content_type:
            content = output_content_type.model_validate_json(reflection_result.content)
            yield Response(
                chat_message=StructuredMessage[output_content_type](  # type: ignore[valid-type]
                    content=content,
                    source=agent_name,
                    models_usage=reflection_result.usage,
                ),
                inner_messages=inner_messages,
            )
        else:
            yield Response(
                chat_message=TextMessage(
                    content=reflection_result.content,
                    source=agent_name,
                    models_usage=reflection_result.usage,
                ),
                inner_messages=inner_messages,
            )

    @staticmethod
    def _summarize_tool_use(
        executed_calls_and_results: List[Tuple[FunctionCall, FunctionExecutionResult]],
        inner_messages: List[BaseAgentEvent | BaseChatMessage],
        handoffs: Dict[str, HandoffBase],
        tool_call_summary_format: str,
        tool_call_summary_formatter: Callable[[FunctionCall, FunctionExecutionResult], str] | None,
        agent_name: str,
    ) -> Response:
        """
        If reflect_on_tool_use=False, create a summary message of all tool calls.
        """
        # Filter out calls which were actually handoffs
        normal_tool_calls = [(call, result) for call, result in executed_calls_and_results if call.name not in handoffs]

        def default_tool_call_summary_formatter(call: FunctionCall, result: FunctionExecutionResult) -> str:
            return tool_call_summary_format.format(
                tool_name=call.name,
                arguments=call.arguments,
                result=result.content,
                is_error=result.is_error,
            )

        summary_formatter = tool_call_summary_formatter or default_tool_call_summary_formatter

        tool_call_summaries = [summary_formatter(call, result) for call, result in normal_tool_calls]

        tool_call_summary = "\n".join(tool_call_summaries)
        return Response(
            chat_message=ToolCallSummaryMessage(
                content=tool_call_summary,
                source=agent_name,
                tool_calls=[call for call, _ in normal_tool_calls],
                results=[result for _, result in normal_tool_calls],
            ),
            inner_messages=inner_messages,
        )

    @staticmethod
    async def _execute_tool_call(
        tool_call: FunctionCall,
        workbench: Sequence[Workbench],
        handoff_tools: List[BaseTool[Any, Any]],
        agent_name: str,
        cancellation_token: CancellationToken,
    ) -> Tuple[FunctionCall, FunctionExecutionResult]:
        """Execute a single tool call and return the result."""
        # Load the arguments from the tool call.
        try:
            arguments = json.loads(tool_call.arguments)
        except json.JSONDecodeError as e:
            return (
                tool_call,
                FunctionExecutionResult(
                    content=f"Error: {e}",
                    call_id=tool_call.id,
                    is_error=True,
                    name=tool_call.name,
                ),
            )

        # Check if the tool call is a handoff.
        # TODO: consider creating a combined workbench to handle both handoff and normal tools.
        for handoff_tool in handoff_tools:
            if tool_call.name == handoff_tool.name:
                # Run handoff tool call.
                result = await handoff_tool.run_json(arguments, cancellation_token, call_id=tool_call.id)
                result_as_str = handoff_tool.return_value_as_string(result)
                return (
                    tool_call,
                    FunctionExecutionResult(
                        content=result_as_str,
                        call_id=tool_call.id,
                        is_error=False,
                        name=tool_call.name,
                    ),
                )

        # Handle normal tool call using workbench.
        for wb in workbench:
            tools = await wb.list_tools()
            if any(t["name"] == tool_call.name for t in tools):
                result = await wb.call_tool(
                    name=tool_call.name,
                    arguments=arguments,
                    cancellation_token=cancellation_token,
                    call_id=tool_call.id,
                )
                return (
                    tool_call,
                    FunctionExecutionResult(
                        content=result.to_text(),
                        call_id=tool_call.id,
                        is_error=result.is_error,
                        name=tool_call.name,
                    ),
                )

        return (
            tool_call,
            FunctionExecutionResult(
                content=f"Error: tool '{tool_call.name}' not found in any workbench",
                call_id=tool_call.id,
                is_error=True,
                name=tool_call.name,
            ),
        )

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

    @staticmethod
    def _get_compatible_context(model_client: ChatCompletionClient, messages: List[LLMMessage]) -> Sequence[LLMMessage]:
        """Ensure that the messages are compatible with the underlying client, by removing images if needed."""
        if model_client.model_info["vision"]:
            return messages
        else:
            return remove_images(messages)

    def _to_config(self) -> AssistantAgentConfig:
        """Convert the assistant agent to a declarative config."""

        return AssistantAgentConfig(
            name=self.name,
            model_client=self._model_client.dump_component(),
            tools=None,  # versionchanged:: v0.5.5  Now tools are not serialized, Cause they are part of the workbench.
            workbench=[wb.dump_component() for wb in self._workbench] if self._workbench else None,
            handoffs=list(self._handoffs.values()) if self._handoffs else None,
            model_context=self._model_context.dump_component(),
            memory=[memory.dump_component() for memory in self._memory] if self._memory else None,
            description=self.description,
            system_message=self._system_messages[0].content
            if self._system_messages and isinstance(self._system_messages[0].content, str)
            else None,
            model_client_stream=self._model_client_stream,
            reflect_on_tool_use=self._reflect_on_tool_use,
            tool_call_loop_config=self._tool_call_loop_config,
            tool_call_summary_format=self._tool_call_summary_format,
            structured_message_factory=self._structured_message_factory.dump_component()
            if self._structured_message_factory
            else None,
            metadata=self._metadata,
        )

    @classmethod
    def _from_config(cls, config: AssistantAgentConfig) -> Self:
        """Create an assistant agent from a declarative config."""
        if config.structured_message_factory:
            structured_message_factory = StructuredMessageFactory.load_component(config.structured_message_factory)
            format_string = structured_message_factory.format_string
            output_content_type = structured_message_factory.ContentModel

        else:
            format_string = None
            output_content_type = None

        return cls(
            name=config.name,
            model_client=ChatCompletionClient.load_component(config.model_client),
            workbench=[Workbench.load_component(wb) for wb in config.workbench] if config.workbench else None,
            handoffs=config.handoffs,
            model_context=ChatCompletionContext.load_component(config.model_context) if config.model_context else None,
            tools=[BaseTool.load_component(tool) for tool in config.tools] if config.tools else None,
            memory=[Memory.load_component(memory) for memory in config.memory] if config.memory else None,
            description=config.description,
            system_message=config.system_message,
            model_client_stream=config.model_client_stream,
            reflect_on_tool_use=config.reflect_on_tool_use,
            tool_call_loop_config=config.tool_call_loop_config,
            tool_call_summary_format=config.tool_call_summary_format,
            output_content_type=output_content_type,
            output_content_type_format=format_string,
            metadata=config.metadata,
        )
