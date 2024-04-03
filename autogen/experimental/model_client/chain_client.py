from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from openai import APIError, APITimeoutError

from autogen.cache import AbstractCache
from .base import ChatModelClient
from .factory import ModelClientFactory
from ..types import ChatMessage, CreateResponse, RequestUsage, ToolCall


class ChainedChatModelClient(ChatModelClient):
    def __init__(self, clients: List[ChatModelClient]) -> None:
        self._clients = clients

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatModelClient:
        config_list = config.pop("config_list", None)
        factory = config.pop("factory", None)
        if factory is None:
            factory = ModelClientFactory.default()

        if not isinstance(factory, ModelClientFactory):
            raise ValueError("factory must be a ModelClientFactory")

        if config_list is None:
            # There is no list, so no chaining. Just return a single client
            return factory.create_from_config(config)

        # Merge the base config into each list, overwriting if there are conflicts
        clients = []
        for individual_config in config_list:
            base_config = config.copy()
            base_config.update(individual_config)
            clients.append(factory.create_from_config(base_config))

        return cls(clients)

    async def create(
        self, messages: List[ChatMessage], cache: Optional[AbstractCache] = None, extra_create_args: Dict[str, Any] = {}
    ) -> CreateResponse:
        last = len(self._clients) - 1
        for i, client in enumerate(self._clients):
            try:
                return await client.create(messages, cache, extra_create_args)
            except APITimeoutError as err:
                # logger.debug(f"config {i} timed out", exc_info=True)
                if i == last:
                    raise TimeoutError(
                        "OpenAI API call timed out. This could be due to congestion or too small a timeout value. The timeout can be specified by setting the 'timeout' value (in seconds) in the llm_config (if you are using agents) or the OpenAIWrapper constructor (if you are using the OpenAIWrapper directly)."
                    ) from err
            except APIError as err:
                error_code = getattr(err, "code", None)

                if error_code == "content_filter":
                    # raise the error for content_filter
                    raise
                # logger.debug(f"config {i} failed", exc_info=True)
                if i == last:
                    raise
        else:
            raise ValueError("No clients found")

    def create_stream(
        self, messages: List[ChatMessage], cache: Optional[AbstractCache] = None, extra_create_args: Dict[str, Any] = {}
    ) -> AsyncGenerator[Union[Union[str, ToolCall, CreateResponse]], None]:
        last = len(self._clients) - 1
        for i, client in enumerate(self._clients):
            try:
                return client.create_stream(messages, cache, extra_create_args)
            except APITimeoutError as err:
                # logger.debug(f"config {i} timed out", exc_info=True)
                if i == last:
                    raise TimeoutError(
                        "OpenAI API call timed out. This could be due to congestion or too small a timeout value. The timeout can be specified by setting the 'timeout' value (in seconds) in the llm_config (if you are using agents) or the OpenAIWrapper constructor (if you are using the OpenAIWrapper directly)."
                    ) from err
            except APIError as err:
                error_code = getattr(err, "code", None)

                if error_code == "content_filter":
                    # raise the error for content_filter
                    raise
                # logger.debug(f"config {i} failed", exc_info=True)
                if i == last:
                    raise
        else:
            raise ValueError("No clients found")

    def actual_usage(self) -> RequestUsage:
        result = RequestUsage(prompt_tokens=0, completion_tokens=0)
        for client in self._clients:
            usage = client.actual_usage()
            result["prompt_tokens"] += usage["prompt_tokens"]
            result["completion_tokens"] += usage["completion_tokens"]
            if "cost" in usage:
                result["cost"] = result.get("cost", 0) + usage["cost"]
        return result

    def total_usage(self) -> RequestUsage:
        result = RequestUsage(prompt_tokens=0, completion_tokens=0)
        for client in self._clients:
            usage = client.total_usage()
            result["prompt_tokens"] += usage["prompt_tokens"]
            result["completion_tokens"] += usage["completion_tokens"]
            if "cost" in usage:
                result["cost"] = result.get("cost", 0) + usage["cost"]
        return result
