import json
import logging
import warnings
from typing import Any, Literal, Mapping, Optional, Sequence, Union

from autogen_core import EVENT_LOGGER_NAME, FunctionCall
from autogen_core._cancellation_token import CancellationToken
from autogen_core.logging import LLMCallEvent, LLMStreamEndEvent, LLMStreamStartEvent
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    validate_model_info,
)
from autogen_core.tools import BaseTool, Tool, ToolSchema
from pydantic import BaseModel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents import (
    ChatHistory,
    ChatMessageContent,
    FinishReason,
    FunctionCallContent,
    FunctionResultContent,
)
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.kernel import Kernel
from typing_extensions import AsyncGenerator

from autogen_ext.tools.semantic_kernel import KernelFunctionFromTool, KernelFunctionFromToolSchema

from .._utils.parse_r1_content import parse_r1_content

logger = logging.getLogger(EVENT_LOGGER_NAME)


def ensure_serializable(data: BaseModel) -> BaseModel:
    """
    Workaround for https://github.com/pydantic/pydantic/issues/7713, see https://github.com/pydantic/pydantic/issues/7713#issuecomment-2604574418
    """
    try:
        json.dumps(data)
    except TypeError:
        # use `vars` to coerce nested data into dictionaries
        data_json_from_dicts = json.dumps(data, default=lambda x: vars(x))  # type: ignore
        data_obj = json.loads(data_json_from_dicts)
        data = type(data)(**data_obj)
    return data


class SKChatCompletionAdapter(ChatCompletionClient):
    """
    SKChatCompletionAdapter is an adapter that allows using Semantic Kernel model clients
    as Autogen ChatCompletion clients. This makes it possible to seamlessly integrate
    Semantic Kernel connectors (e.g., Azure OpenAI, Google Gemini, Ollama, etc.) into
    Autogen agents that rely on a ChatCompletionClient interface.

    By leveraging this adapter, you can:

    - Pass in a `Kernel` and any supported Semantic Kernel `ChatCompletionClientBase` connector.
    - Provide tools (via Autogen `Tool` or `ToolSchema`) for function calls during chat completion.
    - Stream responses or retrieve them in a single request.
    - Provide prompt settings to control the chat completion behavior either globally through the constructor
        or on a per-request basis through the `extra_create_args` dictionary.

    The list of extras that can be installed:

    - `semantic-kernel-anthropic`: Install this extra to use Anthropic models.
    - `semantic-kernel-google`: Install this extra to use Google Gemini models.
    - `semantic-kernel-ollama`: Install this extra to use Ollama models.
    - `semantic-kernel-mistralai`: Install this extra to use MistralAI models.
    - `semantic-kernel-aws`: Install this extra to use AWS models.
    - `semantic-kernel-hugging-face`: Install this extra to use Hugging Face models.

    Args:
        sk_client (ChatCompletionClientBase):
            The Semantic Kernel client to wrap (e.g., AzureChatCompletion, GoogleAIChatCompletion, OllamaChatCompletion).
        kernel (Optional[Kernel]):
            The Semantic Kernel instance to use for executing requests. If not provided, one must be passed
            in the extra_create_args for each request.
        prompt_settings (Optional[PromptExecutionSettings]):
            Default prompt execution settings to use. Can be overridden per request.
        model_info (Optional[ModelInfo]):
            Information about the model's capabilities.
        service_id (Optional[str]):
            Optional service identifier.

    Examples:

        Anthropic models with function calling:

        .. code-block:: bash

            pip install "autogen-ext[semantic-kernel-anthropic]"

        .. code-block:: python

            import asyncio
            import os

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core.models import ModelFamily, UserMessage
            from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.anthropic import AnthropicChatCompletion, AnthropicChatPromptExecutionSettings
            from semantic_kernel.memory.null_memory import NullMemory


            async def get_weather(city: str) -> str:
                \"\"\"Get the weather for a city.\"\"\"
                return f"The weather in {city} is 75 degrees."


            async def main() -> None:
                sk_client = AnthropicChatCompletion(
                    ai_model_id="claude-3-5-sonnet-20241022",
                    api_key=os.environ["ANTHROPIC_API_KEY"],
                    service_id="my-service-id",  # Optional; for targeting specific services within Semantic Kernel
                )
                settings = AnthropicChatPromptExecutionSettings(
                    temperature=0.2,
                )

                model_client = SKChatCompletionAdapter(
                    sk_client,
                    kernel=Kernel(memory=NullMemory()),
                    prompt_settings=settings,
                    model_info={
                        "function_calling": True,
                        "json_output": True,
                        "vision": True,
                        "family": ModelFamily.CLAUDE_3_5_SONNET,
                        "structured_output": True,
                    },
                )

                # Call the model directly.
                response = await model_client.create([UserMessage(content="What is the capital of France?", source="test")])
                print(response)

                # Create an assistant agent with the model client.
                assistant = AssistantAgent(
                    "assistant", model_client=model_client, system_message="You are a helpful assistant.", tools=[get_weather]
                )
                # Call the assistant with a task.
                await Console(assistant.run_stream(task="What is the weather in Paris and London?"))


            asyncio.run(main())


        Google Gemini models with function calling:

        .. code-block:: bash

            pip install "autogen-ext[semantic-kernel-google]"

        .. code-block:: python

            import asyncio
            import os

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core.models import UserMessage, ModelFamily
            from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.google.google_ai import (
                GoogleAIChatCompletion,
                GoogleAIChatPromptExecutionSettings,
            )
            from semantic_kernel.memory.null_memory import NullMemory


            def get_weather(city: str) -> str:
                \"\"\"Get the weather for a city.\"\"\"
                return f"The weather in {city} is 75 degrees."


            async def main() -> None:
                sk_client = GoogleAIChatCompletion(
                    gemini_model_id="gemini-2.0-flash",
                    api_key=os.environ["GEMINI_API_KEY"],
                )
                settings = GoogleAIChatPromptExecutionSettings(
                    temperature=0.2,
                )

                kernel = Kernel(memory=NullMemory())

                model_client = SKChatCompletionAdapter(
                    sk_client,
                    kernel=kernel,
                    prompt_settings=settings,
                    model_info={
                        "family": ModelFamily.GEMINI_2_0_FLASH,
                        "function_calling": True,
                        "json_output": True,
                        "vision": True,
                        "structured_output": True,
                    },
                )

                # Call the model directly.
                model_result = await model_client.create(
                    messages=[UserMessage(content="What is the capital of France?", source="User")]
                )
                print(model_result)

                # Create an assistant agent with the model client.
                assistant = AssistantAgent(
                    "assistant", model_client=model_client, tools=[get_weather], system_message="You are a helpful assistant."
                )
                # Call the assistant with a task.
                stream = assistant.run_stream(task="What is the weather in Paris and London?")
                await Console(stream)


            asyncio.run(main())


        Ollama models:

        .. code-block:: bash

            pip install "autogen-ext[semantic-kernel-ollama]"

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.models import UserMessage
            from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion, OllamaChatPromptExecutionSettings
            from semantic_kernel.memory.null_memory import NullMemory


            async def main() -> None:
                sk_client = OllamaChatCompletion(
                    host="http://localhost:11434",
                    ai_model_id="llama3.2:latest",
                )
                ollama_settings = OllamaChatPromptExecutionSettings(
                    options={"temperature": 0.5},
                )

                model_client = SKChatCompletionAdapter(
                    sk_client, kernel=Kernel(memory=NullMemory()), prompt_settings=ollama_settings
                )

                # Call the model directly.
                model_result = await model_client.create(
                    messages=[UserMessage(content="What is the capital of France?", source="User")]
                )
                print(model_result)

                # Create an assistant agent with the model client.
                assistant = AssistantAgent("assistant", model_client=model_client)
                # Call the assistant with a task.
                result = await assistant.run(task="What is the capital of France?")
                print(result)


            asyncio.run(main())

    """

    def __init__(
        self,
        sk_client: ChatCompletionClientBase,
        kernel: Optional[Kernel] = None,
        prompt_settings: Optional[PromptExecutionSettings] = None,
        model_info: Optional[ModelInfo] = None,
        service_id: Optional[str] = None,
    ):
        self._service_id = service_id
        self._kernel = kernel
        self._prompt_settings = prompt_settings
        self._sk_client = sk_client
        self._model_info = model_info or ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=False
        )
        validate_model_info(self._model_info)
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._tools_plugin: KernelPlugin = KernelPlugin(name="autogen_tools")

    def _convert_to_chat_history(self, messages: Sequence[LLMMessage]) -> ChatHistory:
        """Convert Autogen LLMMessages to SK ChatHistory"""
        chat_history = ChatHistory()

        for msg in messages:
            if msg.type == "SystemMessage":
                chat_history.add_system_message(msg.content)

            elif msg.type == "UserMessage":
                if isinstance(msg.content, str):
                    chat_history.add_user_message(msg.content)
                else:
                    # Handle list of str/Image - convert to string for now
                    chat_history.add_user_message(str(msg.content))

            elif msg.type == "AssistantMessage":
                # Check if it's a function-call style message
                if isinstance(msg.content, list) and all(isinstance(fc, FunctionCall) for fc in msg.content):
                    # If there's a 'thought' field, you can add that as plain assistant text
                    if msg.thought:
                        chat_history.add_assistant_message(msg.thought)

                    function_call_contents: list[FunctionCallContent] = []
                    for fc in msg.content:
                        function_call_contents.append(
                            FunctionCallContent(
                                id=fc.id,
                                name=fc.name,
                                plugin_name=self._tools_plugin.name,
                                function_name=fc.name,
                                arguments=fc.arguments,
                            )
                        )

                    # Mark the assistant's message as tool-calling
                    chat_history.add_assistant_message(
                        function_call_contents,
                        finish_reason=FinishReason.TOOL_CALLS,
                    )
                else:
                    # Plain assistant text
                    chat_history.add_assistant_message(msg.content)

            elif msg.type == "FunctionExecutionResultMessage":
                # Add each function result as a separate tool message
                tool_results: list[FunctionResultContent] = []
                for result in msg.content:
                    tool_results.append(
                        FunctionResultContent(
                            id=result.call_id,
                            plugin_name=self._tools_plugin.name,
                            function_name=result.name,
                            result=result.content,
                        )
                    )
                # A single "tool" message with one or more results
                chat_history.add_tool_message(tool_results)

        return chat_history

    def _build_execution_settings(
        self, default_prompt_settings: Optional[PromptExecutionSettings], tools: Sequence[Tool | ToolSchema]
    ) -> PromptExecutionSettings:
        """Build PromptExecutionSettings from extra_create_args"""

        if default_prompt_settings is not None:
            prompt_args: dict[str, Any] = default_prompt_settings.prepare_settings_dict()  # type: ignore
        else:
            prompt_args = {}

        # If tools are available, configure function choice behavior with auto_invoke disabled
        function_choice_behavior = None
        if tools:
            function_choice_behavior = FunctionChoiceBehavior.Auto(  # type: ignore
                auto_invoke=False
            )

        # Create settings with remaining args as extension_data
        settings = PromptExecutionSettings(
            service_id=self._service_id,
            extension_data=prompt_args,
            function_choice_behavior=function_choice_behavior,
        )

        return settings

    def _sync_tools_with_kernel(self, kernel: Kernel, tools: Sequence[Tool | ToolSchema]) -> None:
        """Sync tools with kernel by updating the plugin"""
        # Get current tool names in plugin
        current_tool_names = set(self._tools_plugin.functions.keys())

        # Get new tool names
        new_tool_names = {tool.schema["name"] if isinstance(tool, Tool) else tool["name"] for tool in tools}

        # Remove tools that are no longer needed
        for tool_name in current_tool_names - new_tool_names:
            del self._tools_plugin.functions[tool_name]

        # Add or update tools
        for tool in tools:
            if isinstance(tool, BaseTool):
                # Convert Tool to KernelFunction using KernelFunctionFromTool
                kernel_function = KernelFunctionFromTool(tool)  # type: ignore
                self._tools_plugin.functions[tool.schema["name"]] = kernel_function
            else:
                kernel_function = KernelFunctionFromToolSchema(tool)  # type: ignore
                self._tools_plugin.functions[tool.get("name")] = kernel_function  # type: ignore

        kernel.add_plugin(self._tools_plugin)

    def _process_tool_calls(self, result: ChatMessageContent) -> list[FunctionCall]:
        """Process tool calls from SK ChatMessageContent"""
        function_calls: list[FunctionCall] = []
        for item in result.items:
            if isinstance(item, FunctionCallContent):
                # Extract plugin name and function name
                plugin_name = item.plugin_name or ""
                function_name = item.function_name
                if plugin_name:
                    full_name = f"{plugin_name}-{function_name}"
                else:
                    full_name = function_name

                if item.id is None:
                    raise ValueError("Function call ID is required")

                if isinstance(item.arguments, Mapping):
                    arguments = json.dumps(item.arguments)
                else:
                    arguments = item.arguments or "{}"

                function_calls.append(FunctionCall(id=item.id, name=full_name, arguments=arguments))
        return function_calls

    def _get_kernel(self, extra_create_args: Mapping[str, Any]) -> Kernel:
        kernel = extra_create_args.get("kernel", self._kernel)
        if not kernel:
            raise ValueError("kernel must be provided either in constructor or extra_create_args")
        if not isinstance(kernel, Kernel):
            raise ValueError("kernel must be an instance of semantic_kernel.kernel.Kernel")
        return kernel

    def _get_prompt_settings(self, extra_create_args: Mapping[str, Any]) -> Optional[PromptExecutionSettings]:
        return extra_create_args.get("prompt_execution_settings", None) or self._prompt_settings

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Create a chat completion using the Semantic Kernel client.

        The `extra_create_args` dictionary can include two special keys:

        1) `"kernel"` (optional):
            An instance of :class:`semantic_kernel.Kernel` used to execute the request.
            If not provided either in constructor or extra_create_args, a ValueError is raised.

        2) `"prompt_execution_settings"` (optional):
            An instance of a :class:`PromptExecutionSettings` subclass corresponding to the
            underlying Semantic Kernel client (e.g., `AzureChatPromptExecutionSettings`,
            `GoogleAIChatPromptExecutionSettings`). If not provided, the adapter's default
            prompt settings will be used.

        Args:
            messages: The list of LLM messages to send.
            tools: The tools that may be invoked during the chat.
            json_output: Whether the model is expected to return JSON.
            extra_create_args: Additional arguments to control the chat completion behavior.
            cancellation_token: Token allowing cancellation of the request.

        Returns:
            CreateResult: The result of the chat completion.
        """
        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            raise ValueError("structured output is not currently supported in SKChatCompletionAdapter")

        # Handle tool_choice parameter
        if tool_choice != "auto":
            warnings.warn(
                "tool_choice parameter is specified but may not be fully supported by SKChatCompletionAdapter.",
                stacklevel=2,
            )

        kernel = self._get_kernel(extra_create_args)

        chat_history = self._convert_to_chat_history(messages)
        user_settings = self._get_prompt_settings(extra_create_args)
        settings = self._build_execution_settings(user_settings, tools)

        # Sync tools with kernel
        self._sync_tools_with_kernel(kernel, tools)

        result = await self._sk_client.get_chat_message_contents(chat_history, settings=settings, kernel=kernel)
        # Track token usage from result metadata
        prompt_tokens = 0
        completion_tokens = 0

        if result[0].metadata and "usage" in result[0].metadata:
            usage = result[0].metadata["usage"]
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)

        logger.info(
            LLMCallEvent(
                messages=[msg.model_dump() for msg in chat_history],
                response=ensure_serializable(result[0]).model_dump(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens

        # Process content based on whether there are tool calls
        content: Union[str, list[FunctionCall]]
        if any(isinstance(item, FunctionCallContent) for item in result[0].items):
            content = self._process_tool_calls(result[0])
            finish_reason: Literal["function_calls", "stop"] = "function_calls"
        else:
            content = result[0].content
            finish_reason = "stop"

        if isinstance(content, str) and self._model_info["family"] == ModelFamily.R1:
            thought, content = parse_r1_content(content)
        else:
            thought = None

        return CreateResult(
            content=content,
            finish_reason=finish_reason,
            usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            cached=False,
            thought=thought,
        )

    @staticmethod
    def _merge_function_call_content(existing_call: FunctionCallContent, new_chunk: FunctionCallContent) -> None:
        """Helper to merge partial argument chunks from new_chunk into existing_call."""
        if isinstance(existing_call.arguments, str) and isinstance(new_chunk.arguments, str):
            existing_call.arguments += new_chunk.arguments
        elif isinstance(existing_call.arguments, dict) and isinstance(new_chunk.arguments, dict):
            existing_call.arguments.update(new_chunk.arguments)
        elif not existing_call.arguments or existing_call.arguments in ("{}", ""):
            # If existing had no arguments yet, just take the new one
            existing_call.arguments = new_chunk.arguments
        else:
            # If there's a mismatch (str vs dict), handle as needed
            warnings.warn("Mismatch in argument types during merge. Existing arguments retained.", stacklevel=2)

        # Optionally update name/function_name if newly provided
        if new_chunk.name:
            existing_call.name = new_chunk.name
        if new_chunk.plugin_name:
            existing_call.plugin_name = new_chunk.plugin_name
        if new_chunk.function_name:
            existing_call.function_name = new_chunk.function_name

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Create a streaming chat completion using the Semantic Kernel client.

        The `extra_create_args` dictionary can include two special keys:

        1) `"kernel"` (optional):
            An instance of :class:`semantic_kernel.Kernel` used to execute the request.
            If not provided either in constructor or extra_create_args, a ValueError is raised.

        2) `"prompt_execution_settings"` (optional):
            An instance of a :class:`PromptExecutionSettings` subclass corresponding to the
            underlying Semantic Kernel client (e.g., `AzureChatPromptExecutionSettings`,
            `GoogleAIChatPromptExecutionSettings`). If not provided, the adapter's default
            prompt settings will be used.

        Args:
            messages: The list of LLM messages to send.
            tools: The tools that may be invoked during the chat.
            json_output: Whether the model is expected to return JSON.
            extra_create_args: Additional arguments to control the chat completion behavior.
            cancellation_token: Token allowing cancellation of the request.

        Yields:
            Union[str, CreateResult]: Either a string chunk of the response or a CreateResult containing function calls.
        """

        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            raise ValueError("structured output is not currently supported in SKChatCompletionAdapter")

        # Handle tool_choice parameter
        if tool_choice != "auto":
            warnings.warn(
                "tool_choice parameter is specified but may not be fully supported by SKChatCompletionAdapter.",
                stacklevel=2,
            )

        kernel = self._get_kernel(extra_create_args)
        chat_history = self._convert_to_chat_history(messages)
        user_settings = self._get_prompt_settings(extra_create_args)
        settings = self._build_execution_settings(user_settings, tools)
        self._sync_tools_with_kernel(kernel, tools)

        prompt_tokens = 0
        completion_tokens = 0
        accumulated_text = ""

        # Keep track of in-progress function calls. Keyed by ID
        # because partial chunks for the same function call might arrive separately.
        function_calls_in_progress: dict[str, FunctionCallContent] = {}

        # Track the ID of the last function call we saw so we can continue
        # accumulating chunk arguments for that call if new items have id=None
        last_function_call_id: Optional[str] = None

        first_chunk = True

        async for streaming_messages in self._sk_client.get_streaming_chat_message_contents(
            chat_history, settings=settings, kernel=kernel
        ):
            if first_chunk:
                first_chunk = False
                # Emit the start event.
                logger.info(
                    LLMStreamStartEvent(
                        messages=[msg.model_dump() for msg in chat_history],
                    )
                )
            for msg in streaming_messages:
                # Track token usage
                if msg.metadata and "usage" in msg.metadata:
                    usage = msg.metadata["usage"]
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)

                # Process function call deltas
                for item in msg.items:
                    if isinstance(item, FunctionCallContent):
                        # If the chunk has a valid ID, we start or continue that ID explicitly
                        if item.id:
                            last_function_call_id = item.id
                            if last_function_call_id not in function_calls_in_progress:
                                function_calls_in_progress[last_function_call_id] = item
                            else:
                                # Merge partial arguments into existing call
                                existing_call = function_calls_in_progress[last_function_call_id]
                                self._merge_function_call_content(existing_call, item)
                        else:
                            # item.id is None, so we assume it belongs to the last known ID
                            if not last_function_call_id:
                                # No call in progress means we can't merge
                                # You could either skip or raise an error here
                                warnings.warn(
                                    "Received function call chunk with no ID and no call in progress.", stacklevel=2
                                )
                                continue

                            existing_call = function_calls_in_progress[last_function_call_id]
                            # Merge partial chunk
                            self._merge_function_call_content(existing_call, item)

                # Check if the model signaled tool_calls finished
                if msg.finish_reason == "tool_calls" and function_calls_in_progress:
                    calls_to_yield: list[FunctionCall] = []
                    for _, call_content in function_calls_in_progress.items():
                        plugin_name = call_content.plugin_name or ""
                        function_name = call_content.function_name
                        if plugin_name:
                            full_name = f"{plugin_name}-{function_name}"
                        else:
                            full_name = function_name

                        if isinstance(call_content.arguments, dict):
                            arguments = json.dumps(call_content.arguments)
                        else:
                            assert isinstance(call_content.arguments, str)
                            arguments = call_content.arguments or "{}"

                        calls_to_yield.append(
                            FunctionCall(
                                id=call_content.id or "unknown_id",
                                name=full_name,
                                arguments=arguments,
                            )
                        )
                    # Yield all function calls in progress
                    yield CreateResult(
                        content=calls_to_yield,
                        finish_reason="function_calls",
                        usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
                        cached=False,
                    )
                    return

                # Handle any plain text in the message
                if msg.content:
                    accumulated_text += msg.content
                    yield msg.content

        # If we exit the loop without tool calls finishing, yield whatever text was accumulated
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens

        thought = None
        if isinstance(accumulated_text, str) and self._model_info["family"] == ModelFamily.R1:
            thought, accumulated_text = parse_r1_content(accumulated_text)

        result = CreateResult(
            content=accumulated_text,
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            cached=False,
            thought=thought,
        )

        # Emit the end event.
        logger.info(
            LLMStreamEndEvent(
                response=result.model_dump(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

        yield result

    async def close(self) -> None:
        pass  # No explicit close method in SK client?

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=self._total_prompt_tokens, completion_tokens=self._total_completion_tokens)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=self._total_prompt_tokens, completion_tokens=self._total_completion_tokens)

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        chat_history = self._convert_to_chat_history(messages)
        total_tokens = 0
        for message in chat_history.messages:
            if message.metadata and "usage" in message.metadata:
                usage = message.metadata["usage"]
                total_tokens += getattr(usage, "total_tokens", 0)
        return total_tokens

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        # Get total token count
        used_tokens = self.count_tokens(messages)
        # Assume max tokens from SK client if available, otherwise use default
        max_tokens = getattr(self._sk_client, "max_tokens", 4096)
        return max_tokens - used_tokens

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info
