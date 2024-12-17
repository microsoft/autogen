# mypy: disable-error-code="no-any-unimported,misc"
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Generator, List, Union, cast

from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai._openai_client import AzureOpenAIChatCompletionClient

from graphrag.query.llm.base import BaseLLM, BaseLLMCallback


class GraphragOpenAiModelAdapter(BaseLLM):
    """
    Adapts an autogen OpenAIChatCompletionClient to a graphrag-compatible LLM interface.
    """

    def __init__(self, client: OpenAIChatCompletionClient | AzureOpenAIChatCompletionClient):
        self._client = client

    @property
    def model_name(self) -> str:
        return self._client._raw_config["model"]  # type: ignore

    def _to_autogen_messages(self, messages: Union[str, List[Any]]) -> List[Any]:
        # Convert graphrag-style input into autogen LLMMessage
        # If it's a single string, assume user message
        if isinstance(messages, str):
            return [UserMessage(content=messages, source="user")]

        # If it's a list, assume a list of dicts { "role": "user|assistant|system", "content": str }
        autogen_messages: List[SystemMessage | UserMessage | AssistantMessage] = []
        for i, m in enumerate(messages):
            if not isinstance(m, dict):
                raise ValueError("Each message must be a dict with keys: role, content")
            message_dict = cast(Dict[str, Any], m)
            role = cast(str, message_dict.get("role"))
            content = cast(str, message_dict.get("content", ""))
            name = cast(str, message_dict.get("name", f"source_{i}"))

            if role == "user":
                autogen_messages.append(UserMessage(content=content, source=name))
            elif role == "system":
                autogen_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                autogen_messages.append(AssistantMessage(content=content, source=name))
            else:
                # Default to user if unknown
                autogen_messages.append(UserMessage(content=content, source=name))

        return autogen_messages

    def generate(
        self,
        messages: Union[str, List[Any]],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        # Synchronous generation (rarely used in graphrag)
        # We'll just run async create
        return asyncio.run(self.agenerate(messages, streaming=streaming, callbacks=callbacks, **kwargs))

    async def agenerate(
        self,
        messages: Union[str, List[Any]],
        streaming: bool = True,
        callbacks: list[BaseLLMCallback] | None = None,
        **kwargs: Any,
    ) -> str:
        autogen_msgs = self._to_autogen_messages(messages)
        result: CreateResult = await self._client.create(autogen_msgs, tools=[])
        if isinstance(result.content, str):
            return result.content
        # If it's function calls or something else, just return a string representation
        return json.dumps(result.content)

    def stream_generate(
        self, messages: Union[str, List[Any]], callbacks: list[BaseLLMCallback] | None = None, **kwargs: Any
    ) -> Generator[str, None, None]:
        # This would be a generator that yields tokens
        # For simplicity, we won't implement streaming here, but it can be done similarly
        raise NotImplementedError("stream_generate not implemented")

    async def astream_generate(
        self, messages: Union[str, List[Any]], callbacks: list[BaseLLMCallback] | None = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        # Async streaming (not implemented here)
        if False:  # This ensures the function has correct return type while still raising NotImplementedError
            yield ""
        raise NotImplementedError("astream_generate not implemented")