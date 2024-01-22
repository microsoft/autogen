import asyncio
import functools
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from autogen.agentchat.agent import Agent
from autogen._pydantic import model_dump
from autogen.cache.cache import Cache
from autogen.oai.client import OpenAIWrapper

logger = logging.getLogger(__name__)


class LLMMiddleware:
    """A middleware for creating LLM generated response.

    This middleware handles messages with OpenAI-compatible schema.

    Args:
        llm_config (Dict): LLM inference configuration. Please refer to
            [OpenAIWrapper.create](/docs/reference/oai/client#create) for available options.
        system_message (Optional[Union[str, List]]): the system message for ChatCompletion inference.
    """

    def __init__(
        self,
        name: str,
        llm_config: Optional[Union[Dict[str, Any], bool]],
        system_message: Union[str, List] = "You are a helpful AI Assistant.",
        cache: Optional[Cache] = None,
    ) -> None:
        if isinstance(system_message, str):
            self._oai_system_messages = [{"content": system_message, "role": "system"}]
        elif isinstance(system_message, list):
            self._oai_system_messages = system_message
        else:
            raise ValueError(f"system_message must be a string or a list of messages, but got {system_message}")
        if llm_config is None:
            raise ValueError("llm_config must be provided")
        if not (isinstance(llm_config, dict) or isinstance(llm_config, bool)):
            raise ValueError(f"llm_config must be a dict or bool, but got {llm_config}")
        self._name = name
        self._llm_config = llm_config
        self._client = OpenAIWrapper(**self._llm_config) if llm_config else None
        self._client_cache = cache

    @property
    def system_messages(self) -> List[Dict]:
        return self._oai_system_messages

    @system_messages.setter
    def system_messages(self, system_message: Union[str, List]) -> None:
        if isinstance(system_message, str):
            self._oai_system_messages = [{"content": system_message, "role": "system"}]
        elif isinstance(system_message, list):
            self._oai_system_messages = system_message
        else:
            raise ValueError(f"system_message must be a string or a list of messages, but got {system_message}")

    @property
    def client(self) -> OpenAIWrapper:
        return self._client

    @client.setter
    def client(self, client: OpenAIWrapper) -> None:
        self._client = client

    @property
    def client_cache(self) -> Cache:
        return self._client_cache

    @client_cache.setter
    def client_cache(self, cache: Cache) -> None:
        self._client_cache = cache

    def call(
        self,
        messages: List[Dict],
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        """Call the middleware.

        Args:
            messages (List[Dict]): the messages to be processed.
            sender (Optional[Agent]): the sender of the messages.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.
        """
        if self._llm_config is False:
            return next(messages, sender)
        else:
            final, reply = self._generate_oai_reply(messages)
            if final:
                return reply
            else:
                return next(messages, sender)

    async def a_call(
        self,
        messages: List[Dict],
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        """Call the middleware asynchronously.

        Args:
            messages (List[Dict]): the messages to be processed.
            sender (Optional[Agent]): the sender of the messages.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.
        """
        if self._llm_config is False:
            return next(messages, sender)
        else:
            final, reply = await self._a_generate_oai_reply(messages)
            if final:
                return reply
            else:
                return await next(messages, sender)

    def update_function_signature(self, func_sig: Union[str, Dict], is_remove: None):
        """update a function_signature in the LLM configuration for function_call.

        Args:
            func_sig (str or dict): description/name of the function to update/remove to the model. See: https://platform.openai.com/docs/api-reference/chat/create#chat/create-functions
            is_remove: whether removing the function from llm_config with name 'func_sig'

        Deprecated as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-function_call
        """

        if not isinstance(self._llm_config, dict):
            error_msg = "To update a function signature, agent must have an llm_config"
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if is_remove:
            if "functions" not in self._llm_config.keys():
                error_msg = "The agent config doesn't have function {name}.".format(name=func_sig)
                logger.error(error_msg)
                raise AssertionError(error_msg)
            else:
                self._llm_config["functions"] = [
                    func for func in self._llm_config["functions"] if func["name"] != func_sig
                ]
        else:
            self._assert_valid_name(func_sig["name"])
            if "functions" in self._llm_config.keys():
                self._llm_config["functions"] = [
                    func for func in self._llm_config["functions"] if func.get("name") != func_sig["name"]
                ] + [func_sig]
            else:
                self._llm_config["functions"] = [func_sig]

        if len(self._llm_config["functions"]) == 0:
            del self._llm_config["functions"]

        self._client = OpenAIWrapper(**self._llm_config)

    def update_tool_signature(self, tool_sig: Union[str, Dict], is_remove: None):
        """update a tool_signature in the LLM configuration for tool_call.

        Args:
            tool_sig (str or dict): description/name of the tool to update/remove to the model. See: https://platform.openai.com/docs/api-reference/chat/create#chat-create-tools
            is_remove: whether removing the tool from llm_config with name 'tool_sig'
        """

        if not self._llm_config:
            error_msg = "To update a tool signature, agent must have an llm_config"
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if is_remove:
            if "tools" not in self._llm_config.keys():
                error_msg = "The agent config doesn't have tool {name}.".format(name=tool_sig)
                logger.error(error_msg)
                raise AssertionError(error_msg)
            else:
                self._llm_config["tools"] = [
                    tool for tool in self._llm_config["tools"] if tool["function"]["name"] != tool_sig
                ]
        else:
            self._assert_valid_name(tool_sig["function"]["name"])
            if "tools" in self._llm_config.keys():
                self._llm_config["tools"] = [
                    tool
                    for tool in self._llm_config["tools"]
                    if tool.get("function", {}).get("name") != tool_sig["function"]["name"]
                ] + [tool_sig]
            else:
                self._llm_config["tools"] = [tool_sig]

        if len(self._llm_config["tools"]) == 0:
            del self._llm_config["tools"]

        self._client = OpenAIWrapper(**self._llm_config)

    def _generate_oai_reply(
        self,
        messages: List[Dict],
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        client = self._client if config is None else config
        if client is None:
            return False, None

        # unroll tool_responses
        all_messages = []
        for message in messages:
            tool_responses = message.get("tool_responses", [])
            if tool_responses:
                all_messages += tool_responses
                # tool role on the parent message means the content is just concatenation of all of the tool_responses
                if message.get("role") != "tool":
                    all_messages.append({key: message[key] for key in message if key != "tool_responses"})
            else:
                all_messages.append(message)

        # TODO: #1143 handle token limit exceeded error
        response = client.create(
            context=messages[-1].pop("context", None),
            messages=self._oai_system_messages + all_messages,
            cache=self._client_cache,
        )

        extracted_response = client.extract_text_or_completion_object(response)[0]

        # ensure function and tool calls will be accepted when sent back to the LLM
        if not isinstance(extracted_response, str):
            extracted_response = model_dump(extracted_response)
        if isinstance(extracted_response, dict):
            if extracted_response.get("function_call"):
                extracted_response["function_call"]["name"] = self._normalize_name(
                    extracted_response["function_call"]["name"]
                )
            for tool_call in extracted_response.get("tool_calls") or []:
                tool_call["function"]["name"] = self._normalize_name(tool_call["function"]["name"])
        return True, extracted_response

    async def _a_generate_oai_reply(
        self,
        messages: List[Dict],
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(self._generate_oai_reply, messages=messages, config=config)
        )

    def print_usage_summary(self, mode: Union[str, List[str]] = ["actual", "total"]) -> None:
        """Print the usage summary."""
        if self._client is None:
            print(f"No cost incurred from agent '{self._name}'.")
        else:
            print(f"Agent '{self._name}':")
            self._client.print_usage_summary(mode)

    def get_actual_usage(self) -> Union[None, Dict[str, int]]:
        """Get the actual usage summary."""
        if self._client is None:
            return None
        else:
            return self._client.actual_usage_summary

    def get_total_usage(self) -> Union[None, Dict[str, int]]:
        """Get the total usage summary."""
        if self._client is None:
            return None
        else:
            return self._client.total_usage_summary

    @staticmethod
    def _normalize_name(name):
        """
        LLMs sometimes ask functions while ignoring their own format requirements, this function should be used to replace invalid characters with "_".

        Prefer _assert_valid_name for validating user configuration or input
        """
        return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]

    @staticmethod
    def _assert_valid_name(name):
        """
        Ensure that configured names are valid, raises ValueError if not.

        For munging LLM responses use _normalize_name to ensure LLM specified names don't break the API.
        """
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
        if len(name) > 64:
            raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
        return name
