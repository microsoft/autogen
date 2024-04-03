from __future__ import annotations

from typing import Any, Dict, MutableMapping, Type

from .base import ChatModelClient
from .openai_client import OpenAIChatModelClient


class ModelClientFactory:
    def __init__(self, types: MutableMapping[str, Type[ChatModelClient]]):
        self.types = types

    @classmethod
    def default(cls) -> ModelClientFactory:
        types: Dict[str, Type[ChatModelClient]] = {
            "openai": OpenAIChatModelClient,
            "azure": OpenAIChatModelClient,
        }
        return cls(types)

    def add(self, api_type: str, type: Type[ChatModelClient]) -> None:
        self.types[api_type] = type

    def create_from_config(self, config: Dict[str, Any]) -> ChatModelClient:
        from .chain_client import ChainedChatModelClient

        # Chained model client is a special case to support the existing use format
        if "config_list" in config:
            config_copy = config.copy()
            config_copy["factory"] = self
            return ChainedChatModelClient.create_from_config(config_copy)

        api_type = config.get("api_type", "openai")
        return self.types[api_type].create_from_config(config)


DEFAULT_FACTORY = ModelClientFactory.default()
