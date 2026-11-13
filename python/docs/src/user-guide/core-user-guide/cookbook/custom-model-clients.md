# Custom Model Clients

AutoGen's model client system is designed for extensibility. While the framework ships with clients for OpenAI, Azure, Anthropic, Ollama, and others, you may need to integrate a model provider that isn't supported out of the box — a proprietary API, a self-hosted model behind a custom gateway, or a local inference engine with a non-standard interface.

This guide walks you through building a custom model client from scratch by implementing the {py:class}`~autogen_core.models.ChatCompletionClient` interface.

## When to Build a Custom Client

A custom model client makes sense when:

- **You use a provider without a built-in client** — e.g., Cohere, AI21, or a proprietary internal API.
- **You run local models** with a custom serving layer (not Ollama or OpenAI-compatible).
- **You need custom preprocessing or postprocessing** — prompt rewriting, response filtering, or logging that doesn't fit `extra_create_args`.
- **You want to wrap a non-chat API** as a chat completion interface (e.g., a classification model or an embedding model with a generation head).
- **You need deterministic or mock responses** for testing agent workflows.

```{note}
If your provider exposes an OpenAI-compatible API (many do), try {py:class}`~autogen_ext.models.openai.OpenAIChatCompletionClient` with a custom `base_url` first. That's often sufficient and requires no custom code.
```

## The ChatCompletionClient Interface

Every model client in AutoGen implements {py:class}`~autogen_core.models.ChatCompletionClient`. Here's what you need to provide:

| Method | Purpose |
|--------|---------|
| `create()` | Send messages to the model and return a `CreateResult` |
| `create_stream()` | Streaming variant that yields string chunks, ending with a `CreateResult` |
| `close()` | Clean up resources (HTTP sessions, connections) |
| `actual_usage()` | Token usage from the last request only |
| `total_usage()` | Cumulative token usage across all requests |
| `count_tokens()` | Estimate token count for a set of messages |
| `remaining_tokens()` | How many tokens are left in the context window |
| `model_info` | A `ModelInfo` dict describing model capabilities |
| `capabilities` | *(Deprecated)* Legacy capabilities dict |

## Step-by-Step Implementation

Let's build a complete custom client. We'll create one that calls a hypothetical REST API, but the pattern applies to any backend.

### Step 1: Define the Class

```python
from __future__ import annotations

import json
from typing import AsyncGenerator, Literal, Mapping, Optional, Sequence, Union

import httpx
from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel


class MyCustomClient(ChatCompletionClient):
    """A custom model client that calls a hypothetical REST API."""

    component_type = "model"
    # component_config_schema is needed for declarative config (optional)

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model_name: str = "my-model",
        max_tokens: int = 4096,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._client = httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
```

### Step 2: Convert Messages to Your API Format

Most of the work in a custom client is translating between AutoGen's message types and your API's format.

```python
    def _to_api_messages(self, messages: Sequence[LLMMessage]) -> list[dict]:
        """Convert AutoGen messages to the API's expected format."""
        api_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                api_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, UserMessage):
                # UserMessage content can be str or list of str/Image
                if isinstance(msg.content, str):
                    api_messages.append({"role": "user", "content": msg.content})
                else:
                    # Handle multimodal content if your API supports it
                    text_parts = [part for part in msg.content if isinstance(part, str)]
                    api_messages.append({"role": "user", "content": " ".join(text_parts)})
            elif isinstance(msg, AssistantMessage):
                if isinstance(msg.content, str):
                    api_messages.append({"role": "assistant", "content": msg.content})
                else:
                    # Function calls — serialize as JSON for APIs that don't
                    # natively support tool calling
                    api_messages.append({
                        "role": "assistant",
                        "content": json.dumps([fc.model_dump() for fc in msg.content]),
                    })
        return api_messages
```

### Step 3: Implement `create()`

This is the core method. Send messages, parse the response, return a `CreateResult`.

```python
    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        # Build the request payload
        payload: dict = {
            "model": self._model_name,
            "messages": self._to_api_messages(messages),
            "max_tokens": self._max_tokens,
            **extra_create_args,
        }

        # Add JSON mode if requested
        if json_output is True:
            payload["response_format"] = {"type": "json_object"}

        # Make the API call
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        # Parse the response — adapt this to your API's response format
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason", "stop")

        # Map finish reasons to AutoGen's expected values
        finish_reason_map = {
            "stop": "stop",
            "length": "length",
            "tool_calls": "function_calls",
            "content_filter": "content_filter",
        }
        mapped_reason = finish_reason_map.get(finish_reason, "unknown")

        # Track token usage
        usage_data = data.get("usage", {})
        self._actual_usage = RequestUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )
        self._total_usage = RequestUsage(
            prompt_tokens=self._total_usage.prompt_tokens + self._actual_usage.prompt_tokens,
            completion_tokens=self._total_usage.completion_tokens + self._actual_usage.completion_tokens,
        )

        return CreateResult(
            finish_reason=mapped_reason,
            content=content,
            usage=self._actual_usage,
            cached=False,
        )
```

### Step 4: Implement `create_stream()`

The streaming method yields string chunks and **must** end with a `CreateResult`.

```python
    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        # If your API doesn't support streaming, fall back to create()
        result = await self.create(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )

        # Yield the full content as a single chunk, then the result
        if isinstance(result.content, str):
            yield result.content
        yield result
```

```{tip}
If your API supports server-sent events (SSE) for streaming, use `httpx` streaming responses and yield chunks as they arrive. The final `CreateResult` should contain the full concatenated content and usage stats.
```

### Step 5: Implement the Remaining Methods

```python
    async def close(self) -> None:
        """Clean up the HTTP client."""
        await self._client.aclose()

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
    ) -> int:
        # Simple estimation: ~4 chars per token (adjust for your model)
        total_chars = sum(
            len(str(msg.content)) if hasattr(msg, "content") else 0
            for msg in messages
        )
        return total_chars // 4

    def remaining_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
    ) -> int:
        return self._max_tokens - self.count_tokens(messages, tools=tools)

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        return {
            "vision": False,
            "function_calling": False,
            "json_output": True,
        }

    @property
    def model_info(self) -> ModelInfo:
        return {
            "vision": False,
            "function_calling": False,
            "json_output": True,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        }
```

## Using Your Custom Client

Once implemented, your client works like any built-in client:

```python
import asyncio
from autogen_core.models import UserMessage

async def main():
    client = MyCustomClient(
        api_url="https://my-model-api.example.com",
        api_key="sk-...",
        model_name="my-custom-model",
    )

    result = await client.create(
        messages=[UserMessage(content="What is the capital of France?", source="user")]
    )
    print(result.content)
    print(f"Tokens used: {result.usage}")

    await client.close()

asyncio.run(main())
```

### With an AssistantAgent

```python
from autogen_agentchat.agents import AssistantAgent

agent = AssistantAgent(
    name="assistant",
    model_client=MyCustomClient(
        api_url="https://my-model-api.example.com",
        api_key="sk-...",
    ),
    system_message="You are a helpful assistant.",
)
```

## Example: A Mock Client for Testing

A common use case is a deterministic client for testing agent logic without making real API calls:

```python
class MockChatCompletionClient(ChatCompletionClient):
    """Returns predetermined responses. Useful for unit testing agents."""

    component_type = "model"

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._call_count = 0
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    async def create(
        self,
        messages: Sequence[LLMMessage],
        **kwargs,
    ) -> CreateResult:
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        self._actual_usage = RequestUsage(prompt_tokens=10, completion_tokens=len(response.split()))
        self._total_usage = RequestUsage(
            prompt_tokens=self._total_usage.prompt_tokens + 10,
            completion_tokens=self._total_usage.completion_tokens + len(response.split()),
        )
        return CreateResult(
            finish_reason="stop",
            content=response,
            usage=self._actual_usage,
            cached=False,
        )

    async def create_stream(self, messages, **kwargs):
        result = await self.create(messages, **kwargs)
        if isinstance(result.content, str):
            yield result.content
        yield result

    async def close(self) -> None:
        pass

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages, **kwargs) -> int:
        return sum(len(str(getattr(m, "content", ""))) // 4 for m in messages)

    def remaining_tokens(self, messages, **kwargs) -> int:
        return 4096 - self.count_tokens(messages)

    @property
    def capabilities(self):
        return {"vision": False, "function_calling": False, "json_output": False}

    @property
    def model_info(self) -> ModelInfo:
        return {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        }
```

Usage in tests:

```python
async def test_agent_workflow():
    mock_client = MockChatCompletionClient(
        responses=[
            "I'll analyze that for you.",
            "Based on my analysis, the answer is 42.",
            "TERMINATE",
        ]
    )
    agent = AssistantAgent(name="test_agent", model_client=mock_client)
    # ... run your agent workflow with deterministic responses
```

## Adding Tool/Function Calling Support

If your model supports function calling, you need to:

1. Convert `tools` parameter to your API's format in `create()`.
2. Parse tool call responses into {py:class}`~autogen_core.FunctionCall` objects.
3. Set `model_info["function_calling"] = True`.
4. Return `finish_reason="function_calls"` when the model requests tool use.

```python
from autogen_core import FunctionCall

# In your create() method, when parsing a tool call response:
function_calls = [
    FunctionCall(
        id=tool_call["id"],
        name=tool_call["function"]["name"],
        arguments=tool_call["function"]["arguments"],
    )
    for tool_call in response_tool_calls
]

return CreateResult(
    finish_reason="function_calls",
    content=function_calls,
    usage=self._actual_usage,
    cached=False,
)
```

## Tips and Best Practices

- **Start simple.** Get `create()` working with plain text first, then add streaming, tool calling, and vision support incrementally.
- **Handle errors gracefully.** Wrap API calls in try/except and raise meaningful errors. AutoGen agents will propagate exceptions.
- **Token counting matters.** Agents use `remaining_tokens()` to manage context windows. A rough estimate is fine, but don't return `float('inf')` — it defeats context management.
- **Test with real agents.** Use {py:class}`~autogen_agentchat.agents.AssistantAgent` to validate your client handles multi-turn conversations correctly.
- **Look at existing implementations.** The {py:class}`~autogen_ext.models.ollama.OllamaChatCompletionClient` is a good reference for a relatively simple but complete implementation.

## Further Reading

- {py:class}`~autogen_core.models.ChatCompletionClient` — the full protocol definition
- {py:class}`~autogen_core.models.CreateResult` — the return type for model completions
- {doc}`model-clients` — overview of built-in model clients
- {doc}`../cookbook/local-llms-ollama-litellm` — using local models with existing clients
