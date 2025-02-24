"""Base Gemini client implementation using google.genai."""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
)

from autogen_core import CancellationToken, Image
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from google import genai

from . import _model_info
from .adapter import convert_tools, prepare_genai_contents
from .utils import (
    extract_tool_calls,
    get_response_text,
    get_response_usage,
    handle_structured_output,
    map_finish_reason,
    prepare_config,
)


class GeminiCallWrapper:
    """
    Wrapper for Gemini API calls with enhanced capabilities.

    This wrapper provides direct access to Google's Gemini models with support for:
    - Streaming responses
    - Vision/multimodal inputs
    - Function/tool calling
    - Structured output (JSON, Pydantic)
    - Token management

    References:
        - https://ai.google.dev/gemini-api/docs
        - https://github.com/googleapis/python-genai
    """

    def __init__(
        self,
        model: str,
        create_args: Dict[str, Any],
        model_info: Optional[ModelInfo] = None,
        client: Optional[genai.Client] = None,
    ):
        self._model = model
        self._create_args = create_args
        self._client = client

        # Context caching for long-running conversations
        self._context_cache: Dict[str, Any] = {
            "contents": [],
            "system_instruction": None,
            "ttl": None,
        }

        # Resolve model metadata
        if model_info is None:
            try:
                self._model_info = _model_info.get_info(model)
            except KeyError as err:
                raise ValueError(
                    "model_info is required when model name is not known"
                ) from err
        else:
            self._model_info = model_info

        # Initialize usage tracking
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    def _ensure_client(self) -> genai.Client:
        """Ensure the google.genai client is initialized."""
        if not self._client:
            raise RuntimeError("Client not initialized")
        return self._client

    def set_client(self, client: genai.Client) -> None:
        """Set the google.genai client instance."""
        self._client = client

    def _prepare_genai_contents(
        self, contents: Union[str, LLMMessage, Sequence[Union[str, Image, LLMMessage]]]
    ) -> List[Any]:
        """
        Convert the given contents in various forms into a list of Gemini API Content objects.
        Uses the adapter function 'prepare_genai_contents' which expects a sequence of LLMMessage.
        For raw string or Image inputs, a UserMessage is created.
        """
        from autogen_core.models import (
            LLMMessage,
        )

        if isinstance(contents, (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage, LLMMessage)):
            return prepare_genai_contents([contents])
        elif isinstance(contents, (str, Image)):
            return prepare_genai_contents([UserMessage(content=contents)])
        elif isinstance(contents, (list, tuple)):
            if contents and isinstance(contents[0], (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage, LLMMessage)):
                return prepare_genai_contents(list(contents))
            else:
                messages = []
                for item in contents:
                    if isinstance(item, (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage, LLMMessage)):
                        messages.append(item)
                    else:
                        messages.append(UserMessage(content=item))
                return prepare_genai_contents(messages)
        else:
            raise ValueError("Unsupported contents type")

    async def generate_content(
        self,
        contents: Union[str, Sequence[Union[str, Image]], LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
        json_output: Optional[bool] = None,
        structured_output: Optional[Dict[str, Any]] = None,
        extra_create_args: Dict[str, Any] = {},
        use_cached_context: bool = False,
        config: Optional[
            Union[genai.types.GenerateContentConfig, Dict[str, Any]]
        ] = None,
    ) -> CreateResult:
        """Generate content using the Gemini model."""
        client = self._ensure_client()

        # Convert the input into Gemini-compatible contents
        genai_contents = self._prepare_genai_contents(contents)

        # Use cached context if requested
        if use_cached_context and self._context_cache.get("contents"):
            genai_contents = self._context_cache["contents"] + genai_contents

        genai_tools = convert_tools(tools) if tools else None

        response_format = None
        if json_output or structured_output:
            response_format = {
                "type": (
                    structured_output.get("type", "json_object")
                    if structured_output
                    else "json_object"
                ),
                "schema": (
                    structured_output.get("schema") if structured_output else None
                ),
            }

        if response_format:
            output_type = response_format["type"]
            if output_type == "json_object":
                genai_contents.append("Please provide your response in valid JSON format.")
            elif output_type == "pydantic":
                schema = response_format.get("schema")
                if schema and hasattr(schema, "model_json_schema"):
                    schema_dict = schema.model_json_schema()
                    genai_contents.append(
                        f"Please provide your response as a JSON object that matches this schema: {schema_dict}"
                    )

        generation_config = prepare_config(
            config=config,
            create_args=self._create_args,
            extra_create_args=extra_create_args,
            tools=genai_tools,
            response_format=response_format,
        )

        try:
            response = await client.aio.models.generate_content(
                model=self._model, contents=genai_contents, config=generation_config
            )

            tool_calls = extract_tool_calls(response)
            text = get_response_text(response)
            content = handle_structured_output(text, response_format) if response_format else text
            if tool_calls:
                content = tool_calls

            usage = get_response_usage(response)

            finish_reason: Literal[
                "stop", "length", "function_calls", "content_filter", "unknown"
            ] = "unknown"
            if response.candidates:
                finish_reason_attr = getattr(response.candidates[0], "finish_reason", None)
                if finish_reason_attr:
                    finish_reason = map_finish_reason(finish_reason_attr)
                elif not tool_calls:
                    finish_reason = "stop"
                else:
                    finish_reason = "function_calls"

            result = CreateResult(
                content=content,
                finish_reason=finish_reason,
                usage=usage,
                cached=use_cached_context and bool(self._context_cache.get("contents")),
            )

            self._total_usage = RequestUsage(
                prompt_tokens=self._total_usage.prompt_tokens + usage.prompt_tokens,
                completion_tokens=self._total_usage.completion_tokens + usage.completion_tokens,
            )
            self._actual_usage = usage

            return result

        except Exception:
            raise

    async def generate_content_stream(
        self,
        contents: Union[str, Sequence[Union[str, Image]], LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Dict[str, Any] = {},
        use_cached_context: bool = False,
        config: Optional[
            Union[genai.types.GenerateContentConfig, Dict[str, Any]]
        ] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Generate streaming content using the Gemini model."""
        client = self._ensure_client()

        # Convert the input to Gemini-compatible contents
        genai_contents = self._prepare_genai_contents(contents)

        if use_cached_context and self._context_cache.get("contents"):
            genai_contents = self._context_cache["contents"] + genai_contents

        genai_tools = convert_tools(tools) if tools else None

        generation_config = prepare_config(
            config=config,
            create_args=self._create_args,
            extra_create_args=extra_create_args,
            tools=genai_tools,
        )

        try:
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=genai_contents,
                config=generation_config,
            )

            if response.text:
                chunk_size = 100  # characters
                text = response.text
                for i in range(0, len(text), chunk_size):
                    if cancellation_token and cancellation_token.is_cancelled():
                        break
                    yield text[i : i + chunk_size]

            usage = get_response_usage(response)

            self._total_usage = RequestUsage(
                prompt_tokens=self._total_usage.prompt_tokens + usage.prompt_tokens,
                completion_tokens=self._total_usage.completion_tokens + usage.completion_tokens,
            )
            self._actual_usage = usage

        except Exception:
            raise

    def count_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
    ) -> int:
        """Count tokens for the given messages and tools."""
        client = self._ensure_client()

        try:
            contents = prepare_genai_contents(messages)
            combined_text = "\n".join(str(content) for content in contents)
            message_tokens = client.models.count_tokens(
                model=self._model, contents=combined_text
            ).total_tokens
            tool_tokens = 0
            if tools:
                tool_text = str(convert_tools(tools))
                tool_tokens = client.models.count_tokens(
                    model=self._model, contents=tool_text
                ).total_tokens
            return message_tokens + tool_tokens

        except Exception:
            total_text = "\n".join(str(msg.content) for msg in messages)
            if tools:
                total_text += "\n" + str(tools)
            return len(total_text) // 4

    def remaining_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
    ) -> int:
        """Calculate remaining tokens based on model's token limit."""
        token_limit = _model_info.get_token_limit(self._model)
        used_tokens = self.count_tokens(messages, tools=tools)
        return max(0, token_limit - used_tokens)

    @property
    def model_info(self) -> ModelInfo:
        """Return the model information."""
        return self._model_info

    def actual_usage(self) -> RequestUsage:
        """Return the actual usage for the last request."""
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        """Return the total usage across all requests."""
        return self._total_usage
