import asyncio
import json
from typing import Any, List, Optional, Union

from graphrag.query.llm.base import BaseLLM

from autogen_ext.models.openai._openai_client import (
    AssistantMessage,
    CreateResult,
    OpenAIChatCompletionClient,
    SystemMessage,
    UserMessage,
)


class GraphragOpenAiModelAdapter(BaseLLM):
    """
    Adapts an autogen OpenAIChatCompletionClient to a graphrag-compatible LLM interface.
    """

    def __init__(self, client: OpenAIChatCompletionClient):
        self._client = client

    def _to_autogen_messages(self, messages: Union[str, List[Any]]) -> List[Any]:
        # Convert graphrag-style input into autogen LLMMessage
        # If it's a single string, assume user message
        if isinstance(messages, str):
            return [UserMessage(content=messages, source="user")]

        # If it's a list, assume a list of dicts { "role": "user|assistant|system", "content": str }
        autogen_messages = []
        for i, m in enumerate(messages):
            if not isinstance(m, dict):
                raise ValueError("Each message must be a dict with keys: role, content")
            role = m.get("role")
            content = m.get("content", "")
            name = m.get("name", f"source_{i}")

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

    def generate(self, messages: Union[str, List[Any]], streaming: bool = True, callbacks=None, **kwargs) -> str:
        # Synchronous generation (rarely used in graphrag)
        # We'll just run async create
        return asyncio.run(self.agenerate(messages, streaming=streaming, callbacks=callbacks, **kwargs))

    async def agenerate(self, messages: Union[str, List[Any]], streaming: bool = True, callbacks=None, **kwargs) -> str:
        autogen_msgs = self._to_autogen_messages(messages)
        result: CreateResult = await self._client.create(autogen_msgs, tools=[])
        if isinstance(result.content, str):
            return result.content
        # If it's function calls or something else, just return a string representation
        return json.dumps(result.content)

    def stream_generate(self, messages: Union[str, List[Any]], callbacks=None, **kwargs) -> Any:
        # This would be a generator that yields tokens
        # For simplicity, we won't implement streaming here, but it can be done similarly
        raise NotImplementedError("stream_generate not implemented")

    async def astream_generate(self, messages: Union[str, List[Any]], callbacks=None, **kwargs) -> Any:
        # Async streaming (not implemented here)
        raise NotImplementedError("astream_generate not implemented")
