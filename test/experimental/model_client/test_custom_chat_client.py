#!/usr/bin/env python3 -m pytest

from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import pytest
from autogen.cache.abstract_cache_base import AbstractCache
from autogen.experimental.model_client.base import ChatModelClient
from autogen.experimental.model_client.factory import ModelClientFactory
from autogen.experimental.types import ChatMessage, CreateResponse, RequestUsage, ToolCall
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402


@pytest.mark.asyncio
async def test_create() -> None:
    class MyClient(ChatModelClient):
        @classmethod
        def create_from_config(cls, config: Dict[str, Any]) -> ChatModelClient:
            assert config["config_var"] == "value1"
            return cls()

        # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
        async def create(
            self,
            messages: List[ChatMessage],
            cache: Optional[AbstractCache] = None,
            extra_create_args: Dict[str, Any] = {},
        ) -> CreateResponse:
            return CreateResponse(
                finish_reason="stop",
                content="4",
                cached=False,
                usage=RequestUsage(prompt_tokens=1, completion_tokens=1),
            )

        def create_stream(
            self,
            messages: List[ChatMessage],
            cache: Optional[AbstractCache] = None,
            extra_create_args: Dict[str, Any] = {},
        ) -> AsyncGenerator[Union[Union[str, CreateResponse]], None]:
            raise NotImplementedError

        def actual_usage(self) -> RequestUsage:
            raise NotImplementedError

        def total_usage(self) -> RequestUsage:
            raise NotImplementedError

    factory = ModelClientFactory.default()
    factory.add("my_api", MyClient)

    client = factory.create_from_config({"api_type": "my_api", "config_var": "value1"})

    assert isinstance(client, MyClient)

    response = await client.create(messages=[])
    assert response["cached"] is False
    assert response["finish_reason"] == "stop"
    assert response["content"] == "4"
