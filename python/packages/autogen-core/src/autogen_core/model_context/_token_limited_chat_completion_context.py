from typing import List, Sequence, cast
import logging
import json
from autogen_core.tools import Tool, ToolSchema
from autogen_core import Image
from autogen_core.models import UserMessage
from autogen_core import TRACE_LOGGER_NAME

from pydantic import BaseModel
from typing_extensions import Self
import tiktoken

from .._component_config import Component
from ..models import FunctionExecutionResultMessage, LLMMessage
from ._chat_completion_context import ChatCompletionContext

from autogen_ext.models.ollama._ollama_client import to_ollama_type, convert_tools, calculate_vision_tokens
from autogen_ext.models.openai._openai_client import to_oai_type
from openai.types.chat import ChatCompletionContentPartParam

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


class TokenLimitedChatCompletionContextConfig(BaseModel):
    token_limit: int
    model: str
    initial_messages: List[LLMMessage] | None = None


class TokenLimitedChatCompletionContext(ChatCompletionContext, Component[TokenLimitedChatCompletionContextConfig]):
    """A token based chat completion context maintains a view of the context up to a token limit,
    where n is the token limit. The token limit is set at initialization.

    Args:
        token_limit (int): Max tokens for context.
        initial_messages (List[LLMMessage] | None): The initial messages.
    """

    component_config_schema = TokenLimitedChatCompletionContextConfig
    component_provider_override = "autogen_core.model_context.TokenLimitedChatCompletionContext"

    def __init__(self, token_limit: int, model: str, initial_messages: List[LLMMessage] | None = None) -> None:
        super().__init__(initial_messages)
        if token_limit <= 0:
            raise ValueError("token_limit must be greater than 0.")
        self._token_limit = token_limit
        self._model = model

    async def get_messages(self) -> List[LLMMessage]:
        """Get at most `token_limit` tokens in recent messages."""
        token_count = count_chat_tokens(self._messages, self._model)
        while token_count > self._token_limit:
            middle_index = len(self._messages) // 2
            self._messages.pop(middle_index)
            token_count = count_chat_tokens(self._messages, self._model)
        messages = self._messages
        # Handle the first message is a function call result message.
        if messages and isinstance(messages[0], FunctionExecutionResultMessage):
            # Remove the first message from the list.
            messages = messages[1:]
        return messages

    def _to_config(self) -> TokenLimitedChatCompletionContextConfig:
        return TokenLimitedChatCompletionContextConfig(
            token_limit=self._token_limit, model=self._model, initial_messages=self._messages
        )

    @classmethod
    def _from_config(cls, config: TokenLimitedChatCompletionContextConfig) -> Self:
        return cls(**config.model_dump())


def count_chat_tokens(
    messages: Sequence[LLMMessage], model: str = "gpt-4o", *, tools: Sequence[Tool | ToolSchema] = []
) -> int:
    """Count tokens for a list of messages using the appropriate client based on the model."""
    try:
        # Check if the model is an OpenAI model
        if "gpt" in model.lower():
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                trace_logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
                encoding = tiktoken.get_encoding("cl100k_base")
            tokens_per_message = 3
            tokens_per_name = 1
            num_tokens = 0

            # Message tokens.
            for message in messages:
                num_tokens += tokens_per_message
                oai_message = to_oai_type(message)
                for oai_message_part in oai_message:
                    for key, value in oai_message_part.items():
                        if value is None:
                            continue

                        if isinstance(message, UserMessage) and isinstance(value, list):
                            typed_message_value = cast(List[ChatCompletionContentPartParam], value)

                            assert len(typed_message_value) == len(
                                message.content
                            ), "Mismatch in message content and typed message value"

                            # We need image properties that are only in the original message
                            for part, content_part in zip(typed_message_value, message.content, strict=False):
                                if isinstance(content_part, Image):
                                    # TODO: add detail parameter
                                    num_tokens += calculate_vision_tokens(content_part)
                                elif isinstance(part, str):
                                    num_tokens += len(encoding.encode(part))
                                else:
                                    try:
                                        serialized_part = json.dumps(part)
                                        num_tokens += len(encoding.encode(serialized_part))
                                    except TypeError:
                                        trace_logger.warning(f"Could not convert {part} to string, skipping.")
                        else:
                            if not isinstance(value, str):
                                try:
                                    value = json.dumps(value)
                                except TypeError:
                                    trace_logger.warning(f"Could not convert {value} to string, skipping.")
                                    continue
                            num_tokens += len(encoding.encode(value))
                            if key == "name":
                                num_tokens += tokens_per_name
            num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
            return num_tokens

        # Check if the model is an Ollama model
        elif "ollama" in model.lower():
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                trace_logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
                encoding = tiktoken.get_encoding("cl100k_base")
            tokens_per_message = 3
            num_tokens = 0

            # Message tokens.
            for message in messages:
                num_tokens += tokens_per_message
                ollama_message = to_ollama_type(message)
                for ollama_message_part in ollama_message:
                    if isinstance(message.content, Image):
                        num_tokens += calculate_vision_tokens(message.content)
                    elif ollama_message_part.content is not None:
                        num_tokens += len(encoding.encode(ollama_message_part.content))
            # TODO: every model family has its own message sequence.
            num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

            # Tool tokens.
            ollama_tools = convert_tools(tools)
            for tool in ollama_tools:
                function = tool["function"]
                tool_tokens = len(encoding.encode(function["name"]))
                if "description" in function:
                    tool_tokens += len(encoding.encode(function["description"]))
                tool_tokens -= 2
                if "parameters" in function:
                    parameters = function["parameters"]
                    if "properties" in parameters:
                        assert isinstance(parameters["properties"], dict)
                        for propertiesKey in parameters["properties"]:  # pyright: ignore
                            assert isinstance(propertiesKey, str)
                            tool_tokens += len(encoding.encode(propertiesKey))
                            v = parameters["properties"][propertiesKey]  # pyright: ignore
                            for field in v:  # pyright: ignore
                                if field == "type":
                                    tool_tokens += 2
                                    tool_tokens += len(encoding.encode(v["type"]))  # pyright: ignore
                                elif field == "description":
                                    tool_tokens += 2
                                    tool_tokens += len(encoding.encode(v["description"]))  # pyright: ignore
                                elif field == "enum":
                                    tool_tokens -= 3
                                    for o in v["enum"]:  # pyright: ignore
                                        tool_tokens += 3
                                        tool_tokens += len(encoding.encode(o))  # pyright: ignore
                                else:
                                    trace_logger.warning(f"Not supported field {field}")
                        tool_tokens += 11
                        if len(parameters["properties"]) == 0:  # pyright: ignore
                            tool_tokens -= 2
                num_tokens += tool_tokens
            num_tokens += 12
            return num_tokens

        # Fallback to cl100k_base encoding if the model is unrecognized
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
            total_tokens = 0
            for message in messages:
                total_tokens += len(encoding.encode(str(message.content)))
            return total_tokens

    except Exception as e:
        # Log the error and re-raise
        trace_logger.error(f"Error counting tokens: {e}")
        raise
