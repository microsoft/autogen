from typing import Any, Mapping, Optional, Sequence
from autogen_core._cancellation_token import CancellationToken
from autogen_core.models import RequestUsage, FunctionExecutionResultMessage, ModelCapabilities, AssistantMessage, SystemMessage, UserMessage, FunctionExecutionResult
from autogen_core.models import ChatCompletionClient, CreateResult, LLMMessage
from autogen_core.tools import Tool, ToolSchema
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from typing_extensions import AsyncGenerator, Union
from autogen_ext.tools.semantic_kernel import KernelFunctionFromTool
from semantic_kernel.contents.function_call_content import FunctionCallContent
from autogen_core import FunctionCall
from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent


class SKChatCompletionAdapter(ChatCompletionClient):
    def __init__(self, sk_client: ChatCompletionClientBase):
        self._sk_client = sk_client
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

    def _convert_from_chat_message(self, message: ChatMessageContent, source: str = "assistant") -> LLMMessage:
        """Convert SK ChatMessageContent to Autogen LLMMessage"""
        if message.role == AuthorRole.SYSTEM:
            return SystemMessage(content=message.content)
        
        elif message.role == AuthorRole.USER:
            return UserMessage(content=message.content, source=source)
        
        elif message.role == AuthorRole.ASSISTANT:
            return AssistantMessage(content=message.content, source=source)
        
        elif message.role == AuthorRole.TOOL:
            return FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content=message.content, call_id="")]
            )
        
        raise ValueError(f"Unknown role: {message.role}")

    def _build_execution_settings(self, extra_create_args: Mapping[str, Any], tools: Sequence[Tool | ToolSchema]) -> PromptExecutionSettings:
        """Build PromptExecutionSettings from extra_create_args"""
        # Extract service_id if provided, otherwise use None
        service_id = extra_create_args.get("service_id")
        
        # If tools are available, configure function choice behavior with auto_invoke disabled
        function_choice_behavior = None
        if tools:
            function_choice_behavior = FunctionChoiceBehavior.Auto(auto_invoke=extra_create_args.get("auto_invoke", False))
        
        # Create settings with remaining args as extension_data
        settings = PromptExecutionSettings(
            service_id=service_id,
            extension_data=dict(extra_create_args),
            function_choice_behavior=function_choice_behavior
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
        new_tool_names = {tool.schema["name"] if isinstance(tool, Tool) else tool.name for tool in tools}

        # Remove tools that are no longer needed
        for tool_name in current_tool_names - new_tool_names:
            del self._tools_plugin.functions[tool_name]

        # Add or update tools
        for tool in tools:
            if isinstance(tool, Tool):
                # Convert Tool to KernelFunction using KernelFunctionFromTool
                kernel_function = KernelFunctionFromTool(tool, plugin_name="autogen_tools")
                self._tools_plugin.functions[tool.name] = kernel_function

    def _process_tool_calls(self, result: ChatMessageContent) -> list[FunctionCall]:
        """Process tool calls from SK ChatMessageContent"""
        function_calls = []
        for item in result.items:
            if isinstance(item, FunctionCallContent):
                # Extract plugin name and function name
                plugin_name = item.plugin_name or ""
                function_name = item.function_name or item.name
                if plugin_name:
                    full_name = f"{plugin_name}-{function_name}"
                else:
                    full_name = function_name
                    
                function_calls.append(
                    FunctionCall(
                        id=item.id,
                        name=full_name,
                        arguments=item.arguments or "{}"
                    )
                )
        return function_calls

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        if "kernel" not in extra_create_args:
            raise ValueError("kernel is required in extra_create_args")
            
        kernel = extra_create_args["kernel"]
        if not isinstance(kernel, Kernel):
            raise ValueError("kernel must be an instance of semantic_kernel.kernel.Kernel")
            
        chat_history = self._convert_to_chat_history(messages)
        
        # Build execution settings from extra args and tools
        settings = self._build_execution_settings(extra_create_args, tools)
        
        # Sync tools with kernel
        self._sync_tools_with_kernel(kernel, tools)
        
        result = await self._sk_client.get_chat_message_contents(
            chat_history,
            settings=settings,
            kernel=kernel
        )
        # Track token usage from result metadata
        prompt_tokens = 0
        completion_tokens = 0
        
        if result[0].metadata and 'usage' in result[0].metadata:
            usage = result[0].metadata['usage']
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)
        
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens

        # Process content based on whether there are tool calls
        content: Union[str, list[FunctionCall]]
        if any(isinstance(item, FunctionCallContent) for item in result[0].items):
            content = self._process_tool_calls(result[0])
            finish_reason = "function_calls"
        else:
            content = result[0].content
            finish_reason = "stop"
        
        return CreateResult(
            content=content,
            finish_reason=finish_reason,
            usage=RequestUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            ),
            cached=False
        )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        if "kernel" not in extra_create_args:
            raise ValueError("kernel is required in extra_create_args")
            
        kernel = extra_create_args["kernel"]
        if not isinstance(kernel, Kernel):
            raise ValueError("kernel must be an instance of semantic_kernel.kernel.Kernel")

        chat_history = self._convert_to_chat_history(messages)
        settings = self._build_execution_settings(extra_create_args, tools)
        self._sync_tools_with_kernel(kernel, tools)

        prompt_tokens = 0
        completion_tokens = 0
        accumulated_content = ""
        
        async for streaming_messages in self._sk_client.get_streaming_chat_message_contents(
            chat_history,
            settings=settings,
            kernel=kernel
        ):
            for msg in streaming_messages:
                if not isinstance(msg, StreamingChatMessageContent):
                    continue

                # Track token usage
                if msg.metadata and 'usage' in msg.metadata:
                    usage = msg.metadata['usage']
                    prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                    completion_tokens = getattr(usage, 'completion_tokens', 0)

                # Check for function calls
                if any(isinstance(item, FunctionCallContent) for item in msg.items):
                    function_calls = self._process_tool_calls(msg)
                    yield CreateResult(
                        content=function_calls,
                        finish_reason="function_calls",
                        usage=RequestUsage(
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens
                        ),
                        cached=False
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
                usage=RequestUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens
                ),
                cached=False
            )

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_completion_tokens
        )

    def total_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_completion_tokens
        )

    def count_tokens(self, messages: Sequence[LLMMessage]) -> int:
        chat_history = self._convert_to_chat_history(messages)
        total_tokens = 0
        for message in chat_history.messages:
            if message.metadata and 'usage' in message.metadata:
                usage = message.metadata['usage']
                total_tokens += getattr(usage, 'total_tokens', 0)
        return total_tokens

    def remaining_tokens(self, messages: Sequence[LLMMessage]) -> int:
        # Get total token count
        used_tokens = self.count_tokens(messages)
        # Assume max tokens from SK client if available, otherwise use default
        max_tokens = getattr(self._sk_client, 'max_tokens', 4096)
        return max_tokens - used_tokens

    @property
    def capabilities(self) -> ModelCapabilities:
        # Return something consistent with the underlying SK client
        return {
            "vision": False,
            "function_calling": self._sk_client.SUPPORTS_FUNCTION_CALLING,
            "json_output": False,
        }
