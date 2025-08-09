"""
OpenAI Responses API Client for GPT-5 optimized interactions.

This module provides specialized clients for OpenAI's Responses API, which is designed
for GPT-5 models and provides enhanced features like chain-of-thought (CoT) preservation
across conversation turns, reduced reasoning tokens, and improved cache hit rates.

The Responses API differs from Chat Completions API in several key ways:
- Preserves reasoning context between turns for better performance
- Supports additional GPT-5 specific parameters like `preambles`
- Designed specifically for reasoning models like GPT-5
- Lower latency due to CoT caching and fewer regenerated reasoning tokens

Examples:
    Basic GPT-5 Responses API usage::

        from autogen_ext.models.openai import OpenAIResponsesAPIClient
        from autogen_core.models import UserMessage

        client = OpenAIResponsesAPIClient(model="gpt-5")

        response = await client.create(
            input="Solve this complex math problem: What is the derivative of x^3 + 2x^2 - 5x + 3?",
            reasoning_effort="high",
            verbosity="medium",
            preambles=True,
        )

        # Access reasoning and response
        print(f"Reasoning: {response.thought}")
        print(f"Response: {response.content}")

        # Use the response for follow-up with preserved CoT
        follow_up = await client.create(
            input="Now integrate that result",
            previous_response_id=response.response_id,  # Preserve CoT context
            reasoning_effort="medium",
        )

    Multi-turn conversation with CoT preservation::

        # First turn
        response1 = await client.create(input="Plan a Python function to find prime numbers", reasoning_effort="medium")

        # Second turn with preserved reasoning context
        response2 = await client.create(
            input="Now implement that plan with error handling",
            previous_response_id=response1.response_id,  # CoT context preserved
            tools=[code_tool],
            reasoning_effort="low",  # Can use lower effort due to preserved context
        )

    Using with custom tools and grammar constraints::

        from autogen_core.tools import BaseCustomTool, CustomToolFormat

        sql_grammar = CustomToolFormat(
            type="grammar",
            syntax="lark",
            definition='''
                start: select_statement
                select_statement: "SELECT" column_list "FROM" table_name
                column_list: column ("," column)*
                column: IDENTIFIER
                table_name: IDENTIFIER
                IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
            ''',
        )


        class SQLTool(BaseCustomTool[str]):
            def __init__(self):
                super().__init__(
                    return_type=str,
                    name="sql_query",
                    description="Execute SQL queries with grammar validation",
                    format=sql_grammar,
                )

            async def run(self, input_text: str, cancellation_token) -> str:
                return f"SQL Result: {input_text}"


        sql_tool = SQLTool()

        response = await client.create(
            input="Find all users in the database", tools=[sql_tool], reasoning_effort="medium", verbosity="low", preambles=True
        )
"""

import asyncio
import logging
import os
from asyncio import Task
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

from autogen_core import EVENT_LOGGER_NAME, CancellationToken, FunctionCall
from autogen_core.logging import LLMCallEvent
from autogen_core.models import (
    CreateResult,
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import CustomTool, CustomToolSchema, Tool, ToolSchema
from openai import NOT_GIVEN, AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat.chat_completion_message_custom_tool_call import ChatCompletionMessageCustomToolCall
from openai.types.chat.chat_completion_message_function_tool_call import ChatCompletionMessageFunctionToolCall
from openai.types.responses.response_create_params import ToolParam as ResponsesToolParam
from typing import cast as _cast  # alias to avoid shadowing

# Import concrete tool call classes for strict typing
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from typing_extensions import Unpack

from .._utils.normalize_stop_reason import normalize_stop_reason
from . import _model_info
from ._openai_client import (
    azure_openai_client_from_config as _azure_openai_client_from_config,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from ._openai_client import (
    convert_tools,
    normalize_name,
)

# Backward-compatible private aliases for tests that patch private symbols
from ._openai_client import (
    openai_client_from_config as _openai_client_from_config,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from .config import (
    AzureOpenAIClientConfiguration,
    OpenAIClientConfiguration,
)

logger = logging.getLogger(EVENT_LOGGER_NAME)


def _add_usage(usage1: RequestUsage, usage2: RequestUsage) -> RequestUsage:
    return RequestUsage(
        prompt_tokens=usage1.prompt_tokens + usage2.prompt_tokens,
        completion_tokens=usage1.completion_tokens + usage2.completion_tokens,
    )


# Responses API specific parameters
responses_api_kwargs = {
    "input",
    "reasoning",
    "text",
    "tools",
    "tool_choice",
    "allowed_tools",
    "previous_response_id",
    "reasoning_items",
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "max_tokens",
    "stop",
    "seed",
    "timeout",
    "preambles",
}

# Parameters specific to reasoning control
reasoning_kwargs = {"effort"}
text_kwargs = {"verbosity"}


class ResponsesAPICreateParams:
    """Parameters for OpenAI Responses API create method."""

    # Explicit attribute types for static type checkers
    input: str
    tools: List[ResponsesToolParam]
    create_args: Dict[str, Any]

    def __init__(
        self,
        input: str,
        tools: List[ResponsesToolParam],
        create_args: Dict[str, Any],
    ):
        self.input = input
        self.tools = tools
        self.create_args = create_args


class BaseOpenAIResponsesAPIClient:
    """Base client for OpenAI Responses API optimized for GPT-5 reasoning models.

    The Responses API is specifically designed for GPT-5 and provides:
    - Chain-of-thought (CoT) preservation between conversation turns
    - Reduced reasoning token generation through context reuse
    - Improved cache hit rates and lower latency
    - Enhanced support for GPT-5 specific features like preambles

    This client is optimized for multi-turn conversations where reasoning context
    should be preserved, resulting in better performance and lower costs compared
    to the Chat Completions API for reasoning-heavy interactions.
    """

    def __init__(
        self,
        client: Union[AsyncOpenAI, AsyncAzureOpenAI],
        *,
        create_args: Dict[str, Any],
        model_info: Optional[ModelInfo] = None,
    ):
        self._client = client
        if model_info is None:
            try:
                self._model_info = _model_info.get_info(create_args["model"])
            except KeyError as err:
                raise ValueError("model_info is required when model name is not a valid OpenAI model") from err
        else:
            self._model_info = model_info

        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    def info(self) -> ModelInfo:
        """Return a normalized view of the resolved model info.

        Exposes a read-only view for tests and diagnostics, normalizing the
        family field to an enum-style string expected by some tests.
        """
        info_copy = dict(self._model_info)
        family = info_copy.get("family")
        if isinstance(family, str):
            info_copy["family"] = family.upper().replace("-", "_")
        return info_copy  # type: ignore[return-value]

    def _process_create_args(
        self,
        input: str,
        tools: Sequence[Tool | ToolSchema | CustomTool | CustomToolSchema],
        tool_choice: Tool | CustomTool | Literal["auto", "required", "none"],
        extra_create_args: Mapping[str, Any],
        reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]] = None,
        verbosity: Optional[Literal["low", "medium", "high"]] = None,
        allowed_tools: Optional[Sequence[Tool | CustomTool | str]] = None,
        preambles: Optional[bool] = None,
        previous_response_id: Optional[str] = None,
        reasoning_items: Optional[List[Dict[str, Any]]] = None,
    ) -> ResponsesAPICreateParams:
        # Validate extra args are responses API compatible
        extra_create_args_keys = set(extra_create_args.keys())
        if not responses_api_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(
                f"Extra create args are invalid for Responses API: {extra_create_args_keys - responses_api_kwargs}"
            )

        # Copy base args and add extras
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        # Add input - required for Responses API
        create_args["input"] = input

        # Add GPT-5 specific parameters with proper structure
        if reasoning_effort is not None:
            create_args["reasoning"] = {"effort": reasoning_effort}
        elif "reasoning" not in create_args:
            # Default reasoning for GPT-5
            create_args["reasoning"] = {"effort": "medium"}

        if verbosity is not None:
            create_args["text"] = {"verbosity": verbosity}

        if preambles is not None:
            create_args["preambles"] = preambles

        # Chain-of-thought preservation
        if previous_response_id is not None:
            create_args["previous_response_id"] = previous_response_id

        if reasoning_items is not None:
            create_args["reasoning_items"] = reasoning_items

        # Validate model supports function calling if tools provided
        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        # Convert tools to OpenAI Responses API format
        converted_tools: List[Dict[str, Any]] = []

        for tool in tools:
            if isinstance(tool, CustomTool) or (isinstance(tool, dict) and "format" in tool):
                # GPT-5 Custom tool for Responses API
                custom_schema = cast(Dict[str, Any], getattr(tool, "schema", tool))  # type: ignore[arg-type]
                custom_param: Dict[str, Any] = {
                    "type": "custom",
                    "name": custom_schema["name"],
                    "description": custom_schema.get("description", ""),
                }
                if "format" in custom_schema:
                    fmt = custom_schema["format"]
                    if isinstance(fmt, dict) and fmt.get("type") == "grammar":
                        syntax = fmt.get("syntax")
                        definition = fmt.get("definition")
                        if syntax and definition:
                            custom_param["format"] = {"type": "grammar", "syntax": syntax, "definition": definition}
                    else:
                        custom_param["format"] = fmt
                converted_tools.append(custom_param)
            else:
                # Standard function tool
                tool_schema: Dict[str, Any]
                if isinstance(tool, Tool):
                    tool_schema = tool.schema
                else:
                    tool_schema = cast(Dict[str, Any], tool)

                converted_tools.append(
                    {
                        "type": "function",
                        "name": tool_schema["name"],
                        "description": tool_schema.get("description", ""),
                        "parameters": tool_schema.get("parameters", {}),
                        "strict": tool_schema.get("strict", False),
                    }
                )

        # Process tool choice
        if isinstance(tool_choice, (Tool, CustomTool)):
            if len(tools) == 0:
                raise ValueError("tool_choice specified but no tools provided")

            # Validate tool exists
            tool_names_available: List[str] = []
            for tool in tools:
                if isinstance(tool, (Tool, CustomTool)):
                    tool_names_available.append(tool.schema["name"])
                else:
                    tool_names_available.append(tool["name"])

            tool_name = tool_choice.schema["name"]
            if tool_name not in tool_names_available:
                raise ValueError(f"tool_choice references '{tool_name}' but it's not in provided tools")

        # Add tools and tool_choice to args
        if len(converted_tools) > 0:
            from ._openai_client import convert_tool_choice

            create_args["tool_choice"] = convert_tool_choice(tool_choice)

            # Handle allowed_tools for GPT-5
            if allowed_tools is not None:
                allowed_tool_names: List[str] = []
                for allowed_tool in allowed_tools:
                    if isinstance(allowed_tool, str):
                        allowed_tool_names.append(allowed_tool)
                    elif isinstance(allowed_tool, (Tool, CustomTool)):
                        allowed_tool_names.append(allowed_tool.schema["name"])

                # Build allowed tools structure for Responses API
                if isinstance(tool_choice, str) and tool_choice in ["auto", "required"]:
                    allowed_tools_param: Dict[str, Any] = {"type": "allowed_tools", "mode": tool_choice, "tools": []}

                    for tool_param in converted_tools:
                        tool_dict = cast(Dict[str, Any], tool_param)
                        tool_type = tool_dict.get("type")
                        tool_name = cast(str, tool_dict.get("name", ""))
                        if tool_type in {"function", "custom"} and tool_name in allowed_tool_names:
                            allowed_tools_param["tools"].append({"type": tool_type, "name": tool_name})

                    create_args["tool_choice"] = allowed_tools_param

        # Cast converted tools to the precise ToolParam union type for typing only
        return ResponsesAPICreateParams(
            input=input,
            tools=_cast(List[ResponsesToolParam], converted_tools),
            create_args=create_args,
        )

    async def create(
        self,
        input: str,
        *,
        tools: Sequence[Tool | ToolSchema | CustomTool | CustomToolSchema] = [],
        tool_choice: Tool | CustomTool | Literal["auto", "required", "none"] = "auto",
        allowed_tools: Optional[Sequence[Tool | CustomTool | str]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]] = None,
        verbosity: Optional[Literal["low", "medium", "high"]] = None,
        preambles: Optional[bool] = None,
        previous_response_id: Optional[str] = None,
        reasoning_items: Optional[List[Dict[str, Any]]] = None,
    ) -> CreateResult:
        """Create a response using OpenAI Responses API optimized for GPT-5.

        The Responses API provides better performance for multi-turn reasoning conversations
        by preserving chain-of-thought context between turns, reducing token usage and latency.

        Args:
            input: The input text/message for the model
            tools: Standard function tools and/or GPT-5 custom tools
            tool_choice: Tool selection strategy or specific tool to use
            allowed_tools: Restrict model to subset of available tools
            extra_create_args: Additional Responses API parameters
            cancellation_token: Token to cancel the operation
            reasoning_effort: GPT-5 reasoning depth (minimal/low/medium/high)
            verbosity: GPT-5 output length control (low/medium/high)
            preambles: Enable explanatory text before tool calls
            previous_response_id: ID of previous response to preserve CoT context
            reasoning_items: Explicit reasoning items to include in context

        Returns:
            CreateResult with response content, reasoning, and usage information

        Examples:
            Basic usage with reasoning control::

                client = OpenAIResponsesAPIClient(model="gpt-5")

                response = await client.create(
                    input="Explain quantum computing to a 10-year-old",
                    reasoning_effort="medium",
                    verbosity="high",
                    preambles=True,
                )

            Multi-turn with CoT preservation::

                # First turn - reasoning is generated and cached
                response1 = await client.create(input="What are the pros and cons of solar energy?", reasoning_effort="high")

                # Second turn - reuses cached reasoning context
                response2 = await client.create(
                    input="How does this compare to wind energy?",
                    previous_response_id=response1.response_id,
                    reasoning_effort="low",  # Less reasoning needed due to context
                )

            Using with custom tools::

                from autogen_core.tools import CodeExecutorTool

                code_tool = CodeExecutorTool()

                response = await client.create(
                    input="Calculate the factorial of 15 using Python",
                    tools=[code_tool],
                    reasoning_effort="minimal",
                    preambles=True,  # Explain tool usage
                )
        """
        create_params = self._process_create_args(
            input,
            tools,
            tool_choice,
            extra_create_args,
            reasoning_effort,
            verbosity,
            allowed_tools,
            preambles,
            previous_response_id,
            reasoning_items,
        )

        # Call OpenAI Responses API endpoint
        future: Task[Dict[str, Any]] = asyncio.ensure_future(
            cast(
                Task[Dict[str, Any]],
                self._client.responses.create(  # type: ignore
                    **create_params.create_args,
                    tools=cast(Any, create_params.tools) if len(create_params.tools) > 0 else NOT_GIVEN,
                ),
            )
        )

        if cancellation_token is not None:
            cancellation_token.link_future(future)

        from openai.types.responses.response import Response as SDKResponse
        from openai.types.responses.response_output_message import ResponseOutputMessage
        from openai.types.responses.response_output_text import ResponseOutputText
        from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
        from openai.types.responses.response_custom_tool_call import ResponseCustomToolCall

        sdk_response = cast(SDKResponse, await future)

        # Handle usage information (Responses API uses input/output tokens)
        usage = RequestUsage(
            prompt_tokens=int(getattr(sdk_response.usage, "input_tokens", 0) or 0),
            completion_tokens=int(getattr(sdk_response.usage, "output_tokens", 0) or 0),
        )

        # Log the call
        logger.info(
            LLMCallEvent(
                messages=[{"role": "user", "content": input}],
                response=sdk_response.to_dict(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                tools=create_params.tools,
            )
        )

        # Parse Responses API output
        tool_calls_fc: List[FunctionCall] = []
        thought: Optional[str] = None
        text_parts: List[str] = []
        for item in sdk_response.output or []:
            if isinstance(item, ResponseFunctionToolCall):
                tool_calls_fc.append(
                    FunctionCall(id=item.id or "", arguments=item.arguments or "", name=normalize_name(item.name))
                )
            elif isinstance(item, ResponseCustomToolCall):
                tool_calls_fc.append(
                    FunctionCall(id=item.id or "", arguments=item.input or "", name=normalize_name(item.name))
                )
            elif isinstance(item, ResponseOutputMessage):
                for c in item.content or []:
                    if isinstance(c, ResponseOutputText):
                        text_parts.append(c.text)

        # Reasoning items
        if sdk_response.reasoning is not None:
            try:
                # Newer SDKs may expose summary text
                summary_texts = getattr(sdk_response.reasoning, "summary", None)
                if summary_texts:
                    thought = "\n".join([getattr(s, "text", "") for s in summary_texts])
            except Exception:
                thought = None

        if tool_calls_fc:
            create_result = CreateResult(
                finish_reason=normalize_stop_reason("tool_calls"),
                content=tool_calls_fc,
                usage=usage,
                cached=False,
                thought=thought,
            )
        else:
            create_result = CreateResult(
                finish_reason=normalize_stop_reason("stop"),
                content="".join(text_parts),
                usage=usage,
                cached=False,
                thought=thought,
            )

        # The CreateResult type does not currently expose a response_id field
        # We can add it in the future if the core model supports it.

        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        return create_result

    async def close(self) -> None:
        """Close the underlying client."""
        await self._client.close()

    def actual_usage(self) -> RequestUsage:
        """Get actual token usage."""
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        """Get total token usage."""
        return self._total_usage

    @property
    def model_info(self) -> ModelInfo:
        """Get model information and capabilities."""
        return self._model_info


class OpenAIResponsesAPIClient(BaseOpenAIResponsesAPIClient):
    """OpenAI Responses API client for GPT-5 optimized interactions.

    This client uses the OpenAI Responses API which is specifically designed for
    GPT-5 reasoning models and provides significant performance improvements over
    the Chat Completions API for multi-turn conversations.

    Key benefits of the Responses API:
    - Chain-of-thought preservation reduces reasoning token generation
    - Higher cache hit rates improve response latency
    - Better integration with GPT-5 specific features like preambles
    - Optimized for reasoning-heavy multi-turn conversations

    Examples:
        Basic client setup::

            from autogen_ext.models.openai import OpenAIResponsesAPIClient

            client = OpenAIResponsesAPIClient(
                model="gpt-5",
                api_key="sk-...",  # Optional if OPENAI_API_KEY env var set
            )

        Single turn with reasoning control::

            response = await client.create(
                input="Solve this differential equation: dy/dx = 2x + 3", reasoning_effort="high", verbosity="medium"
            )

            print(f"Reasoning: {response.thought}")
            print(f"Solution: {response.content}")

        Multi-turn conversation with CoT preservation::

            # Turn 1: Initial problem solving with high reasoning
            response1 = await client.create(
                input="Design an algorithm to find the shortest path in a graph", reasoning_effort="high"
            )

            # Turn 2: Follow up uses cached reasoning context
            response2 = await client.create(
                input="How would you optimize this for very large graphs?",
                previous_response_id=response1.response_id,
                reasoning_effort="medium",  # Can use lower effort due to context
            )

            # Turn 3: Implementation request with tool usage
            response3 = await client.create(
                input="Implement the optimized version in Python",
                previous_response_id=response2.response_id,
                tools=[code_tool],
                reasoning_effort="low",  # Minimal reasoning needed
                preambles=True,  # Explain why code tool is being used
            )

        Configuration loading::

            from autogen_core.models import ChatCompletionClient

            config = {
                "provider": "OpenAIResponsesAPIClient",
                "config": {
                    "model": "gpt-5",
                    "api_key": "sk-...",
                    "reasoning": {"effort": "medium"},
                    "text": {"verbosity": "medium"},
                    "preambles": True,
                },
            }

            client = ChatCompletionClient.load_component(config)
    """

    def __init__(self, **kwargs: Unpack[OpenAIClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for OpenAIResponsesAPIClient")

        # Extract client configuration
        from ._openai_client import create_args_from_config, openai_client_from_config

        copied_args = dict(kwargs).copy()
        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        # Handle special model routing
        assert "model" in copied_args and isinstance(copied_args["model"], str)
        if copied_args["model"].startswith("gemini-"):
            if "base_url" not in copied_args:
                copied_args["base_url"] = _model_info.GEMINI_OPENAI_BASE_URL
            if "api_key" not in copied_args and "GEMINI_API_KEY" in os.environ:
                copied_args["api_key"] = os.environ["GEMINI_API_KEY"]

        client = openai_client_from_config(copied_args)
        create_args = create_args_from_config(copied_args)

        super().__init__(
            client=client,
            create_args=create_args,
            model_info=model_info,
        )

    # NOTE: This private alias is used by tests for static type checking (Pyright/MyPy)
    # to access a name-mangled method on this concrete class. It forwards to the
    # protected method on the base class and returns a precisely typed result.
    def _OpenAIResponsesAPIClient__process_create_args(  # type: ignore[unused-private-name]
        self,
        *,
        input: str,
        tools: Sequence[Tool | ToolSchema | CustomTool | CustomToolSchema],
        tool_choice: Tool | CustomTool | Literal["auto", "required", "none"],
        extra_create_args: Mapping[str, Any],
        reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]] | None = None,
        verbosity: Optional[Literal["low", "medium", "high"]] | None = None,
        allowed_tools: Optional[Sequence[Tool | CustomTool | str]] | None = None,
        preambles: Optional[bool] | None = None,
        previous_response_id: Optional[str] | None = None,
        reasoning_items: Optional[List[Dict[str, Any]]] | None = None,
    ) -> ResponsesAPICreateParams:
        return super()._process_create_args(
            input=input,
            tools=tools,
            tool_choice=tool_choice,
            extra_create_args=extra_create_args,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
            allowed_tools=allowed_tools,
            preambles=preambles,
            previous_response_id=previous_response_id,
            reasoning_items=reasoning_items,
        )


class AzureOpenAIResponsesAPIClient(BaseOpenAIResponsesAPIClient):
    """Azure OpenAI Responses API client for GPT-5 optimized interactions.

    Similar to OpenAIResponsesAPIClient but configured for Azure OpenAI service.
    Provides the same GPT-5 optimizations and Responses API benefits through
    Azure's OpenAI implementation.

    Examples:
        Basic Azure setup::

            from autogen_ext.models.openai import AzureOpenAIResponsesAPIClient

            client = AzureOpenAIResponsesAPIClient(
                model="gpt-5",
                azure_endpoint="https://your-resource.openai.azure.com/",
                azure_deployment="your-gpt5-deployment",
                api_version="2024-06-01",
                api_key="your-azure-key",
            )

        With Azure AD authentication::

            from autogen_ext.auth.azure import AzureTokenProvider
            from azure.identity import DefaultAzureCredential

            token_provider = AzureTokenProvider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

            client = AzureOpenAIResponsesAPIClient(
                model="gpt-5",
                azure_endpoint="https://your-resource.openai.azure.com/",
                azure_deployment="your-gpt5-deployment",
                api_version="2024-06-01",
                azure_ad_token_provider=token_provider,
            )
    """

    def __init__(self, **kwargs: Unpack[AzureOpenAIClientConfiguration]):
        # Extract configuration
        from ._openai_client import azure_openai_client_from_config, create_args_from_config

        copied_args = dict(kwargs).copy()
        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        client = azure_openai_client_from_config(copied_args)
        create_args = create_args_from_config(copied_args)

        super().__init__(
            client=client,
            create_args=create_args,
            model_info=model_info,
        )
