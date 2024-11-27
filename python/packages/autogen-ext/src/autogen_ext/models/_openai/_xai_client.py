#!/usr/bin/env python3

from typing import Any, Dict, Mapping, Optional, Set
from autogen_core.components.models import ModelCapabilities
from .config import XAIClientConfiguration
from openai import AsyncOpenAI
from typing_extensions import Unpack
from ._openai_client import (
    BaseOpenAIChatCompletionClient,
    openai_init_kwargs,
    create_kwargs,
)

# Only single choice allowed
disallowed_create_args = set(["stream", "messages", "function_call", "functions", "n"])
required_create_args: Set[str] = set(["model"])


def _openai_client_from_config(config: Mapping[str, Any]) -> AsyncOpenAI:
    openai_config = {k: v for k, v in config.items() if k in openai_init_kwargs}
    return AsyncOpenAI(**openai_config)


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    create_args = {k: v for k, v in config.items() if k in create_kwargs}
    create_args_keys = set(create_args.keys())
    if not required_create_args.issubset(create_args_keys):
        raise ValueError(
            f"Required create args are missing: {required_create_args - create_args_keys}"
        )
    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(
            f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}"
        )
    return create_args


class XAIChatCompletionClient(BaseOpenAIChatCompletionClient):
    """Chat completion client for xAI hosted models."""

    def __init__(self, **kwargs: Unpack[XAIClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for XAIChatCompletionClient.")

        model_capabilities: Optional[ModelCapabilities] = None
        copied_args = dict(kwargs).copy()

        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        client = _openai_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)
        self._raw_config = copied_args

        super().__init__(
            client=client,
            create_args=create_args,
            model_capabilities=model_capabilities,
        )
