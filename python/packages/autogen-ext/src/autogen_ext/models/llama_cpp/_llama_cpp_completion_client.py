import logging  # added import
import re
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional, Sequence, Union, cast

from autogen_core import EVENT_LOGGER_NAME, CancellationToken, FunctionCall, MessageHandlerContext
from autogen_core.logging import LLMCallEvent
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
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
)

logger = logging.getLogger(EVENT_LOGGER_NAME)  # initialize logger


def from_pretrained(
    model_path: str,
    repo_id: str | None = None,
    model_info: ModelInfo | None = None,
    additional_files: List[str] | None = None,
    local_dir: str | None = None,
    local_dir_use_symlinks: str = "auto",
    cache_dir: str | None = None,
    **kwargs: Any,
) -> Llama:
    """
    Load a model from the Hugging Face Hub or a local directory.

    :param repo_id: The repository ID of the model.
    :param filename: The filename of the model.
    :param model_info: The model info.
    :param additional_files: Additional files to download.
    :param local_dir: The local directory to load the model from.
    :param local_dir_use_symlinks: Whether to use symlinks for the local directory.
    :param cache_dir: The cache directory.
    :param kwargs: Additional keyword arguments.
    :return: The loaded model.
    """
    if repo_id:
        return Llama.from_pretrained(repo_id=repo_id, filename=model_path, **kwargs) # pyright: ignore[reportUnknownMemberType]
        # The partially unknown type is in the `llama_cpp` package
    else:
        return Llama(model_path=model_path, **kwargs)


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


class LlamaCppChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        filename: str,
        repo_id: str | None = None,
        model_info: ModelInfo | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the LlamaCpp client.
        """
        self.llm: Llama = from_pretrained(repo_id=repo_id, model_path=filename, model_info=model_info, kwargs=kwargs)
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        tools = tools or []

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

        if self.model_info["function_calling"]:
            response = self.llm.create_chat_completion(
                messages=converted_messages, tools=convert_tools(tools), stream=False
            )

        else:
            # Add tool descriptions to the system message
            tool_descriptions = "\n".join(
                [
                    f"Tool: {i+1}. {tool.name} - {tool.description}"
                    for i, tool in enumerate(tools)
                    if isinstance(tool, Tool)
                ]
            )

            few_shot_example = """
            Example tool usage:
            User: Add two numbers: {"num1": 5, "num2": 10}
            Assistant: Calling tool 'add' with arguments: {"num1": 5, "num2": 10}
            """

            system_message = (
                "You are an assistant with access to tools. "
                "If a user query matches a tool, explicitly invoke it with JSON arguments. "
                "Here are the tools available:\n"
                f"{tool_descriptions}\n"
                f"{few_shot_example}"
            )
            converted_messages.insert(0, {"role": "system", "content": system_message})

            response = self.llm.create_chat_completion(messages=converted_messages, stream=False)

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
        elif response_text:
            content = await self._detect_tool(response_text, [tool for tool in tools if isinstance(tool, Tool)])
            if len(content) > 0 and len(response_text) > 0:
                thought = response_text
            else:
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
                messages=cast(Dict[str, Any], messages),
                response=create_result.model_dump(),
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"],
                agent_id=agent_id,
            )
        )
        return create_result

    async def _detect_tool(self, response_text: str, tools: List[Tool]) -> List[FunctionCall]:
        """
        Detect if the model is requesting a tool and execute the tool.

        :param response_text: The raw response text from the model.
        :param tools: A list of available tools.
        :return: The result of the tool execution or None if no tool is called.
        """
        content: List[FunctionCall] = []
        if not tools:
            return []
        for tool in tools:
            if tool.name.lower() + "(" in response_text.lower():  # Case-insensitive matching
                logger.debug(f"DEBUG: Detected tool '{tool.name}' in response.")
                # Extract arguments (if any) from the response
                func_args = self._extract_tool_arguments(response_text)
                content.append(
                    FunctionCall(
                        id="",
                        arguments=func_args,
                        name=normalize_name(tool.name),
                    )
                )

        return content

    def _extract_tool_arguments(self, response_text: str) -> str:
        """
        Extract tool arguments from the response text.

        :param response_text: The raw response text.
        :return: A dictionary of extracted arguments.
        """
        args_start = response_text.find("{")
        args_end = response_text.find("}")
        if args_start != -1 and args_end != -1:
            return response_text[args_start : args_end + 1]

        return ""

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
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
        return ModelInfo(vision=False, json_output=False, family="llama-cpp", function_calling=True)

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
