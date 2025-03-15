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
    ThoughtEvent,
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
    You can also create your own model context by subclassing
    :class:`~autogen_core.model_context.ChatCompletionContext`.

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

        **Example 1: basic agent**

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

        **Example 2: model client token streaming**

        This example demonstrates how to create an assistant agent with
        a model client and generate a token stream by setting `model_client_stream=True`.

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken


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

                stream = agent.on_messages_stream(
                    [TextMessage(content="Name two cities in North America.", source="user")], CancellationToken()
                )
                async for message in stream:
                    print(message)


            asyncio.run(main())

        .. code-block:: text

            source='assistant' models_usage=None content='Two' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' cities' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' in' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' North' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' America' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' are' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' New' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' York' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' City' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' in' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' the' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' United' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' States' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' and' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' Toronto' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' in' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' Canada' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content='.' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content=' TERMIN' type='ModelClientStreamingChunkEvent'
            source='assistant' models_usage=None content='ATE' type='ModelClientStreamingChunkEvent'
            Response(chat_message=TextMessage(source='assistant', models_usage=RequestUsage(prompt_tokens=0, completion_tokens=0), content='Two cities in North America are New York City in the United States and Toronto in Canada. TERMINATE', type='TextMessage'), inner_messages=[])


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

        **Example 4: agent with structured output and tool**

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
            from autogen_agentchat.messages import TextMessage
            from autogen_agentchat.ui import Console
            from autogen_core import CancellationToken
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

            # Create an OpenAIChatCompletionClient instance that uses the structured output format.
            model_client = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                response_format=AgentResponse,  # type: ignore
            )

            # Create an AssistantAgent instance that uses the tool and model client.
            agent = AssistantAgent(
                name="assistant",
                model_client=model_client,
                tools=[tool],
                system_message="Use the tool to analyze sentiment.",
                reflect_on_tool_use=True,  # Use reflection to have the agent generate a formatted response.
            )


            async def main() -> None:
                stream = agent.on_messages_stream([TextMessage(content="I am happy today!", source="user")], CancellationToken())
                await Console(stream)


            asyncio.run(main())

        .. code-block:: text

            ---------- assistant ----------
            [FunctionCall(id='call_tIZjAVyKEDuijbBwLY6RHV2p', arguments='{"text":"I am happy today!"}', name='sentiment_analysis')]
            ---------- assistant ----------
            [FunctionExecutionResult(content='happy', call_id='call_tIZjAVyKEDuijbBwLY6RHV2p', is_error=False)]
            ---------- assistant ----------
            {"thoughts":"The user expresses a clear positive emotion by stating they are happy today, suggesting an upbeat mood.","response":"happy"}

        **Example 5: agent with bounded model context**

        The following example shows how to use a
        :class:`~autogen_core.model_context.BufferedChatCompletionContext`
        that only keeps the last 2 messages (1 user + 1 assistant).
        Bounded model context is useful when the model has a limit on the
        number of tokens it can process.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
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

                response = await agent.on_messages(
                    [TextMessage(content="Name two cities in North America.", source="user")], CancellationToken()
                )
                print(response.chat_message.content)  # type: ignore

                response = await agent.on_messages(
                    [TextMessage(content="My favorite color is blue.", source="user")], CancellationToken()
                )
                print(response.chat_message.content)  # type: ignore

                response = await agent.on_messages(
                    [TextMessage(content="Did I ask you any question?", source="user")], CancellationToken()
                )
                print(response.chat_message.content)  # type: ignore


            asyncio.run(main())

        .. code-block:: text

            Two cities in North America are New York City and Toronto.
            That's great! Blue is often associated with calmness and serenity. Do you have a specific shade of blue that you like, or any particular reason why it's your favorite?
            No, you didn't ask a question. I apologize for any misunderstanding. If you have something specific you'd like to discuss or ask, feel free to let me know!

        **Example 6: agent with memory**

        The following example shows how to use a list-based memory with the assistant agent.
        The memory is preloaded with some initial content.
        Under the hood, the memory is used to update the model context
        before making an inference, using the :meth:`~autogen_core.memory.Memory.update_context` method.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
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

                response = await agent.on_messages(
                    [TextMessage(content="One idea for a dinner.", source="user")], CancellationToken()
                )
                print(response.chat_message.content)  # type: ignore


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

        **Example 7: agent with `o1-mini`**

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


        **Example 8: agent using reasoning model with custom model context.**

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
        if reflect_on_tool_use and ModelFamily.is_claude(model_client.model_info["family"]):
            warnings.warn(
                "Claude models may not work with reflection on tool use because Claude requires that any requests including a previous tool use or tool result must include the original tools definition."
                "Consider setting reflect_on_tool_use to False. "
                "As an alternative, consider calling the agent in a loop until it stops producing tool calls. "
                "See [Single-Agent Team](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html#single-agent-team) "
                "for more details.",
                UserWarning,
                stacklevel=2,
            )
        self._model_client = model_client
        self._model_client_stream = model_client_stream
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

        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()

        self._reflect_on_tool_use = reflect_on_tool_use
        self._tool_call_summary_format = tool_call_summary_format
        self._is_running = False

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
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
        """
        Process the incoming messages with the assistant agent and yield events/responses as they happen.
        """

        # Gather all relevant state here
        agent_name = self.name
        model_context = self._model_context
        memory = self._memory
        system_messages = self._system_messages
        tools = self._tools
        handoff_tools = self._handoff_tools
        handoffs = self._handoffs
        model_client = self._model_client
        model_client_stream = self._model_client_stream
        reflect_on_tool_use = self._reflect_on_tool_use
        tool_call_summary_format = self._tool_call_summary_format

        # STEP 1: Add new user/handoff messages to the model context
        await self._add_messages_to_context(
            model_context=model_context,
            messages=messages,
        )

        # STEP 2: Update model context with any relevant memory
        inner_messages: List[AgentEvent | ChatMessage] = []
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
            tools=tools,
            handoff_tools=handoff_tools,
            agent_name=agent_name,
            cancellation_token=cancellation_token,
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
            tools=tools,
            handoff_tools=handoff_tools,
            handoffs=handoffs,
            model_client=model_client,
            model_client_stream=model_client_stream,
            reflect_on_tool_use=reflect_on_tool_use,
            tool_call_summary_format=tool_call_summary_format,
        ):
            yield output_event

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext,
        messages: Sequence[ChatMessage],
    ) -> None:
        """
        Add incoming user (and possibly handoff) messages to the model context.
        """
        for msg in messages:
            if isinstance(msg, HandoffMessage):
                # Add handoff context to the model context.
                for context_msg in msg.context:
                    await model_context.add_message(context_msg)
            await model_context.add_message(UserMessage(content=msg.content, source=msg.source))

    @staticmethod
    async def _update_model_context_with_memory(
        memory: Optional[Sequence[Memory]],
        model_context: ChatCompletionContext,
        agent_name: str,
    ) -> List[MemoryQueryEvent]:
        """
        If memory modules are present, update the model context and return the events produced.
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
        tools: List[BaseTool[Any, Any]],
        handoff_tools: List[BaseTool[Any, Any]],
        agent_name: str,
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[Union[CreateResult, ModelClientStreamingChunkEvent], None]:
        """
        Perform a model inference and yield either streaming chunk events or the final CreateResult.
        """
        all_messages = await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=system_messages + all_messages)

        all_tools = tools + handoff_tools

        if model_client_stream:
            model_result: Optional[CreateResult] = None
            async for chunk in model_client.create_stream(
                llm_messages, tools=all_tools, cancellation_token=cancellation_token
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
                llm_messages, tools=all_tools, cancellation_token=cancellation_token
            )
            yield model_result

    @classmethod
    async def _process_model_result(
        cls,
        model_result: CreateResult,
        inner_messages: List[AgentEvent | ChatMessage],
        cancellation_token: CancellationToken,
        agent_name: str,
        system_messages: List[SystemMessage],
        model_context: ChatCompletionContext,
        tools: List[BaseTool[Any, Any]],
        handoff_tools: List[BaseTool[Any, Any]],
        handoffs: Dict[str, HandoffBase],
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        reflect_on_tool_use: bool,
        tool_call_summary_format: str,
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        """
        Handle final or partial responses from model_result, including tool calls, handoffs,
        and reflection if needed.
        """

        # If direct text response (string)
        if isinstance(model_result.content, str):
            yield Response(
                chat_message=TextMessage(
                    content=model_result.content,
                    source=agent_name,
                    models_usage=model_result.usage,
                ),
                inner_messages=inner_messages,
            )
            return

        # Otherwise, we have function calls
        assert isinstance(model_result.content, list) and all(
            isinstance(item, FunctionCall) for item in model_result.content
        )

        # STEP 4A: Yield ToolCallRequestEvent
        tool_call_msg = ToolCallRequestEvent(
            content=model_result.content,
            source=agent_name,
            models_usage=model_result.usage,
        )
        event_logger.debug(tool_call_msg)
        inner_messages.append(tool_call_msg)
        yield tool_call_msg

        # STEP 4B: Execute tool calls
        executed_calls_and_results = await asyncio.gather(
            *[
                cls._execute_tool_call(
                    tool_call=call,
                    tools=tools,
                    handoff_tools=handoff_tools,
                    agent_name=agent_name,
                    cancellation_token=cancellation_token,
                )
                for call in model_result.content
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
            model_result=model_result,
            executed_calls_and_results=executed_calls_and_results,
            inner_messages=inner_messages,
            handoffs=handoffs,
            agent_name=agent_name,
        )
        if handoff_output:
            yield handoff_output
            return

        # STEP 4D: Reflect or summarize tool results
        if reflect_on_tool_use:
            async for reflection_response in AssistantAgent._reflect_on_tool_use_flow(
                system_messages=system_messages,
                model_client=model_client,
                model_client_stream=model_client_stream,
                model_context=model_context,
                agent_name=agent_name,
                inner_messages=inner_messages,
            ):
                yield reflection_response
        else:
            yield AssistantAgent._summarize_tool_use(
                executed_calls_and_results=executed_calls_and_results,
                inner_messages=inner_messages,
                handoffs=handoffs,
                tool_call_summary_format=tool_call_summary_format,
                agent_name=agent_name,
            )

    @staticmethod
    def _check_and_handle_handoff(
        model_result: CreateResult,
        executed_calls_and_results: List[Tuple[FunctionCall, FunctionExecutionResult]],
        inner_messages: List[AgentEvent | ChatMessage],
        handoffs: Dict[str, HandoffBase],
        agent_name: str,
    ) -> Optional[Response]:
        """
        Detect handoff calls, generate the HandoffMessage if needed, and return a Response.
        If multiple handoffs exist, only the first is used.
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
            for exec_call, exec_result in executed_calls_and_results:
                if exec_call.name not in handoffs:
                    tool_calls.append(exec_call)
                    tool_call_results.append(exec_result)

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

            # Return response for the first handoff
            return Response(
                chat_message=HandoffMessage(
                    content=selected_handoff.message,
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
        agent_name: str,
        inner_messages: List[AgentEvent | ChatMessage],
    ) -> AsyncGenerator[Response | ModelClientStreamingChunkEvent | ThoughtEvent, None]:
        """
        If reflect_on_tool_use=True, we do another inference based on tool results
        and yield the final text response (or streaming chunks).
        """
        all_messages = system_messages + await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=all_messages)

        reflection_result: Optional[CreateResult] = None

        if model_client_stream:
            async for chunk in model_client.create_stream(llm_messages):
                if isinstance(chunk, CreateResult):
                    reflection_result = chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
        else:
            reflection_result = await model_client.create(llm_messages)

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
        inner_messages: List[AgentEvent | ChatMessage],
        handoffs: Dict[str, HandoffBase],
        tool_call_summary_format: str,
        agent_name: str,
    ) -> Response:
        """
        If reflect_on_tool_use=False, create a summary message of all tool calls.
        """
        # Filter out calls which were actually handoffs
        normal_tool_calls = [(call, result) for call, result in executed_calls_and_results if call.name not in handoffs]
        tool_call_summaries: List[str] = []
        for tool_call, tool_call_result in normal_tool_calls:
            tool_call_summaries.append(
                tool_call_summary_format.format(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    result=tool_call_result.content,
                )
            )
        tool_call_summary = "\n".join(tool_call_summaries)
        return Response(
            chat_message=ToolCallSummaryMessage(
                content=tool_call_summary,
                source=agent_name,
            ),
            inner_messages=inner_messages,
        )

    @staticmethod
    async def _execute_tool_call(
        tool_call: FunctionCall,
        tools: List[BaseTool[Any, Any]],
        handoff_tools: List[BaseTool[Any, Any]],
        agent_name: str,
        cancellation_token: CancellationToken,
    ) -> Tuple[FunctionCall, FunctionExecutionResult]:
        """Execute a single tool call and return the result."""
        try:
            all_tools = tools + handoff_tools
            if not all_tools:
                raise ValueError("No tools are available.")
            tool = next((t for t in all_tools if t.name == tool_call.name), None)
            if tool is None:
                raise ValueError(f"The tool '{tool_call.name}' is not available.")
            arguments: Dict[str, Any] = json.loads(tool_call.arguments) if tool_call.arguments else {}
            result = await tool.run_json(arguments, cancellation_token)
            result_as_str = tool.return_value_as_string(result)
            return (
                tool_call,
                FunctionExecutionResult(
                    content=result_as_str,
                    call_id=tool_call.id,
                    is_error=False,
                    name=tool_call.name,
                ),
            )
        except Exception as e:
            return (
                tool_call,
                FunctionExecutionResult(
                    content=f"Error: {e}",
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
            tools=[tool.dump_component() for tool in self._tools],
            handoffs=list(self._handoffs.values()) if self._handoffs else None,
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
