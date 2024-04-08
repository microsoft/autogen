from __future__ import annotations

from typing import Any, Dict, MutableMapping, Type

from ..model_client import ModelClient
from .openai_client import OpenAI


class ModelClientFactory:
    def __init__(self, types: MutableMapping[str, Type[ModelClient]]):
        self.types = types

    @classmethod
    def default(cls) -> ModelClientFactory:
        types: Dict[str, Type[ModelClient]] = {
            "openai": OpenAI,
            "azure": OpenAI,
        }
        return cls(types)

    def add(self, api_type: str, type: Type[ModelClient]) -> None:
        self.types[api_type] = type

    def create_from_config(self, config: Dict[str, Any]) -> ModelClient:
        api_type = config.get("api_type", "openai")
        return self.types[api_type].create_from_config(config)


DEFAULT_FACTORY = ModelClientFactory.default()
