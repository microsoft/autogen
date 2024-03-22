from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Type

from autogen.model_client.base import TextModelClient
from autogen.model_client.chain_client import ChainedTextModelClient
from autogen.model_client.openai_client import OpenAITextModelClient

class ModelClientFactory:
    def __init__(self, types: MutableMapping[str, Type[TextModelClient]]):
        self.types = types

    @classmethod
    def default(cls) -> ModelClientFactory:
        types: Dict[str, Type[TextModelClient]] = {
            "openai": OpenAITextModelClient,
            "azure": OpenAITextModelClient,
        }
        return cls(types)

    def add(self, api_type: str, type: Type[TextModelClient]) -> None:
        self.types[api_type] = type

    def create_from_config(self, config: Dict[str, Any]) -> TextModelClient:
        # Chained model client is a special case to support the existing use format
        if "config_list" in config:
            config_copy = config.copy()
            config_copy["factory"] = self
            return ChainedTextModelClient.create_from_config(config_copy)

        api_type = config.get("api_type", "openai")
        return self.types[api_type].create_from_config(config)