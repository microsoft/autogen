import json
import logging  # added import
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Sequence, Union

from autogen_core import CancellationToken
from autogen_core.models import AssistantMessage, ChatCompletionClient, CreateResult, SystemMessage, UserMessage
from autogen_core.tools import Tool
from llama_cpp import Llama
from pydantic import BaseModel


class ComponentModel(BaseModel):
    provider: str
    component_type: Optional[Literal["model", "agent", "tool", "termination", "token_provider"]] = None
    version: Optional[int] = None
    component_version: Optional[int] = None
    description: Optional[str] = None
    config: Dict[str, Any]


class LlamaCppChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        repo_id: str,
        filename: str,
        n_gpu_layers: int = -1,
        seed: int = 1337,
        n_ctx: int = 1000,
        verbose: bool = True,
    ):
        """
        Initialize the LlamaCpp client.
        """
        self.logger = logging.getLogger(__name__)  # initialize logger
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)  # set level based on verbosity
        self.llm = Llama.from_pretrained(
            repo_id=repo_id,
            filename=filename,
            n_gpu_layers=n_gpu_layers,
            seed=seed,
            n_ctx=n_ctx,
            verbose=verbose,
        )
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    async def create(self, messages: List[Any], tools: List[Any] = None, **kwargs) -> CreateResult:
        """
        Generate a response using the model, incorporating tool metadata.

        :param messages: A list of message objects to process.
        :param tools: A list of tool objects to register dynamically.
        :param kwargs: Additional arguments for the model.
        :return: A CreateResult object containing the model's response.
        """
        tools = tools or []

        # Convert LLMMessage objects to dictionaries with 'role' and 'content'
        converted_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, UserMessage):
                converted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AssistantMessage):
                converted_messages.append({"role": "assistant", "content": msg.content})
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")

        # Add tool descriptions to the system message
        tool_descriptions = "\n".join(
            [f"Tool: {i+1}. {tool.name} - {tool.description}" for i, tool in enumerate(tools)]
        )

        few_shot_example = """
        Example tool usage:
        User: Validate this request: {"patient_name": "John Doe", "patient_id": "12345", "procedure": "MRI Knee"}
        Assistant: Calling tool 'validate_request' with arguments: {"patient_name": "John Doe", "patient_id": "12345", "procedure": "MRI Knee"}
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
        response = self.llm.create_chat_completion(messages=converted_messages, stream=False)
        self._total_usage["prompt_tokens"] += response.get("usage", {}).get("prompt_tokens", 0)
        self._total_usage["completion_tokens"] += response.get("usage", {}).get("completion_tokens", 0)

        # Parse the response
        response_text = response["choices"][0]["message"]["content"]
        # print(f"DEBUG: Model response: {response_text}")

        # Detect tool usage in the response
        tool_call = await self._detect_and_execute_tool(response_text, tools)
        if not tool_call:
            self.logger.debug("DEBUG: No tool was invoked. Returning raw model response.")
        else:
            self.logger.debug(f"DEBUG: Tool executed successfully: {tool_call}")

        # Create a CreateResult object
        create_result = CreateResult(
            content=tool_call if tool_call else response_text,
            usage=response.get("usage", {}),
            finish_reason=response["choices"][0].get("finish_reason", "unknown"),
            cached=False,
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
                self.logger.debug(f"DEBUG: Detected tool '{tool.name}' in response.")
                # Extract arguments (if any) from the response
                func_args = self._extract_tool_arguments(response_text)
                if func_args:
                    self.logger.debug(f"DEBUG: Extracted arguments for tool '{tool.name}': {func_args}")
                else:
                    self.logger.debug(f"DEBUG: No arguments found for tool '{tool.name}'.")
                    return f"Error: No valid arguments provided for tool '{tool.name}'."

                # Ensure arguments match the tool's args_type
                try:
                    args_model = tool.args_type()
                    if "request" in args_model.__fields__:  # Handle nested arguments
                        func_args = {"request": func_args}
                    args_instance = args_model(**func_args)
                except Exception as e:
                    return f"Error parsing arguments for tool '{tool.name}': {e}"

                # Execute the tool
                try:
                    result = await tool.run(args=args_instance, cancellation_token=CancellationToken())
                    if isinstance(result, dict):
                        return json.dumps(result)
                    elif hasattr(result, "model_dump"):  # If it's a Pydantic model
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
                return json.loads(args_str)
        except json.JSONDecodeError as e:
            self.logger.debug(f"DEBUG: Failed to parse arguments: {e}")
        return {}

    async def create_stream(self, messages: List[Any], tools: List[Any] = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using the model.

        :param messages: A list of messages to process.
        :param tools: A list of tool objects to register dynamically.
        :param kwargs: Additional arguments for the model.
        :return: An asynchronous generator yielding the response stream.
        """
        tools = tools or []

        # Convert LLMMessage objects to dictionaries with 'role' and 'content'
        converted_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, UserMessage):
                converted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AssistantMessage):
                converted_messages.append({"role": "assistant", "content": msg.content})
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")

        # Add tool descriptions to the system message
        tool_descriptions = "\n".join([f"Tool: {tool.name} - {tool.description}" for tool in tools])
        if tool_descriptions:
            converted_messages.insert(
                0, {"role": "system", "content": f"The following tools are available:\n{tool_descriptions}"}
            )

        # Convert messages into a plain string prompt
        prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in converted_messages)
        # Call the model with streaming enabled
        response_generator = self.llm(prompt=prompt, stream=True)

        for token in response_generator:
            yield token["choices"][0]["text"]

    # Implement abstract methods
    def actual_usage(self) -> Dict[str, int]:
        return self._total_usage

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {"chat": True, "stream": True}

    def count_tokens(self, messages: Sequence[Dict[str, Any]], **kwargs) -> int:
        return sum(len(msg["content"].split()) for msg in messages)

    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "name": "llama-cpp",
            "capabilities": {"chat": True, "stream": True},
            "context_window": self.llm.n_ctx,
            "function_calling": True,
        }

    def remaining_tokens(self, messages: Sequence[Dict[str, Any]], **kwargs) -> int:
        used_tokens = self.count_tokens(messages)
        return max(self.llm.n_ctx - used_tokens, 0)

    def total_usage(self) -> Dict[str, int]:
        return self._total_usage
