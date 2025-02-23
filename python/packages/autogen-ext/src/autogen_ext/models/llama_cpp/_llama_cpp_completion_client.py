import json
import logging  # added import
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, cast

from autogen_core import EVENT_LOGGER_NAME, CancellationToken, MessageHandlerContext
from autogen_core.logging import LLMCallEvent
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from llama_cpp import (
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestFunctionMessage,
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestToolMessage,
    ChatCompletionRequestUserMessage,
    CreateChatCompletionResponse,
    Llama,
)

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


class LlamaCppChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        filename: str,
        **kwargs: Any,
    ):
        """
        Initialize the LlamaCpp client.
        """
        self.llm = (
            Llama.from_pretrained(filename=filename, repo_id=kwargs.pop("repo_id"), **kwargs)  # type: ignore
            # The partially unknown type is in the `llama_cpp` package
            if "repo_id" in kwargs
            else Llama(model_path=filename, **kwargs)
        )
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    async def create(
        self,
        messages: Sequence[SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage],
        tools: Optional[Sequence[Tool | ToolSchema]] = None,
        **kwargs: Any,
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
                raise ValueError("Image messages are not currently supported.")
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")

        if self.model_info["function_calling"]:
            # Add tool descriptions to the system message
            tool_descriptions = "\n".join(
                [f"Tool: {i+1}. {tool.name} - {tool.description}" for i, tool in enumerate(tools) if isinstance(tool, Tool)]
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

        # Debugging outputs
        # print(f"DEBUG: System message: {system_message}")
        # print(f"DEBUG: Converted messages: {converted_messages}")

        # Generate the model response
        response = cast(
            CreateChatCompletionResponse, self.llm.create_chat_completion(messages=converted_messages, stream=False)
        )

        prompt_tokens = response.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = response.get("usage", {}).get("completion_tokens", 0)

        self._total_usage["prompt_tokens"] += prompt_tokens
        self._total_usage["completion_tokens"] += completion_tokens

        # Parse the response
        response_text = response["choices"][0]["message"]["content"]
        # print(f"DEBUG: Model response: {response_text}")

        # Detect tool usage in the response
        if not response_text:
            logger.debug("DEBUG: No response text found. Returning empty response.")
            return CreateResult(
                content="", usage=RequestUsage(prompt_tokens=0, completion_tokens=0), finish_reason="stop", cached=False
            )

        tool_call = await self._detect_and_execute_tool(
            response_text, [tool for tool in tools if isinstance(tool, Tool)]
        )
        if not tool_call:
            logger.debug("DEBUG: No tool was invoked. Returning raw model response.")
        else:
            logger.debug(f"DEBUG: Tool executed successfully: {tool_call}")

        # Create a CreateResult object
        finish_reason = response["choices"][0].get("finish_reason")
        if finish_reason not in ("stop", "length", "function_calls", "content_filter", "unknown"):
            finish_reason = "unknown"
        usage = cast(RequestUsage, response.get("usage", {}))
        create_result = CreateResult(
            content=tool_call if tool_call else response_text,
            usage=usage,
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
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                agent_id=agent_id,
            )
        )
        return create_result

    async def _detect_and_execute_tool(self, response_text: str, tools: List[Tool]) -> Optional[str]:
        """
        Detect if the model is requesting a tool and execute the tool.

        :param response_text: The raw response text from the model.
        :param tools: A list of available tools.
        :return: The result of the tool execution or None if no tool is called.
        """
        for tool in tools:
            if tool.name.lower() in response_text.lower():  # Case-insensitive matching
                logger.debug(f"DEBUG: Detected tool '{tool.name}' in response.")
                # Extract arguments (if any) from the response
                func_args = self._extract_tool_arguments(response_text)
                if func_args:
                    logger.debug(f"DEBUG: Extracted arguments for tool '{tool.name}': {func_args}")
                else:
                    logger.debug(f"DEBUG: No arguments found for tool '{tool.name}'.")
                    return f"Error: No valid arguments provided for tool '{tool.name}'."

                # Ensure arguments match the tool's args_type
                try:
                    args_model = tool.args_type()
                    if "request" in args_model.model_fields:  # Handle nested arguments
                        func_args = {"request": func_args}
                    args_instance = args_model(**func_args)
                except Exception as e:
                    return f"Error parsing arguments for tool '{tool.name}': {e}"

                # Execute the tool
                try:
                    if callable(getattr(tool, "run", None)):
                        result = await cast(Any, tool).run(args=args_instance, cancellation_token=CancellationToken())
                        if isinstance(result, dict):
                            return json.dumps(result)
                        elif callable(getattr(result, "model_dump", None)):  # If it's a Pydantic model
                            return json.dumps(result.model_dump())
                        else:
                            return str(result)
                except Exception as e:
                    return f"Error executing tool '{tool.name}': {e}"

        return None

    def _extract_tool_arguments(self, response_text: str) -> Dict[str, Any]:
        """
        Extract tool arguments from the response text.

        :param response_text: The raw response text.
        :return: A dictionary of extracted arguments.
        """
        try:
            args_start = response_text.find("{")
            args_end = response_text.find("}")
            if args_start != -1 and args_end != -1:
                args_str = response_text[args_start : args_end + 1]
                args = json.loads(args_str)
                if isinstance(args, dict):
                    return cast(Dict[str, Any], args)
                else:
                    return {}
        except json.JSONDecodeError as e:
            logger.debug(f"DEBUG: Failed to parse arguments: {e}")
        return {}

    async def create_stream(
        self,
        messages: Sequence[SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage],
        tools: Optional[Sequence[Tool | ToolSchema]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Stream not yet implemented for LlamaCppChatCompletionClient")
        if False:  # Unreachable code to satisfy the return type.
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
