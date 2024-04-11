#!/usr/bin/env python3 -m pytest

from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import pytest
from autogen.cache.abstract_cache_base import AbstractCache
from autogen.experimental.model_client import ModelClient, ModelCapabilities
from autogen.experimental.types import Message, CreateResult, FunctionDefinition, RequestUsage
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
async def test_create() -> None:
    class MyClient(ModelClient):
        # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
        async def create(
            self,
            messages: List[Message],
            cache: Optional[AbstractCache] = None,
            functions: List[FunctionDefinition] = [],
            extra_create_args: Dict[str, Any] = {},
        ) -> CreateResult:
            return CreateResult(
                finish_reason="stop",
                content="4",
                cached=False,
                usage=RequestUsage(cost=0, prompt_tokens=1, completion_tokens=1),
            )

        def create_stream(
            self,
            messages: List[Message],
            cache: Optional[AbstractCache] = None,
            functions: List[FunctionDefinition] = [],
            extra_create_args: Dict[str, Any] = {},
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            raise NotImplementedError

        def actual_usage(self) -> RequestUsage:
            raise NotImplementedError

        def total_usage(self) -> RequestUsage:
            raise NotImplementedError

        @property
        def capabilities(self) -> ModelCapabilities:
            raise NotImplementedError

    client = MyClient()

    assert isinstance(client, ModelClient)

    response = await client.create(messages=[])
    assert response.cached is False
    assert response.finish_reason == "stop"
    assert response.content == "4"
