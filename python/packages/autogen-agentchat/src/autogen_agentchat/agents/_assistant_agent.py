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
from pydantic import BaseModel, Field
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
    max_tool_iterations: int = Field(default=1, ge=1)
    metadata: Dict[str, str] | None = None
    structured_message_factory: ComponentModel | None = None


class AssistantAgent(BaseChatAgent, Component[AssistantAgentConfig]):
    """An agent that provides assistance with tool use.
    The :meth:`on_messages` returns a :class:`~autogen_agentchat.base.Response`
    in which :attr:`~autogen_agentchat.base.Response.chat_message` is the final
    response message.

    The :meth:`on_messages_stream` creates an async generator that produces
    the inner messages as they are created, and the :class:`~autogen_agentchat.base.Response`
    object as the last item before closing the generator.

    The :meth:`BaseChatAgent.run` method returns a :class:`~autogen_agentchat.base.TaskResult`
    containing the messages produced by the agent. In the list of messages,
    :attr:`~autogen_agentchat.base.TaskResult.messages`,
    the last message is the final response message.

    The :meth:`BaseChatAgent.run_stream` method creates an async generator that produces
    the inner messages as they are created, and the :class:`~autogen_agentchat.base.TaskResult`
    object as the last item before closing the generator.

    .. attention::

        The caller must only pass the new messages to the agent on each call
        to the :meth:`on_messages`, :meth:`on_messages_stream`, :meth:`BaseChatAgent.run`,
        or :meth:`BaseChatAgent.run_stream` methods.
        The agent maintains its state between calls to these methods.
        Do not pass the entire conversation history to the agent on each call.

    .. warning::
        The assistant agent is not thread-safe or coroutine-safe.
        It should not be shared between multiple tasks or coroutines, and it should
        not call its methods concurrently.

    The following diagram shows how the assistant agent works:

    .. image:: ../../images/assistant-agent.svg

    **Structured output:**

    If the `output_content_type` is set, the agent will respond with a :class:`~autogen_agentchat.messages.StructuredMessage`
    instead of a :class:`~autogen_agentchat.messages.TextMessage` in the final response by default.

    .. note::

        Currently, setting `output_content_type` prevents the agent from being
        able to call `load_component` and `dum_component` methods for serializable
        configuration. This will be fixed soon in the future.

    **Tool call behavior:**

    * If the model returns no tool call, then the response is immediately returned as a :class:`~autogen_agentchat.messages.TextMessage` or a :class:`~autogen_agentchat.messages.StructuredMessage` (when using structured output) in :attr:`~autogen_agentchat.base.Response.chat_message`.
    * When the model returns tool calls, they will be executed right away:
        - When `reflect_on_tool_use` is False, the tool call results are returned as a :class:`~autogen_agentchat.messages.ToolCallSummaryMessage` in :attr:`~autogen_agentchat.base.Response.chat_message`. You can customise the summary with either a static format string (`tool_call_summary_format`) **or** a callable (`tool_call_summary_formatter`); the callable is evaluated once per tool call.
        - When `reflect_on_tool_use` is True, the another model inference is made using the tool calls and results, and final response is returned as a :class:`~autogen_agentchat.messages.TextMessage` or a :class:`~autogen_agentchat.messages.StructuredMessage` (when using structured output) in :attr:`~autogen_agentchat.base.Response.chat_message`.
        - `reflect_on_tool_use` is set to `True` by default when `output_content_type` is set.
        - `reflect_on_tool_use` is set to `False` by default when `output_content_type` is not set.
    * If the model returns multiple tool calls, they will be executed concurrently. To disable parallel tool calls you need to configure the model client. For example, set `parallel_tool_calls=False` for :class:`~autogen_ext.models.openai.OpenAIChatCompletionClient` and :class:`~autogen_ext.models.openai.AzureOpenAIChatCompletionClient`.

    .. tip::

        By default, the tool call results are returned as the response when tool
        calls are made, so pay close attention to how the tools’ return values
        are formatted—especially if another agent expects a specific schema.

        * Use **`tool_call_summary_format`** for a simple static template.
        * Use **`tool_call_summary_formatter`** for full programmatic control
          (e.g., “hide large success payloads, show full details on error”).

        *Note*: `tool_call_summary_formatter` is **not serializable** and will
        be ignored when an agent is loaded from, or exported to, YAML/JSON
        configuration files.


    **Hand off behavior:**

    * If a handoff is triggered, a :class:`~autogen_agentchat.messages.HandoffMessage` will be returned in :attr:`~autogen_agentchat.base.Response.chat_message`.
    * If there are tool calls, they will also be executed right away before returning the handoff.
    * The tool calls and results are passed to the target agent through :attr:`~autogen_agentchat.messages.HandoffMessage.context`.


    .. note::
        If multiple handoffs are detected, only the first handoff is executed.
        To avoid this, disable parallel tool calls in the model client configuration.


    **Limit context size sent to the model:**

    You can limit the number of messages sent to the model by setting
    the `model_context` parameter to a :class:`~autogen_core.model_context.BufferedChatCompletionContext`.
    This will limit the number of recent messages sent to the model and can be useful
    when the model has a limit on the number of tokens it can process.
    Another option is to use a :class:`~autogen_core.model_context.TokenLimitedChatCompletionContext`
    which will limit the number of tokens sent to the model.
    You can also create your own model context by subclassing
    :class:`~autogen_core.model_context.ChatCompletionContext`.

    **Streaming mode:**

    The assistant agent can be used in streaming mode by setting `model_client_stream=True`.
    In this mode, the :meth:`on_messages_stream` and :meth:`BaseChatAgent.run_stream` methods will also yield
    :class:`~autogen_agentchat.messages.ModelClientStreamingChunkEvent`
    messages as the model client produces chunks of response.
    The chunk messages will not be included in the final response's inner messages.

    Args:
        name (str): The name of the agent.
        model_client (ChatCompletionClient): The model client to use for inference.
        tools (List[BaseTool[Any, Any]  | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None, optional): The tools to register with the agent.
        workbench (Workbench | Sequence[Workbench] | None, optional): The workbench or list of workbenches to use for the agent.
            Tools cannot be used when workbench is set and vice versa.
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
            to generate a response. If `False`, the tool call result will be returned as the response. By default, if `output_content_type` is set, this will be `True`;
            if `output_content_type` is not set, this will be `False`.
        output_content_type (type[BaseModel] | None, optional): The output content type for :class:`~autogen_agentchat.messages.StructuredMessage` response as a Pydantic model.
            This will be used with the model client to generate structured output.
            If this is set, the agent will respond with a :class:`~autogen_agentchat.messages.StructuredMessage` instead of a :class:`~autogen_agentchat.messages.TextMessage`
            in the final response, unless `reflect_on_tool_use` is `False` and a tool call is made.
        output_content_type_format (str | None, optional): (Experimental) The format string used for the content of a :class:`~autogen_agentchat.messages.StructuredMessage` response.
        max_tool_iterations (int, optional): The maximum number of tool iterations to perform until the model stops making tool calls. Defaults to `1`, which means the agent will
            only execute the tool calls made by the model once, and return the result as a :class:`~autogen_agentchat.messages.ToolCallSummaryMessage`,
            or a :class:`~autogen_agentchat.messages.TextMessage` or a :class:`~autogen_agentchat.messages.StructuredMessage` (when using structured output)
            in :attr:`~autogen_agentchat.base.Response.chat_message` as the final response.
            As soon as the model stops making tool calls, the agent will stop executing tool calls and return the result as the final response.
            The value must be greater than or equal to 1.
        tool_call_summary_format (str, optional): Static format string applied to each tool call result when composing the :class:`~autogen_agentchat.messages.ToolCallSummaryMessage`.
            Defaults to ``"{result}"``. Ignored if `tool_call_summary_formatter` is provided. When `reflect_on_tool_use` is ``False``, the summaries for all tool
            calls are concatenated with a newline ('\\n') and returned as the response.  Placeholders available in the template:
            `{tool_name}`, `{arguments}`, `{result}`, `{is_error}`.
        tool_call_summary_formatter (Callable[[FunctionCall, FunctionExecutionResult], str] | None, optional):
            Callable that receives the ``FunctionCall`` and its ``FunctionExecutionResult`` and returns the summary string.
            Overrides `tool_call_summary_format` when supplied and allows conditional logic — for example, emitting static string like
            ``"Tool FooBar executed successfully."`` on success and a full payload (including all passed arguments etc.) only on failure.

            **Limitation**: The callable is *not serializable*; values provided via YAML/JSON configs are ignored.

    .. note::

        `tool_call_summary_formatter` is intended for in-code use only. It cannot currently be saved or restored via
        configuration files.

        memory (Sequence[Memory] | None, optional): The memory store to use for the agent. Defaults to `None`.
        metadata (Dict[str, str] | None, optional): Optional metadata for tracking.

    Raises:
        ValueError: If tool names are not unique.
        ValueError: If handoff names are not unique.
        ValueError: If handoff names are not unique from tool names.
        ValueError: If maximum number of tool iterations is less than 1.

    Examples:

        **Example 1: basic agent**

        The following example demonstrates how to create an assistant agent with
        a model client and generate a response to a simple task.

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )
                agent = AssistantAgent(name="assistant", model_client=model_client)

                result = await agent.run(task="Name two cities in North America.")
                print(result)


            asyncio.run(main())

        **Example 2: model client token streaming**

        This example demonstrates how to create an assistant agent with
        a model client and generate a token stream by setting `model_client_stream=True`.

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )
                agent = AssistantAgent(
                    name="assistant",
                    model_client=model_client,
                    model_client_stream=True,
                )

                stream = agent.run_stream(task="Name two cities in North America.")
                async for message in stream:
                    print(message)


            asyncio.run(main())

        .. code-block:: text

            source='user' models_usage=None metadata={} content='Name two cities in North America.' type='TextMessage'
            source='assistant' models_usage=None metadata={} content='Two' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' cities' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' in' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' North' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' America' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' are' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' New' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' York' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' City' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' and' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' Toronto' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content='.' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content=' TERMIN' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None metadata={} content='ATE' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=RequestUsage(prompt_tokens=0, completion_tokens=0) metadata={} content='Two cities in North America are New York City and Toronto. TERMINATE' type='TextMessage'
            messages=[TextMessage(source='user', models_usage=None, metadata={}, content='Name two cities in North America.', type='TextMessage'), TextMessage(source='assistant', models_usage=RequestUsage(prompt_tokens=0, completion_tokens=0), metadata={}, content='Two cities in North America are New York City and Toronto. TERMINATE', type='TextMessage')] stop_reason=None


        **Example 3: agent with tools**

        The following example demonstrates how to create an assistant agent with
        a model client and a tool, generate a stream of messages for a task, and
        print the messages to the console using :class:`~autogen_agentchat.ui.Console`.

        The tool is a simple function that returns the current time.
        Under the hood, the function is wrapped in a :class:`~autogen_core.tools.FunctionTool`
        and used with the agent's model client. The doc string of the function
        is used as the tool description, the function name is used as the tool name,
        and the function signature including the type hints is used as the tool arguments.

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console


            async def get_current_time() -> str:
                return "The current time is 12:00 PM."


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )
                agent = AssistantAgent(name="assistant", model_client=model_client, tools=[get_current_time])
                await Console(agent.run_stream(task="What is the current time?"))


            asyncio.run(main())

        **Example 4: agent with Model-Context Protocol (MCP) workbench**

        The following example demonstrates how to create an assistant agent with
        a model client and an :class:`~autogen_ext.tools.mcp.McpWorkbench` for
        interacting with a Model-Context Protocol (MCP) server.

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench


            async def main() -> None:
                params = StdioServerParams(
                    command="uvx",
                    args=["mcp-server-fetch"],
                    read_timeout_seconds=60,
                )

                # You can also use `start()` and `stop()` to manage the session.
                async with McpWorkbench(server_params=params) as workbench:
                    model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
                    assistant = AssistantAgent(
                        name="Assistant",
                        model_client=model_client,
                        workbench=workbench,
                        reflect_on_tool_use=True,
                    )
                    await Console(
                        assistant.run_stream(task="Go to https://github.com/microsoft/autogen and tell me what you see.")
                    )


            asyncio.run(main())

        **Example 5: agent with structured output and tool**

        The following example demonstrates how to create an assistant agent with
        a model client configured to use structured output and a tool.
        Note that you need to use :class:`~autogen_core.tools.FunctionTool` to create the tool
        and the `strict=True` is required for structured output mode.
        Because the model is configured to use structured output, the output
        reflection response will be a JSON formatted string.

        .. code-block:: python

            import asyncio
            from typing import Literal

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core.tools import FunctionTool
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from pydantic import BaseModel


            # Define the structured output format.
            class AgentResponse(BaseModel):
                thoughts: str
                response: Literal["happy", "sad", "neutral"]


            # Define the function to be called as a tool.
            def sentiment_analysis(text: str) -> str:
                \"\"\"Given a text, return the sentiment.\"\"\"
                return "happy" if "happy" in text else "sad" if "sad" in text else "neutral"


            # Create a FunctionTool instance with `strict=True`,
            # which is required for structured output mode.
            tool = FunctionTool(sentiment_analysis, description="Sentiment Analysis", strict=True)

            # Create an OpenAIChatCompletionClient instance that supports structured output.
            model_client = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
            )

            # Create an AssistantAgent instance that uses the tool and model client.
            agent = AssistantAgent(
                name="assistant",
                model_client=model_client,
                tools=[tool],
                system_message="Use the tool to analyze sentiment.",
                output_content_type=AgentResponse,
            )


            async def main() -> None:
                stream = agent.run_stream(task="I am happy today!")
                await Console(stream)


            asyncio.run(main())

        .. code-block:: text

            ---------- assistant ----------
            [FunctionCall(id='call_tIZjAVyKEDuijbBwLY6RHV2p', arguments='{"text":"I am happy today!"}', name='sentiment_analysis')]
            ---------- assistant ----------
            [FunctionExecutionResult(content='happy', call_id='call_tIZjAVyKEDuijbBwLY6RHV2p', is_error=False)]
            ---------- assistant ----------
            {"thoughts":"The user expresses a clear positive emotion by stating they are happy today, suggesting an upbeat mood.","response":"happy"}

        **Example 6: agent with bounded model context**

        The following example shows how to use a
        :class:`~autogen_core.model_context.BufferedChatCompletionContext`
        that only keeps the last 2 messages (1 user + 1 assistant).
        Bounded model context is useful when the model has a limit on the
        number of tokens it can process.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.model_context import BufferedChatCompletionContext
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                # Create a model client.
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o-mini",
                    # api_key = "your_openai_api_key"
                )

                # Create a model context that only keeps the last 2 messages (1 user + 1 assistant).
                model_context = BufferedChatCompletionContext(buffer_size=2)

                # Create an AssistantAgent instance with the model client and context.
                agent = AssistantAgent(
                    name="assistant",
                    model_client=model_client,
                    model_context=model_context,
                    system_message="You are a helpful assistant.",
                )

                result = await agent.run(task="Name two cities in North America.")
                print(result.messages[-1].content)  # type: ignore

                result = await agent.run(task="My favorite color is blue.")
                print(result.messages[-1].content)  # type: ignore

                result = await agent.run(task="Did I ask you any question?")
                print(result.messages[-1].content)  # type: ignore


            asyncio.run(main())

        .. code-block:: text

            Two cities in North America are New York City and Toronto.
            That's great! Blue is often associated with calmness and serenity. Do you have a specific shade of blue that you like, or any particular reason why it's your favorite?
            No, you didn't ask a question. I apologize for any misunderstanding. If you have something specific you'd like to discuss or ask, feel free to let me know!

        **Example 7: agent with memory**

        The following example shows how to use a list-based memory with the assistant agent.
        The memory is preloaded with some initial content.
        Under the hood, the memory is used to update the model context
        before making an inference, using the :meth:`~autogen_core.memory.Memory.update_context` method.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.memory import ListMemory, MemoryContent
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                # Create a model client.
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o-mini",
                    # api_key = "your_openai_api_key"
                )

                # Create a list-based memory with some initial content.
                memory = ListMemory()
                await memory.add(MemoryContent(content="User likes pizza.", mime_type="text/plain"))
                await memory.add(MemoryContent(content="User dislikes cheese.", mime_type="text/plain"))

                # Create an AssistantAgent instance with the model client and memory.
                agent = AssistantAgent(
                    name="assistant",
                    model_client=model_client,
                    memory=[memory],
                    system_message="You are a helpful assistant.",
                )

                result = await agent.run(task="What is a good dinner idea?")
                print(result.messages[-1].content)  # type: ignore


            asyncio.run(main())

        .. code-block:: text

            How about making a delicious pizza without cheese? You can create a flavorful veggie pizza with a variety of toppings. Here's a quick idea:

            **Veggie Tomato Sauce Pizza**
            - Start with a pizza crust (store-bought or homemade).
            - Spread a layer of marinara or tomato sauce evenly over the crust.
            - Top with your favorite vegetables like bell peppers, mushrooms, onions, olives, and spinach.
            - Add some protein if you’d like, such as grilled chicken or pepperoni (ensure it's cheese-free).
            - Sprinkle with herbs like oregano and basil, and maybe a drizzle of olive oil.
            - Bake according to the crust instructions until the edges are golden and the veggies are cooked.

            Serve it with a side salad or some garlic bread to complete the meal! Enjoy your dinner!

        **Example 8: agent with `o1-mini`**

        The following example shows how to use `o1-mini` model with the assistant agent.

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(
                    model="o1-mini",
                    # api_key = "your_openai_api_key"
                )
                # The system message is not supported by the o1 series model.
                agent = AssistantAgent(name="assistant", model_client=model_client, system_message=None)

                result = await agent.run(task="What is the capital of France?")
                print(result.messages[-1].content)  # type: ignore


            asyncio.run(main())

        .. note::

            The `o1-preview` and `o1-mini` models do not support system message and function calling.
            So the `system_message` should be set to `None` and the `tools` and `handoffs` should not be set.
            See `o1 beta limitations <https://platform.openai.com/docs/guides/reasoning#beta-limitations>`_ for more details.


        **Example 9: agent using reasoning model with custom model context.**

        The following example shows how to use a reasoning model (DeepSeek R1) with the assistant agent.
        The model context is used to filter out the thought field from the assistant message.

        .. code-block:: python

            import asyncio
            from typing import List

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.model_context import UnboundedChatCompletionContext
            from autogen_core.models import AssistantMessage, LLMMessage, ModelFamily
            from autogen_ext.models.ollama import OllamaChatCompletionClient


            class ReasoningModelContext(UnboundedChatCompletionContext):
                \"\"\"A model context for reasoning models.\"\"\"

                async def get_messages(self) -> List[LLMMessage]:
                    messages = await super().get_messages()
                    # Filter out thought field from AssistantMessage.
                    messages_out: List[LLMMessage] = []
                    for message in messages:
                        if isinstance(message, AssistantMessage):
                            message.thought = None
                        messages_out.append(message)
                    return messages_out


            # Create an instance of the model client for DeepSeek R1 hosted locally on Ollama.
            model_client = OllamaChatCompletionClient(
                model="deepseek-r1:8b",
                model_info={
                    "vision": False,
                    "function_calling": False,
                    "json_output": False,
                    "family": ModelFamily.R1,
                    "structured_output": True,
                },
            )

            agent = AssistantAgent(
                "reasoning_agent",
                model_client=model_client,
                model_context=ReasoningModelContext(),  # Use the custom model context.
            )


            async def run_reasoning_agent() -> None:
                result = await agent.run(task="What is the capital of France?")
                print(result)


            asyncio.run(run_reasoning_agent())

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
        tools: List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        workbench: Workbench | Sequence[Workbench] | None = None,
        handoffs: List[HandoffBase | str] | None = None,
        model_context: ChatCompletionContext | None = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: (
            str | None
        ) = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
        model_client_stream: bool = False,
        reflect_on_tool_use: bool | None = None,
        max_tool_iterations: int = 1,
        tool_call_summary_format: str = "{result}",
        tool_call_summary_formatter: Callable[[FunctionCall, FunctionExecutionResult], str] | None = None,
        output_content_type: type[BaseModel] | None = None,
        output_content_type_format: str | None = None,
        memory: Sequence[Memory] | None = None,
        metadata: Dict[str, str] | None = None,
    ):
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
        # Create sets for faster lookup
        tool_names_set = set(tool_names)
        handoff_tool_names_set = set(handoff_tool_names)

        # Check if there's any overlap between handoff tool names and tool names
        overlap = tool_names_set.intersection(handoff_tool_names_set)

        # Also check if any handoff target name matches a tool name
        # This handles the case where a handoff is specified directly with a string that matches a tool name
        for handoff in handoffs or []:
            if isinstance(handoff, str) and handoff in tool_names_set:
                raise ValueError("Handoff names must be unique from tool names")
            elif isinstance(handoff, HandoffBase) and handoff.target in tool_names_set:
                raise ValueError("Handoff names must be unique from tool names")

        if overlap:
            raise ValueError("Handoff names must be unique from tool names")

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

        # Tool call loop
        self._max_tool_iterations = max_tool_iterations
        if self._max_tool_iterations < 1:
            raise ValueError(
                f"Maximum number of tool iterations must be greater than or equal to 1, got {max_tool_iterations}"
            )

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
        max_tool_iterations = self._max_tool_iterations
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
            max_tool_iterations=max_tool_iterations,
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
        output_content_type: type[BaseModel] | None,
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
        tool_call_summary_format: str,
        tool_call_summary_formatter: Callable[[FunctionCall, FunctionExecutionResult], str] | None,
        max_tool_iterations: int,
        output_content_type: type[BaseModel] | None,
        format_string: str | None = None,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """
        Handle final or partial responses from model_result, including tool calls, handoffs,
        and reflection if needed. Supports tool call loops when enabled.
        """

        # Tool call loop implementation
        current_model_result = model_result
        # This variable is needed for the final summary/reflection step
        executed_calls_and_results: List[Tuple[FunctionCall, FunctionExecutionResult]] = []

        for loop_iteration in range(max_tool_iterations):
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
            # If we are on the last iteration, break to the summary/reflection step.
            if loop_iteration == max_tool_iterations - 1:
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
            max_tool_iterations=self._max_tool_iterations,
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
            max_tool_iterations=config.max_tool_iterations,
            tool_call_summary_format=config.tool_call_summary_format,
            output_content_type=output_content_type,
            output_content_type_format=format_string,
            metadata=config.metadata,
        )
