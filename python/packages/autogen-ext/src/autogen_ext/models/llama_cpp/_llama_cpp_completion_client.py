import asyncio
import logging  # added import
import re
from typing import Any, AsyncGenerator, Dict, List, Literal, Mapping, Optional, Sequence, TypedDict, Union, cast

from autogen_core import EVENT_LOGGER_NAME, CancellationToken, FunctionCall, MessageHandlerContext
from autogen_core.logging import LLMCallEvent
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
    validate_model_info,
)
from autogen_core.tools import Tool, ToolSchema
from llama_cpp import (
    ChatCompletionFunctionParameters,
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestFunctionMessage,
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestToolMessage,
    ChatCompletionRequestUserMessage,
    ChatCompletionTool,
    ChatCompletionToolFunction,
    Llama,
    llama_chat_format,
)
from pydantic import BaseModel
from typing_extensions import Unpack

logger = logging.getLogger(EVENT_LOGGER_NAME)  # initialize logger


def normalize_stop_reason(stop_reason: str | None) -> FinishReasons:
    if stop_reason is None:
        return "unknown"

    # Convert to lower case
    stop_reason = stop_reason.lower()

    KNOWN_STOP_MAPPINGS: Dict[str, FinishReasons] = {
        "stop": "stop",
        "length": "length",
        "content_filter": "content_filter",
        "function_calls": "function_calls",
        "end_turn": "stop",
        "tool_calls": "function_calls",
    }

    return KNOWN_STOP_MAPPINGS.get(stop_reason, "unknown")


def normalize_name(name: str) -> str:
    """
    LLMs sometimes ask functions while ignoring their own format requirements, this function should be used to replace invalid characters with "_".

    Prefer _assert_valid_name for validating user configuration or input
    """
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]


def assert_valid_name(name: str) -> str:
    """
    Ensure that configured names are valid, raises ValueError if not.

    For munging LLM responses use _normalize_name to ensure LLM specified names don't break the API.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
    if len(name) > 64:
        raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
    return name


def convert_tools(
    tools: Sequence[Tool | ToolSchema],
) -> List[ChatCompletionTool]:
    result: List[ChatCompletionTool] = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema
        else:
            assert isinstance(tool, dict)
            tool_schema = tool

        result.append(
            ChatCompletionTool(
                type="function",
                function=ChatCompletionToolFunction(
                    name=tool_schema["name"],
                    description=(tool_schema["description"] if "description" in tool_schema else ""),
                    parameters=(
                        cast(ChatCompletionFunctionParameters, tool_schema["parameters"])
                        if "parameters" in tool_schema
                        else {}
                    ),
                ),
            )
        )
    # Check if all tools have valid names.
    for tool_param in result:
        assert_valid_name(tool_param["function"]["name"])
    return result


class LlamaCppParams(TypedDict, total=False):
    # from_pretrained parameters:
    repo_id: Optional[str]
    filename: Optional[str]
    additional_files: Optional[List[Any]]
    local_dir: Optional[str]
    local_dir_use_symlinks: Union[bool, Literal["auto"]]
    cache_dir: Optional[str]
    # __init__ parameters:
    model_path: str
    n_gpu_layers: int
    split_mode: int
    main_gpu: int
    tensor_split: Optional[List[float]]
    rpc_servers: Optional[str]
    vocab_only: bool
    use_mmap: bool
    use_mlock: bool
    kv_overrides: Optional[Dict[str, Union[bool, int, float, str]]]
    seed: int
    n_ctx: int
    n_batch: int
    n_ubatch: int
    n_threads: Optional[int]
    n_threads_batch: Optional[int]
    rope_scaling_type: Optional[int]
    pooling_type: int
    rope_freq_base: float
    rope_freq_scale: float
    yarn_ext_factor: float
    yarn_attn_factor: float
    yarn_beta_fast: float
    yarn_beta_slow: float
    yarn_orig_ctx: int
    logits_all: bool
    embedding: bool
    offload_kqv: bool
    flash_attn: bool
    no_perf: bool
    last_n_tokens_size: int
    lora_base: Optional[str]
    lora_scale: float
    lora_path: Optional[str]
    numa: Union[bool, int]
    chat_format: Optional[str]
    chat_handler: Optional[llama_chat_format.LlamaChatCompletionHandler]
    draft_model: Optional[Any]  # LlamaDraftModel not exposed by llama_cpp
    tokenizer: Optional[Any]  # BaseLlamaTokenizer not exposed by llama_cpp
    type_k: Optional[int]
    type_v: Optional[int]
    spm_infill: bool
    verbose: bool


class LlamaCppChatCompletionClient(ChatCompletionClient):
    """Chat completion client for LlamaCpp models.
    To use this client, you must install the `llama-cpp` extra:

    .. code-block:: bash

        pip install "autogen-ext[llama-cpp]"

    This client allows you to interact with LlamaCpp models, either by specifying a local model path or by downloading a model from Hugging Face Hub.

    Args:
        model_info (optional, ModelInfo): The information about the model. Defaults to :attr:`~LlamaCppChatCompletionClient.DEFAULT_MODEL_INFO`.
        model_path (optional, str): The path to the LlamaCpp model file. Required if repo_id and filename are not provided.
        repo_id (optional, str): The Hugging Face Hub repository ID. Required if model_path is not provided.
        filename (optional, str): The filename of the model within the Hugging Face Hub repository. Required if model_path is not provided.
        n_gpu_layers (optional, int): The number of layers to put on the GPU.
        n_ctx (optional, int): The context size.
        n_batch (optional, int): The batch size.
        verbose (optional, bool): Whether to print verbose output.
        **kwargs: Additional parameters to pass to the Llama class.

    Examples:

        The following code snippet shows how to use the client with a local model file:

        .. code-block:: python

            import asyncio

            from autogen_core.models import UserMessage
            from autogen_ext.models.llama_cpp import LlamaCppChatCompletionClient


            async def main():
                llama_client = LlamaCppChatCompletionClient(model_path="/path/to/your/model.gguf")
                result = await llama_client.create([UserMessage(content="What is the capital of France?", source="user")])
                print(result)


            asyncio.run(main())

        The following code snippet shows how to use the client with a model from Hugging Face Hub:

        .. code-block:: python

            import asyncio

            from autogen_core.models import UserMessage
            from autogen_ext.models.llama_cpp import LlamaCppChatCompletionClient


            async def main():
                llama_client = LlamaCppChatCompletionClient(
                    repo_id="unsloth/phi-4-GGUF", filename="phi-4-Q2_K_L.gguf", n_gpu_layers=-1, seed=1337, n_ctx=5000
                )
                result = await llama_client.create([UserMessage(content="What is the capital of France?", source="user")])
                print(result)


            asyncio.run(main())
    """

    DEFAULT_MODEL_INFO: ModelInfo = ModelInfo(
        vision=False, json_output=True, family=ModelFamily.UNKNOWN, function_calling=True, structured_output=True
    )

    def __init__(
        self,
        model_info: Optional[ModelInfo] = None,
        **kwargs: Unpack[LlamaCppParams],
    ) -> None:
        """
        Initialize the LlamaCpp client.
        """

        if model_info:
            validate_model_info(model_info)
            self._model_info = model_info
        else:
            # Default model info.
            self._model_info = self.DEFAULT_MODEL_INFO

        if "repo_id" in kwargs and "filename" in kwargs and kwargs["repo_id"] and kwargs["filename"]:
            repo_id: str = cast(str, kwargs.pop("repo_id"))
            filename: str = cast(str, kwargs.pop("filename"))
            pretrained = Llama.from_pretrained(repo_id=repo_id, filename=filename, **kwargs)  # type: ignore
            assert isinstance(pretrained, Llama)
            self.llm = pretrained

        elif "model_path" in kwargs:
            self.llm = Llama(**kwargs)  # pyright: ignore[reportUnknownMemberType]
        else:
            raise ValueError("Please provide model_path if ... or provide repo_id and filename if ....")
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto"] | None = "auto",
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        create_args = dict(extra_create_args)
        # Convert LLMMessage objects to dictionaries with 'role' and 'content'
        # converted_messages: List[Dict[str, str | Image | list[str | Image] | list[FunctionCall]]] = []
        converted_messages: list[
            ChatCompletionRequestSystemMessage
            | ChatCompletionRequestUserMessage
            | ChatCompletionRequestAssistantMessage
            | ChatCompletionRequestUserMessage
            | ChatCompletionRequestToolMessage
            | ChatCompletionRequestFunctionMessage
        ] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, UserMessage) and isinstance(msg.content, str):
                converted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AssistantMessage) and isinstance(msg.content, str):
                converted_messages.append({"role": "assistant", "content": msg.content})
            elif (
                isinstance(msg, SystemMessage) or isinstance(msg, UserMessage) or isinstance(msg, AssistantMessage)
            ) and isinstance(msg.content, list):
                raise ValueError("Multi-part messages such as those containing images are currently not supported.")
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")

        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            create_args["response_format"] = {"type": "json_object", "schema": json_output.model_json_schema()}
        elif json_output is True:
            create_args["response_format"] = {"type": "json_object"}
        elif json_output is not False and json_output is not None:
            raise ValueError("json_output must be a boolean, a BaseModel subclass or None.")

        # Handle tool_choice parameter
        if tool_choice is not None:
            if not self.model_info["function_calling"]:
                raise ValueError("tool_choice specified but model does not support function calling")
            if len(tools) == 0:
                raise ValueError("tool_choice specified but no tools provided")
            logger.warning("tool_choice parameter specified but may not be supported by llama-cpp-python")

        if self.model_info["function_calling"]:
            # Run this in on the event loop to avoid blocking.
            response_future = asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.llm.create_chat_completion(
                    messages=converted_messages, tools=convert_tools(tools), stream=False, **create_args
                ),
            )
        else:
            response_future = asyncio.get_event_loop().run_in_executor(
                None, lambda: self.llm.create_chat_completion(messages=converted_messages, stream=False, **create_args)
            )
        if cancellation_token:
            cancellation_token.link_future(response_future)
        response = await response_future

        if not isinstance(response, dict):
            raise ValueError("Unexpected response type from LlamaCpp model.")

        self._total_usage["prompt_tokens"] += response["usage"]["prompt_tokens"]
        self._total_usage["completion_tokens"] += response["usage"]["completion_tokens"]

        # Parse the response
        response_tool_calls: ChatCompletionTool | None = None
        response_text: str | None = None
        if "choices" in response and len(response["choices"]) > 0:
            if "message" in response["choices"][0]:
                response_text = response["choices"][0]["message"]["content"]
            if "tool_calls" in response["choices"][0]:
                response_tool_calls = response["choices"][0]["tool_calls"]  # type: ignore

        content: List[FunctionCall] | str = ""
        thought: str | None = None
        if response_tool_calls:
            content = []
            for tool_call in response_tool_calls:
                if not isinstance(tool_call, dict):
                    raise ValueError("Unexpected tool call type from LlamaCpp model.")
                content.append(
                    FunctionCall(
                        id=tool_call["id"],
                        arguments=tool_call["function"]["arguments"],
                        name=normalize_name(tool_call["function"]["name"]),
                    )
                )
            if response_text and len(response_text) > 0:
                thought = response_text
        else:
            if response_text:
                content = response_text

        # Detect tool usage in the response
        if not response_tool_calls and not response_text:
            logger.debug("DEBUG: No response text found. Returning empty response.")
            return CreateResult(
                content="", usage=RequestUsage(prompt_tokens=0, completion_tokens=0), finish_reason="stop", cached=False
            )

        # Create a CreateResult object
        if "finish_reason" in response["choices"][0]:
            finish_reason = response["choices"][0]["finish_reason"]
        else:
            finish_reason = "unknown"
        if finish_reason not in ("stop", "length", "function_calls", "content_filter", "unknown"):
            finish_reason = "unknown"
        create_result = CreateResult(
            content=content,
            thought=thought,
            usage=cast(RequestUsage, response["usage"]),
            finish_reason=normalize_stop_reason(finish_reason),  # type: ignore
            cached=False,
        )

        # If we are running in the context of a handler we can get the agent_id
        try:
            agent_id = MessageHandlerContext.agent_id()
        except RuntimeError:
            agent_id = None

        logger.info(
            LLMCallEvent(
                messages=cast(List[Dict[str, Any]], converted_messages),
                response=create_result.model_dump(),
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                agent_id=agent_id,
            )
        )
        return create_result

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto"] | None = "auto",
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        # Validate tool_choice parameter even though streaming is not implemented
        if tool_choice is not None:
            if not self.model_info["function_calling"]:
                raise ValueError("tool_choice specified but model does not support function calling")
            if len(tools) == 0:
                raise ValueError("tool_choice specified but no tools provided")
            logger.warning("tool_choice parameter specified but may not be supported by llama-cpp-python")
        
        raise NotImplementedError("Stream not yet implemented for LlamaCppChatCompletionClient")
        yield ""

    # Implement abstract methods
    def actual_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_usage.get("prompt_tokens", 0),
            completion_tokens=self._total_usage.get("completion_tokens", 0),
        )

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info

    def count_tokens(
        self,
        messages: Sequence[SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage],
        **kwargs: Any,
    ) -> int:
        total = 0
        for msg in messages:
            # Use the Llama model's tokenizer to encode the content
            tokens = self.llm.tokenize(str(msg.content).encode("utf-8"))
            total += len(tokens)
        return total

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    def remaining_tokens(
        self,
        messages: Sequence[SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage],
        **kwargs: Any,
    ) -> int:
        used_tokens = self.count_tokens(messages)
        return max(self.llm.n_ctx() - used_tokens, 0)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_usage.get("prompt_tokens", 0),
            completion_tokens=self._total_usage.get("completion_tokens", 0),
        )

    async def close(self) -> None:
        """
        Close the LlamaCpp client.
        """
        self.llm.close()
