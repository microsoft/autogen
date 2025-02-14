import asyncio
import base64
import copy
import inspect
import json
import logging
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Coroutine,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

from autogen_core import (
    EVENT_LOGGER_NAME,
    TRACE_LOGGER_NAME,
    CancellationToken,
    Component,
    FunctionCall,
    Image,
    MessageHandlerContext,
)
from autogen_core.logging import LLMCallEvent
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from google.genai import types as gemini_types
from google.genai.client import Client as GenaiClient

from . import _model_info
from .config import GeminiClientConfigurationConfigModel

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

# Extract valid kwargs for Gemini client initialization and content generation
gemini_client_kwargs = set(inspect.getfullargspec(GenaiClient.__init__).kwonlyargs)
gemini_create_kwargs = set(gemini_types.GenerateContentConfig.__annotations__.keys())

# Mapping of Gemini finish reasons to Autogen finish reasons
GEMINI_TO_AUTOGEN_FINISH_REASON: Dict[str, FinishReasons] = {
    gemini_types.FinishReason.FINISH_REASON_UNSPECIFIED: "unknown",
    gemini_types.FinishReason.STOP: "stop",
    gemini_types.FinishReason.MAX_TOKENS: "length",
    gemini_types.FinishReason.SAFETY: "content_filter",
    gemini_types.FinishReason.BLOCKLIST: "content_filter",
    gemini_types.FinishReason.PROHIBITED_CONTENT: "content_filter",
    gemini_types.FinishReason.SPII: "content_filter",
    gemini_types.FinishReason.RECITATION: "unknown",
    gemini_types.FinishReason.OTHER: "unknown",
    gemini_types.FinishReason.MALFORMED_FUNCTION_CALL: "function_calls",
}


def _add_usage(usage1: RequestUsage, usage2: RequestUsage) -> RequestUsage:
    """Combine two RequestUsage objects by adding their token counts."""
    return RequestUsage(
        prompt_tokens=usage1.prompt_tokens + usage2.prompt_tokens,
        completion_tokens=usage1.completion_tokens + usage2.completion_tokens,
    )


def _try_parse_json(s: str) -> Any:
    """Attempt to parse a string as JSON, return original string if parsing fails."""
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


def _system_instruction_from_messages(messages: List[LLMMessage]) -> str:
    """Extract system messages from a list of messages and combine them into a single instruction."""
    system_texts: List[str] = []
    remain: List[LLMMessage] = []
    for m in messages:
        if isinstance(m, SystemMessage):
            system_texts.append(m.content.strip())
        else:
            remain.append(m)
    messages[:] = remain  # modify in-place
    if not system_texts:
        return ""
    return "\n".join(system_texts)


def ag_messages_to_gemini(
    messages: Sequence[LLMMessage],
) -> List[gemini_types.Content]:
    """Convert Autogen LLMMessages to Gemini's Content objects."""
    contents: List[gemini_types.Content] = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            if isinstance(msg.content, str):
                parts: List[gemini_types.Part] = [gemini_types.Part(text=msg.content)]
            else:
                parts: List[gemini_types.Part] = []
                for c in msg.content:
                    if isinstance(c, str):
                        parts.append(gemini_types.Part(text=c))
                    elif isinstance(c, Image):
                        # Convert autogen Image to Gemini's image format
                        base64_png = c.to_base64()
                        raw_bytes = base64.b64decode(base64_png)
                        parts.append(gemini_types.Part.from_bytes(data=raw_bytes, mime_type="image/png"))
                    else:
                        trace_logger.warning(f"Unsupported content type: {type(c)}")
                        parts.append(gemini_types.Part(text="[unsupported content]"))

            content = gemini_types.Content(role="user", parts=parts)
            contents.append(content)

        elif isinstance(msg, AssistantMessage):
            if isinstance(msg.content, list):
                # Convert function calls to Gemini
                fc_parts: List[gemini_types.Part] = []
                for fc in msg.content:
                    fc_parts.append(
                        gemini_types.Part(
                            function_call=gemini_types.FunctionCall(
                                name=fc.name,
                                args=_try_parse_json(fc.arguments),
                            )
                        )
                    )
                content = gemini_types.Content(role="model", parts=fc_parts)
            else:
                content = gemini_types.Content(
                    role="model",
                    parts=[gemini_types.Part(text=msg.content)],
                )
            contents.append(content)

        elif isinstance(msg, FunctionExecutionResultMessage):
            exec_parts: List[gemini_types.Part] = []
            for item in msg.content:
                parsed_value = _try_parse_json(item.content)
                f_response = gemini_types.FunctionResponse(
                    id=item.call_id,
                    name="function",  # TODO: Ag's FunctionExecutionResult doesn't have name field
                    response={"result": parsed_value},
                )
                exec_parts.append(gemini_types.Part(function_response=f_response))

            content = gemini_types.Content(role="user", parts=exec_parts)
            contents.append(content)

    return contents


def _gemini_finish_reason_to_autogen(
    reason: gemini_types.FinishReason | None,
) -> FinishReasons:
    """Convert Gemini's FinishReason to Autogen's FinishReasons enum."""
    if reason is None:
        return "unknown"
    return GEMINI_TO_AUTOGEN_FINISH_REASON.get(reason, "unknown")


def _parse_gemini_response(
    response: gemini_types.GenerateContentResponse,
) -> CreateResult:
    """Parse Gemini's response into Autogen's CreateResult format."""
    # Handle potentially None values for token counts
    prompt_tokens = 0
    completion_tokens = 0
    if response.usage_metadata:
        prompt_tokens = response.usage_metadata.prompt_token_count or 0
        completion_tokens = response.usage_metadata.candidates_token_count or 0

    usage = RequestUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    if not response.candidates:
        return CreateResult(
            finish_reason="unknown",
            content="",
            usage=usage,
            cached=False,
        )

    candidate = response.candidates[0]
    contents: List[str] = []
    thoughts: List[str] = []
    fcalls: List[FunctionCall] = []

    if candidate.content and candidate.content.parts:
        for p in candidate.content.parts:
            if p.function_call:
                fcalls.append(
                    FunctionCall(
                        id=p.function_call.id or "",
                        name=p.function_call.name or "",
                        arguments=json.dumps(p.function_call.args or {}),
                    )
                )
            if p.text:
                if p.thought:
                    thoughts.append(p.text)
                else:
                    contents.append(p.text)

    finish_reason = _gemini_finish_reason_to_autogen(candidate.finish_reason)
    if fcalls:
        # Override finish reason if function calls are present
        finish_reason = "function_calls"
        content = fcalls
    else:
        content = "\n".join(contents)

    thought = "\n".join(thoughts) if thoughts else None

    return CreateResult(
        finish_reason=finish_reason,
        content=content,
        usage=usage,
        cached=False,
        logprobs=None,  # Gemini doesn't provide token logprobs (for now)
        thought=thought,
    )


def _strip_unwanted_fields(d: Dict[str, Any]) -> None:
    """Remove keys that would throw an error in Gemini's FunctionDeclaration."""
    # Remove keys that would throw an error in Gemini's FunctionDeclaration
    for key in ["title", "examples"]:
        if key in d:
            del d[key]

    for v in d.values():
        if isinstance(v, dict):
            _strip_unwanted_fields(cast(Dict[str, Any], v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    _strip_unwanted_fields(cast(Dict[str, Any], item))


def convert_tools_to_gemini(
    tools: Sequence[Tool | ToolSchema],
) -> List[gemini_types.Tool]:
    """Convert Autogen tools to Gemini's tool format."""
    gemini_tools: List[gemini_types.Tool] = []

    for tool in tools:
        if isinstance(tool, Tool):
            schema = tool.schema
        else:
            schema = tool  # It's already a dict

        tool_name = schema.get("name")
        tool_desc = schema.get("description")
        parameters_dict = schema.get("parameters")

        # Convert to a plain dict so we can safely call _strip_unwanted_fields
        if parameters_dict:
            params_copy: Dict[str, Any] | None = dict(parameters_dict)
            _strip_unwanted_fields(params_copy)
        else:
            params_copy = None

        # Create a gemini FunctionDeclaration
        decl = gemini_types.FunctionDeclaration(
            name=tool_name,
            description=tool_desc,
            parameters=params_copy,
            response=None,
        )

        gemini_tools.append(gemini_types.Tool(function_declarations=[decl]))

    return gemini_tools


def _client_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Create a dictionary of arguments for the Client from a configuration."""
    return {k: v for k, v in config.items() if k in gemini_client_kwargs}


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Create a dictionary of arguments for the GenerateContentConfig from a configuration."""
    return {k: v for k, v in config.items() if k in gemini_create_kwargs}


class GeminiChatCompletionClient(ChatCompletionClient, Component[GeminiClientConfigurationConfigModel]):
    """Chat completion client for Google's Gemini models.

    Args:
        model (str): Which Gemini model to use (e.g. "gemini-pro", "gemini-pro-vision")
        api_key (optional, str): The API key to use. Required if 'GOOGLE_API_KEY' is not found in environment variables.
        vertexai (optional, bool): Whether to use Vertex AI (Google Cloud) instead of the consumer API.
        project (optional, str): Google Cloud project ID. Required if using Vertex AI.
        location (optional, str): Google Cloud region. Required if using Vertex AI.
        model_info (optional, ModelInfo): The capabilities of the model. Required if model name is not a known Gemini model.
        temperature (optional, float): Controls randomness in the output.
        max_tokens (optional, int): Maximum number of tokens to generate.
        top_p (optional, float): Nucleus sampling parameter.
        top_k (optional, int): Top-k sampling parameter.

    To use this client, you must install the `gemini` extension:

    .. code-block:: bash

        pip install "autogen-ext[gemini]"

    Example usage:

    .. code-block:: python

        from autogen_ext.models.gemini import GeminiChatCompletionClient
        from autogen_core.models import UserMessage

        client = GeminiChatCompletionClient(
            model="gemini-2.0-flash",
            # api_key="your-api-key",  # Optional if GOOGLE_API_KEY environment variable is set
        )

        result = await client.create([UserMessage(content="What is the capital of France?", source="user")])
        print(result.content)

    """

    component_type = "model"
    component_config_schema = GeminiClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.gemini.GeminiChatCompletionClient"

    def __init__(self, **kwargs: Any):
        # Keep a copy of raw config for serialization
        self._raw_config: Dict[str, Any] = dict(kwargs)

        if "model" not in self._raw_config:
            raise ValueError("`model` is required for GeminiChatCompletionClient")

        self._model_name = self._raw_config["model"]
        model_info: Optional[ModelInfo] = self._raw_config.pop("model_info", None)

        if model_info is None:
            try:
                self._model_info = _model_info.get_info(self._model_name)
            except KeyError as err:
                raise ValueError("model_info is required when model name is not a known Gemini model") from err
        else:
            self._model_info = model_info

        client_args = _client_args_from_config(self._raw_config)
        self._client = GenaiClient(**client_args)
        self._async_models = self._client.aio.models

        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

        # Default create args for all requests
        create_args = _create_args_from_config(self._raw_config)
        create_args["automatic_function_calling"] = gemini_types.AutomaticFunctionCallingConfig(
            disable=True,  # Autogen handles tool calling
            maximum_remote_calls=None,
        )
        self._create_args = create_args

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return cls(**config)

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """
        Create a single chat completion.

        Args:
            messages (Sequence[LLMMessage]): A sequence of messages to be processed.
            tools (Sequence[Tool | ToolSchema], optional): A sequence of tools to be used in the completion. Defaults to `[]`.
            json_output (Optional[bool], optional): If True, the output will be in JSON format. Defaults to None.
            extra_create_args (Mapping[str, Any], optional): Additional arguments for the Gemini create method.
            cancellation_token (Optional[CancellationToken], optional): A token to cancel the operation. Defaults to None.

        Returns:
            CreateResult containing the completion and metadata

        Raises:
            ValueError: If incompatible options are requested (e.g. JSON output for non-supporting model)
        """
        # Filter and merge create args
        filtered_create_args = _create_args_from_config(extra_create_args)
        create_conf = dict(self._create_args)
        create_conf.update(filtered_create_args)

        # Validate model capabilities
        if not self._model_info["vision"]:
            for msg in messages:
                if isinstance(msg, UserMessage) and isinstance(msg.content, list):
                    if any(isinstance(x, Image) for x in msg.content):
                        raise ValueError("Model does not support vision, but an Image was supplied.")

        if not self._model_info["function_calling"] and tools:
            raise ValueError("Model does not support function calling, but tools were provided.")

        if json_output is not None and json_output:
            if not self._model_info["json_output"]:
                raise ValueError("Model does not support JSON output but json_output=True was requested.")
            create_conf["response_mime_type"] = "application/json"

        # Extract system messages and convert remaining messages
        msgs_copy = list(messages)
        sys_instruct = _system_instruction_from_messages(msgs_copy)
        gemini_contents = ag_messages_to_gemini(msgs_copy)

        if sys_instruct and "system_instruction" not in create_conf:
            create_conf["system_instruction"] = sys_instruct

        if json_output:
            create_conf["response_mime_type"] = "application/json"

        # Add tools if present
        if tools:
            gemini_tools = convert_tools_to_gemini(tools)
            create_conf["tools"] = gemini_tools

        # Create generation config
        generation_config = gemini_types.GenerateContentConfig(**create_conf)

        coro: Coroutine[Any, Any, gemini_types.GenerateContentResponse]
        coro = self._async_models.generate_content(
            model=self._model_name,
            contents=gemini_contents,
            config=generation_config,
        )

        fut = asyncio.ensure_future(coro)
        if cancellation_token is not None:
            cancellation_token.link_future(fut)

        response = await fut
        result = _parse_gemini_response(response)

        try:
            agent_id = MessageHandlerContext.agent_id()
        except RuntimeError:
            agent_id = None

        logger.info(
            LLMCallEvent(
                messages={"contents": gemini_contents},
                response=response.model_dump(),
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                agent_id=agent_id,
            )
        )

        self._total_usage = _add_usage(self._total_usage, result.usage)
        self._actual_usage = _add_usage(self._actual_usage, result.usage)

        return result

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """
        Create a streaming chat completion.

        Args:
            messages (Sequence[LLMMessage]): A sequence of messages to be processed.
            tools (Sequence[Tool | ToolSchema], optional): A sequence of tools to be used in the completion. Defaults to `[]`.
            json_output (Optional[bool], optional): If True, the output will be in JSON format. Defaults to None.
            extra_create_args (Mapping[str, Any], optional): Additional arguments for the Gemini create method.
            cancellation_token (Optional[CancellationToken], optional): A token to cancel the operation. Defaults to None.

        Yields:
            String tokens as they arrive, followed by a final CreateResult

        Raises:
            ValueError: If incompatible options are requested
        """
        # Filter and merge create args
        filtered_create_args = _create_args_from_config(extra_create_args)
        create_conf = dict(self._create_args)
        create_conf.update(filtered_create_args)

        # Validate model capabilities
        if not self._model_info["vision"]:
            for msg in messages:
                if isinstance(msg, UserMessage) and isinstance(msg.content, list):
                    if any(isinstance(x, Image) for x in msg.content):
                        raise ValueError("Model does not support vision, but an Image was supplied.")

        if not self._model_info["function_calling"] and tools:
            raise ValueError("Model does not support function calling, but tools were provided.")

        if json_output and not self._model_info["json_output"]:
            raise ValueError("Model does not support JSON output but json_output=True was requested.")

        # Extract system messages and convert remaining messages
        msgs_copy = list(messages)
        sys_instruct = _system_instruction_from_messages(msgs_copy)
        gemini_contents = ag_messages_to_gemini(msgs_copy)

        if sys_instruct and "system_instruction" not in create_conf:
            create_conf["system_instruction"] = sys_instruct

        # Configure JSON output if requested
        if json_output:
            create_conf["response_mime_type"] = "application/json"

        # Add tools if present
        if tools:
            gemini_tools = convert_tools_to_gemini(tools)
            create_conf["tools"] = gemini_tools

        generation_config = gemini_types.GenerateContentConfig(**create_conf)

        # Get the stream generator
        generator_coroutine = await self._async_models.generate_content_stream(
            model=self._model_name,
            contents=gemini_contents,
            config=generation_config,
        )
        stream = await generator_coroutine

        # Track partial results
        text_chunks: List[str] = []  # User-visible text
        function_calls: List[FunctionCall] = []  # Accumulated function calls
        thought_chunks: List[str] = []  # Private reasoning text
        last_finish_reason: Optional[gemini_types.FinishReason] = None
        usage_so_far = RequestUsage(prompt_tokens=0, completion_tokens=0)

        while True:
            try:
                chunk_future = asyncio.ensure_future(anext(stream))
                if cancellation_token is not None:
                    cancellation_token.link_future(chunk_future)
                chunk = await chunk_future

                # Update usage from chunk metadata
                if chunk.usage_metadata:
                    usage_so_far.prompt_tokens = chunk.usage_metadata.prompt_token_count or 0
                    usage_so_far.completion_tokens = chunk.usage_metadata.candidates_token_count or 0

                if not chunk.candidates:
                    continue

                candidate = chunk.candidates[0]
                last_finish_reason = candidate.finish_reason

                if not candidate.content or not candidate.content.parts:
                    continue

                for part in candidate.content.parts:
                    if part.function_call:
                        # Accumulate function calls (don't yield partial ones)
                        fc = FunctionCall(
                            id="",  # Gemini doesn't provide IDs
                            name=part.function_call.name,
                            arguments=json.dumps(part.function_call.args or {}),
                        )
                        function_calls.append(fc)
                    elif part.text is not None:
                        if part.thought:
                            thought_chunks.append(part.text)
                        else:
                            # Yield user-visible text immediately
                            text_chunks.append(part.text)
                            yield part.text

            except StopAsyncIteration:
                break

        # Prepare final result
        content: Union[str, List[FunctionCall]]
        if function_calls:
            content = function_calls
            finish_reason = "function_calls"
        else:
            content = "".join(text_chunks)
            finish_reason = _gemini_finish_reason_to_autogen(last_finish_reason)

        thought = "\n".join(thought_chunks) if thought_chunks else None

        # Create final result with all accumulated data
        final_result = CreateResult(
            finish_reason=finish_reason,
            content=content,
            usage=usage_so_far,
            cached=False,
            logprobs=None,  # Gemini doesn't provide token logprobs (for now)
            thought=thought,
        )

        # Update client usage statistics
        self._total_usage = _add_usage(self._total_usage, usage_so_far)
        self._actual_usage = _add_usage(self._actual_usage, usage_so_far)

        yield final_result

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        if not hasattr(self._client.models, "count_tokens"):
            trace_logger.warning("Token counting not supported by this Gemini model/API version")
            return 0

        msgs_copy = list(messages)
        _system_instruction_from_messages(msgs_copy)  # TODO: How are system messages handled?
        gemini_contents = ag_messages_to_gemini(msgs_copy)

        resp = self._client.models.count_tokens(
            model=self._model_name,
            contents=gemini_contents,
        )
        return resp.total_tokens if resp.total_tokens is not None else 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        token_limit = _model_info.get_token_limit(self._model_name)
        return token_limit - self.count_tokens(messages, tools=tools)

    @property
    def model_info(self) -> ModelInfo:
        """Get information about the model's capabilities."""
        return self._model_info

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        warnings.warn(
            "capabilities is deprecated, use model_info instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._model_info

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        # Remove non-picklable Gemini client
        state["_client"] = None
        state["_async_models"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Restore instance from pickle."""
        self.__dict__.update(state)
        # Recreate Gemini client from config
        config = state["_raw_config"]
        self._client = GenaiClient(
            vertexai=config.get("vertexai", False),
            api_key=config.get("api_key", None),
            project=config.get("project", None),
            location=config.get("location", None),
        )
        self._async_models = self._client.aio.models

    def _to_config(self) -> GeminiClientConfigurationConfigModel:
        return GeminiClientConfigurationConfigModel(**self._raw_config)

    @classmethod
    def _from_config(cls, config: GeminiClientConfigurationConfigModel) -> "GeminiChatCompletionClient":
        cfg_dict = config.model_dump(exclude_none=True)
        return cls(**cfg_dict)
