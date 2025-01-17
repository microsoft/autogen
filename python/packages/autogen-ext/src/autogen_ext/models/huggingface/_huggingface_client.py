import requests
from typing import Any, AsyncGenerator, Dict, Mapping, Optional, Sequence, Union

from autogen_core import Component, CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,
    ModelFamily,
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel
from typing_extensions import Self, Unpack
import logging
import json

logger = logging.getLogger(__name__)

class HuggingFaceClientConfiguration(BaseModel):
    model: str
    huggingface_endpoint: str
    api_key: str

class HuggingFaceChatCompletionClient(ChatCompletionClient, Component[HuggingFaceClientConfiguration]):
    component_type = "model"
    component_config_schema = HuggingFaceClientConfiguration
    component_provider_override = "autogen_ext.models.huggingface.HuggingFaceChatCompletionClient"

    def __init__(self, **kwargs: Unpack[HuggingFaceClientConfiguration]):
        self._model = kwargs["model"]
        self._endpoint = kwargs["huggingface_endpoint"]
        self._api_key = kwargs["api_key"]
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._model_info = ModelInfo(
            vision=False,
            function_calling=False,
            json_output=True,
            family=ModelFamily.LLAMA,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [message.content for message in messages],
            "parameters": extra_create_args,
        }
        logger.debug(f"Sending request to Hugging Face API: {self._endpoint}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

        response = requests.post(self._endpoint, headers=headers, json=payload)
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response content: {response.content}")

        if response.status_code != 200:
            logger.error(f"Error response from Hugging Face API: {response.content}")

        response.raise_for_status()
        result = response.json()

        usage = RequestUsage(
            prompt_tokens=len(payload["inputs"]),
            completion_tokens=len(result["generated_text"]),
        )

        self._total_usage = self._add_usage(self._total_usage, usage)
        self._actual_usage = self._add_usage(self._actual_usage, usage)

        return CreateResult(
            finish_reason="stop",
            content=result["generated_text"],
            usage=usage,
            cached=False,
        )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        raise NotImplementedError("Streaming is not supported for HuggingFaceChatCompletionClient")

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return sum(len(message.content) for message in messages)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        token_limit = 4096  # Assuming a token limit for the model
        return token_limit - self.count_tokens(messages, tools=tools)

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._model_info

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    def _to_config(self) -> HuggingFaceClientConfiguration:
        return HuggingFaceClientConfiguration(
            model=self._model,
            huggingface_endpoint=self._endpoint,
            api_key=self._api_key,
        )

    @classmethod
    def _from_config(cls, config: HuggingFaceClientConfiguration) -> Self:
        return cls(**config.dict())
