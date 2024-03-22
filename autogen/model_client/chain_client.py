from typing import Any, Dict, List
from openai import APIError, APITimeoutError

from autogen.cache.cache import Cache
from autogen.model_client.base import TextModelClient
from autogen.model_client.factory import ModelClientFactory
from .types import ChatMessage, CreateResponse

class ChainedTextModelClient(TextModelClient):
    def __init__(self, clients: List[TextModelClient]) -> None:
        self._clients = clients

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> TextModelClient:
        config_list = config.pop("config_list", None)
        factory = config.pop("factory", None)
        if not isinstance(factory, ModelClientFactory):
            raise ValueError("factory must be a ModelClientFactory")

        if factory is None:
            factory = ModelClientFactory.default()

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

    async def create(self, messages: List[ChatMessage], cache: Cache, extra_create_args: Dict[str, Any]) -> CreateResponse:
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

