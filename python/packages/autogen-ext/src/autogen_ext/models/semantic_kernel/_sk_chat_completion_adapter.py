import json
from typing import Any, Literal, Mapping, Optional, Sequence

from autogen_core import FunctionCall
from autogen_core._cancellation_token import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import BaseTool, Tool, ToolSchema
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.kernel import Kernel
from typing_extensions import AsyncGenerator, Union

from autogen_ext.tools.semantic_kernel import KernelFunctionFromTool

from .._utils.parse_r1_content import parse_r1_content


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

        Anthropic models:

        .. code-block:: bash

            pip install "autogen-ext[semantic-kernel-anthropic]"

        .. code-block:: python

            import asyncio
            import os

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.models import UserMessage
            from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.anthropic import AnthropicChatCompletion, AnthropicChatPromptExecutionSettings
            from semantic_kernel.memory.null_memory import NullMemory


            async def main() -> None:
                sk_client = AnthropicChatCompletion(
                    ai_model_id="claude-3-5-sonnet-20241022",
                    api_key=os.environ["ANTHROPIC_API_KEY"],
                    service_id="my-service-id",  # Optional; for targeting specific services within Semantic Kernel
                )
                settings = AnthropicChatPromptExecutionSettings(
                    temperature=0.2,
                )

                model_client = SKChatCompletionAdapter(sk_client, kernel=Kernel(memory=NullMemory()), prompt_settings=settings)

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

        Google Gemini models:

        .. code-block:: bash

            pip install "autogen-ext[semantic-kernel-google]"

        .. code-block:: python

            import asyncio
            import os

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.models import UserMessage
            from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.google.google_ai import (
                GoogleAIChatCompletion,
                GoogleAIChatPromptExecutionSettings,
            )
            from semantic_kernel.memory.null_memory import NullMemory


            async def main() -> None:
                sk_client = GoogleAIChatCompletion(
                    gemini_model_id="gemini-1.5-flash",
                    api_key=os.environ["GEMINI_API_KEY"],
                )
                settings = GoogleAIChatPromptExecutionSettings(
                    temperature=0.2,
                )

                model_client = SKChatCompletionAdapter(sk_client, kernel=Kernel(memory=NullMemory()), prompt_settings=settings)

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
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN
        )
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._tools_plugin: Optional[KernelPlugin] = None

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
                    # Handle list of str/Image - would need to convert to SK content types
                    chat_history.add_user_message(str(msg.content))

            elif msg.type == "AssistantMessage":
                if isinstance(msg.content, str):
                    chat_history.add_assistant_message(msg.content)
                else:
                    # Handle function calls - would need to convert to SK function call format
                    chat_history.add_assistant_message(str(msg.content))

            elif msg.type == "FunctionExecutionResultMessage":
                for result in msg.content:
                    chat_history.add_tool_message(result.content)

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
        # Create new plugin if none exists
        if not self._tools_plugin:
            self._tools_plugin = KernelPlugin(name="autogen_tools")
            kernel.add_plugin(self._tools_plugin)

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
                kernel_function = KernelFunctionFromTool(tool, plugin_name="autogen_tools")  # type: ignore
                self._tools_plugin.functions[tool.schema["name"]] = kernel_function

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
        json_output: Optional[bool] = None,
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

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
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
        kernel = self._get_kernel(extra_create_args)
        chat_history = self._convert_to_chat_history(messages)
        user_settings = self._get_prompt_settings(extra_create_args)
        settings = self._build_execution_settings(user_settings, tools)
        self._sync_tools_with_kernel(kernel, tools)

        prompt_tokens = 0
        completion_tokens = 0
        accumulated_content = ""

        async for streaming_messages in self._sk_client.get_streaming_chat_message_contents(
            chat_history, settings=settings, kernel=kernel
        ):
            for msg in streaming_messages:
                if not isinstance(msg, StreamingChatMessageContent):
                    continue

                # Track token usage
                if msg.metadata and "usage" in msg.metadata:
                    usage = msg.metadata["usage"]
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)

                # Check for function calls
                if any(isinstance(item, FunctionCallContent) for item in msg.items):
                    function_calls = self._process_tool_calls(msg)
                    yield CreateResult(
                        content=function_calls,
                        finish_reason="function_calls",
                        usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
                        cached=False,
                    )
                    return

                # Handle text content
                if msg.content:
                    accumulated_content += msg.content
                    yield msg.content

        # Final yield if there was text content
        if accumulated_content:
            self._total_prompt_tokens += prompt_tokens
            self._total_completion_tokens += completion_tokens

            if isinstance(accumulated_content, str) and self._model_info["family"] == ModelFamily.R1:
                thought, accumulated_content = parse_r1_content(accumulated_content)
            else:
                thought = None

            yield CreateResult(
                content=accumulated_content,
                finish_reason="stop",
                usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
                cached=False,
                thought=thought,
            )

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
