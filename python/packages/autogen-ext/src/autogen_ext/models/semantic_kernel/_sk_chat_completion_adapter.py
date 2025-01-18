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

    Args:
        sk_client (ChatCompletionClientBase):
            The Semantic Kernel client to wrap (e.g., AzureChatCompletion, GoogleAIChatCompletion, OllamaChatCompletion).

    Example usage:

    .. code-block:: python

        import asyncio
        from semantic_kernel import Kernel
        from semantic_kernel.memory.null_memory import NullMemory
        from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
        from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
            AzureChatPromptExecutionSettings,
        )
        from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion
        from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion, OllamaChatPromptExecutionSettings
        from autogen_core.models import SystemMessage, UserMessage, LLMMessage
        from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
        from autogen_core import CancellationToken
        from autogen_core.tools import BaseTool
        from pydantic import BaseModel


        # 1) Basic tool definition (for demonstration)
        class CalculatorArgs(BaseModel):
            a: float
            b: float


        class CalculatorResult(BaseModel):
            result: float


        class CalculatorTool(BaseTool[CalculatorArgs, CalculatorResult]):
            def __init__(self) -> None:
                super().__init__(
                    args_type=CalculatorArgs,
                    return_type=CalculatorResult,
                    name="calculator",
                    description="Add two numbers together",
                )

            async def run(self, args: CalculatorArgs, cancellation_token: CancellationToken) -> CalculatorResult:
                return CalculatorResult(result=args.a + args.b)


        async def main():
            # 2) Create a Semantic Kernel instance (with null memory for simplicity)
            kernel = Kernel(memory=NullMemory())

            # ----------------------------------------------------------------
            # Example A: Azure OpenAI
            # ----------------------------------------------------------------
            deployment_name = "<AZURE_OPENAI_DEPLOYMENT_NAME>"
            endpoint = "<AZURE_OPENAI_ENDPOINT>"
            api_key = "<AZURE_OPENAI_API_KEY>"

            azure_client = AzureChatCompletion(deployment_name=deployment_name, endpoint=endpoint, api_key=api_key)
            azure_request_settings = AzureChatPromptExecutionSettings(temperature=0.8)
            azure_adapter = SKChatCompletionAdapter(sk_client=azure_client, default_prompt_settings=azure_request_settings)

            # ----------------------------------------------------------------
            # Example B: Google Gemini
            # ----------------------------------------------------------------
            google_api_key = "<GCP_API_KEY>"
            google_model = "gemini-1.5-flash"
            google_client = GoogleAIChatCompletion(gemini_model_id=google_model, api_key=google_api_key)
            google_adapter = SKChatCompletionAdapter(sk_client=google_client)

            # ----------------------------------------------------------------
            # Example C: Ollama (local Llama-based model)
            # ----------------------------------------------------------------
            ollama_client = OllamaChatCompletion(
                service_id="ollama",  # custom ID
                host="http://localhost:11434",
                ai_model_id="llama3.1",
            )
            request_settings = OllamaChatPromptExecutionSettings(
                # For model specific settings, specify them in the options dictionary.
                # For more information on the available options, refer to the Ollama API documentation:
                # https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values
                options={
                    "temperature": 0.8,
                },
            )
            ollama_adapter = SKChatCompletionAdapter(sk_client=ollama_client, default_prompt_settings=request_settings)

            # 3) Create a tool and register it with the kernel
            calc_tool = CalculatorTool()

            # 4) Prepare messages for a chat completion
            messages: list[LLMMessage] = [
                SystemMessage(content="You are a helpful assistant."),
                UserMessage(content="What is 2 + 2?", source="user"),
            ]

            # 5) Invoke chat completion with different adapters
            # Azure example
            azure_result = await azure_adapter.create(
                messages=messages,
                tools=[calc_tool],
                extra_create_args={"kernel": kernel, "prompt_execution_settings": azure_request_settings},
            )
            print("Azure result:", azure_result.content)

            # Google example
            google_result = await google_adapter.create(
                messages=messages,
                tools=[calc_tool],
                extra_create_args={"kernel": kernel},
            )
            print("Google result:", google_result.content)

            # Ollama example
            ollama_result = await ollama_adapter.create(
                messages=messages,
                tools=[calc_tool],
                extra_create_args={"kernel": kernel, "prompt_execution_settings": request_settings},
            )
            print("Ollama result:", ollama_result.content)


        if __name__ == "__main__":
            asyncio.run(main())
    """

    def __init__(
        self,
        sk_client: ChatCompletionClientBase,
        model_info: Optional[ModelInfo] = None,
        service_id: Optional[str] = None,
        default_prompt_settings: Optional[PromptExecutionSettings] = None,
    ):
        self._service_id = service_id
        self._default_prompt_settings = default_prompt_settings
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

        1) `"kernel"` (required):
            An instance of :class:`semantic_kernel.Kernel` used to execute the request.
            If not provided, a ValueError is raised.

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
        if "kernel" not in extra_create_args:
            raise ValueError("kernel is required in extra_create_args")

        kernel = extra_create_args["kernel"]
        if not isinstance(kernel, Kernel):
            raise ValueError("kernel must be an instance of semantic_kernel.kernel.Kernel")

        chat_history = self._convert_to_chat_history(messages)

        # Build execution settings from extra args and tools
        user_settings = extra_create_args.get("prompt_execution_settings", None)
        if user_settings is None:
            user_settings = self._default_prompt_settings
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

        return CreateResult(
            content=content,
            finish_reason=finish_reason,
            usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            cached=False,
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

        1) `"kernel"` (required):
            An instance of :class:`semantic_kernel.Kernel` used to execute the request.
            If not provided, a ValueError is raised.

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
        if "kernel" not in extra_create_args:
            raise ValueError("kernel is required in extra_create_args")

        kernel = extra_create_args["kernel"]
        if not isinstance(kernel, Kernel):
            raise ValueError("kernel must be an instance of semantic_kernel.kernel.Kernel")

        chat_history = self._convert_to_chat_history(messages)
        user_settings = extra_create_args.get("prompt_execution_settings", None)
        if user_settings is None:
            user_settings = self._default_prompt_settings
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
            yield CreateResult(
                content=accumulated_content,
                finish_reason="stop",
                usage=RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
                cached=False,
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
