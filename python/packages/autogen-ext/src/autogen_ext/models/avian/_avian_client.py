"""Avian model client for AutoGen.

Avian (https://avian.io) provides an OpenAI-compatible LLM inference API
with access to models like DeepSeek-V3.2, Kimi-K2.5, GLM-5, and MiniMax-M2.5.

This client wraps the OpenAI Python SDK and targets the Avian API endpoint,
implementing the AutoGen ``ChatCompletionClient`` interface.
"""

import os
import warnings
from typing import Any, Dict, Optional, Union, cast

from autogen_core import Component
from autogen_core.models import (
    ModelCapabilities,  # type: ignore
    ModelFamily,
    ModelInfo,
    validate_model_info,
)
from openai import AsyncOpenAI
from pydantic import SecretStr
from typing_extensions import Self, Unpack

from ..openai._openai_client import (
    BaseOpenAIChatCompletionClient,
    _create_args_from_config,
)
from . import _model_info
from .config import AvianClientConfiguration, AvianClientConfigurationConfigModel

AVIAN_BASE_URL = "https://api.avian.io/v1"


def _avian_client_from_config(config: Dict[str, Any]) -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for the Avian API."""
    return AsyncOpenAI(
        api_key=config.get("api_key", os.environ.get("AVIAN_API_KEY", "")),
        base_url=config.get("base_url", AVIAN_BASE_URL),
        timeout=config.get("timeout"),
        max_retries=config.get("max_retries", 2),
    )


class AvianChatCompletionClient(BaseOpenAIChatCompletionClient, Component[AvianClientConfigurationConfigModel]):
    """Chat completion client for models hosted on Avian (https://avian.io).

    Avian provides an OpenAI-compatible API for LLM inference. This client
    handles authentication and model configuration automatically.

    To use this client, you must install the ``openai`` extra:

    .. code-block:: bash

        pip install "autogen-ext[openai]"

    You will also need an Avian API key. Set it via the ``AVIAN_API_KEY``
    environment variable or pass it directly as the ``api_key`` parameter.

    Args:
        model (str): The Avian model identifier. Supported models:
            ``deepseek/deepseek-v3.2``, ``moonshotai/kimi-k2.5``,
            ``z-ai/glm-5``, ``minimax/minimax-m2.5``.
        api_key (optional, str): The Avian API key. If not provided,
            the ``AVIAN_API_KEY`` environment variable is used.
        base_url (optional, str): Override the API base URL.
            Defaults to ``https://api.avian.io/v1``.
        timeout (optional, float): Request timeout in seconds.
        max_retries (optional, int): Maximum number of retries. Defaults to 2.
        model_info (optional, ModelInfo): Override model capabilities.
            Auto-detected for known Avian models.
        temperature (optional, float): Sampling temperature (0.0 - 2.0).
        max_tokens (optional, int): Maximum tokens to generate.
        top_p (optional, float): Nucleus sampling parameter.
        frequency_penalty (optional, float): Frequency penalty (-2.0 to 2.0).
        presence_penalty (optional, float): Presence penalty (-2.0 to 2.0).
        seed (optional, int): Random seed for reproducibility.
        stop (optional, str | list[str]): Stop sequences.

    Examples:

        Basic usage with an Avian model:

        .. code-block:: python

            from autogen_ext.models.avian import AvianChatCompletionClient
            from autogen_core.models import UserMessage

            client = AvianChatCompletionClient(
                model="deepseek/deepseek-v3.2",
                # api_key="...",  # or set AVIAN_API_KEY env var
            )

            result = await client.create([UserMessage(content="Hello!", source="user")])
            print(result)

        Using with AutoGen agents:

        .. code-block:: python

            from autogen_agentchat.agents import AssistantAgent
            from autogen_ext.models.avian import AvianChatCompletionClient

            model_client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
            agent = AssistantAgent("assistant", model_client=model_client)

        Streaming usage:

        .. code-block:: python

            import asyncio
            from autogen_core.models import UserMessage
            from autogen_ext.models.avian import AvianChatCompletionClient


            async def main() -> None:
                client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")

                messages = [UserMessage(content="Write a haiku about code.", source="user")]
                stream = client.create_stream(messages=messages)

                async for response in stream:
                    if isinstance(response, str):
                        print(response, flush=True, end="")
                    else:
                        print("\\n---")
                        print(response.content)

                await client.close()


            asyncio.run(main())

        Loading from a configuration dictionary:

        .. code-block:: python

            from autogen_core.models import ChatCompletionClient

            config = {
                "provider": "autogen_ext.models.avian.AvianChatCompletionClient",
                "config": {
                    "model": "deepseek/deepseek-v3.2",
                    "api_key": "your-avian-api-key",
                },
            }
            client = ChatCompletionClient.load_component(config)

    """

    component_type = "model"
    component_config_schema = AvianClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.avian.AvianChatCompletionClient"

    def __init__(self, **kwargs: Unpack[AvianClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for AvianChatCompletionClient")

        model_capabilities: Optional[ModelCapabilities] = None  # type: ignore
        self._raw_config: Dict[str, Any] = dict(kwargs).copy()
        copied_args = dict(kwargs).copy()

        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        # If no model_info provided, try to auto-detect from known Avian models.
        if model_info is None and model_capabilities is None:
            try:
                model_info = _model_info.get_info(kwargs["model"])
            except KeyError:
                # Unknown model -- user must provide model_info.
                raise ValueError(
                    f"Unknown Avian model: {kwargs['model']}. "
                    "Please provide model_info for custom or new models. "
                    f"Known models: {list(_model_info._MODEL_INFO.keys())}"
                )

        # Ensure base_url defaults to Avian.
        if "base_url" not in copied_args:
            copied_args["base_url"] = AVIAN_BASE_URL

        # Ensure api_key is set from env if not provided.
        if "api_key" not in copied_args:
            api_key = os.environ.get("AVIAN_API_KEY")
            if not api_key:
                raise ValueError(
                    "api_key is required for AvianChatCompletionClient. "
                    "Pass it as a parameter or set the AVIAN_API_KEY environment variable."
                )
            copied_args["api_key"] = api_key
            self._raw_config["api_key"] = api_key

        client = _avian_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)

        super().__init__(
            client=client,
            create_args=create_args,
            model_capabilities=model_capabilities,
            model_info=model_info,
        )

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _avian_client_from_config(state["_raw_config"])

    def _to_config(self) -> AvianClientConfigurationConfigModel:
        copied_config = self._raw_config.copy()
        return AvianClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: AvianClientConfigurationConfigModel) -> Self:
        copied_config = config.model_copy().model_dump(exclude_none=True)

        # Handle api_key as SecretStr.
        if "api_key" in copied_config and isinstance(config.api_key, SecretStr):
            copied_config["api_key"] = config.api_key.get_secret_value()

        return cls(**copied_config)

    def count_tokens(self, messages: Any, *, tools: Any = []) -> int:
        """Count tokens in the messages.

        Uses the OpenAI token counting logic from the base class with
        cl100k_base encoding as a reasonable approximation.
        """
        from ..openai._openai_client import count_tokens_openai

        return count_tokens_openai(
            messages,
            self._create_args["model"],
            add_name_prefixes=self._add_name_prefixes,
            tools=tools,
            model_family=self._model_info["family"],
            include_name_in_message=self._include_name_in_message,
        )

    def remaining_tokens(self, messages: Any, *, tools: Any = []) -> int:
        """Return the number of remaining tokens before hitting the context limit."""
        token_limit = _model_info.get_token_limit(self._create_args["model"])
        return token_limit - self.count_tokens(messages, tools=tools)
