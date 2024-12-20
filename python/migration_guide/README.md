# Migration Guide for v0.2 to v0.4

This is a migration guide for users of the `v0.2.*` versions of `autogen-agentchat`
to the `v0.4` version, which introduces a new set of APIs and features.

> **Note**: The `v0.4` version contains breaking changes. Please read this guide carefully.
We will still maintain the `v0.2` version in the `0.2` branch, however, 
we highly recommend you to upgrade to the `v0.4` version.

## What's in this guide?

We provide a detailed guide on how to migrate your existing codebase from `v0.2` to `v0.4`.

See each feature below for detailed information on how to migrate.

- [Model Client](#model-client)
- [Model Client for OpenAI-Compatible APIs](#model-client-for-openai-compatible-apis)
- [Assistant Agent](#assistant-agent)
- [Multi-Modal Agent](#multi-modal-agent)
- [User Proxy](#user-proxy)
- [Custom Agent and Register Reply](#custom-agent-and-register-reply)
- [Two-Agent Chat](#two-agent-chat)
- [Tool Use](#tool-use)
- [Group Chat](#group-chat)
- [Group Chat with Custom Selector (Stateflow)](#group-chat-with-custom-selector-stateflow)
- [Nested Chat](#nested-chat)
- [Sequential Chat](#sequential-chat)
- [GPTAssistantAgent](#gptassistantagent)
- [Long-Context Handling](#long-context-handling)
- [Observability](#observability)
- [Code Executors](#code-executors)

The following features currently in `v0.2`
will be providied in the future releases of `v0.4.*` versions:

- Model Client Cache
- Teacheable Agent
- RAG Agent

## Model Client

In `v0.2` you configure the model client as follows, and create the `OpenAIWrapper` object.

```python
from autogen.oai import OpenAIWrapper

config_list = [
    {"model": "gpt-4o", "api_key": "sk-xxx"},
    {"model": "gpt-4o-mini", "api_key": "sk-xxx"},
]

model_client = OpenAIWrapper(config_list=config_list)
```

In `v0.4`, we offers two ways to create a model client.

### Use component config

TODO: add example

```python
```

### Use model client class directly

Open AI:

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key="sk-xxx")
```

Azure OpenAI:

```python
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="gpt-4o",
    azure_endpoint="https://<your-endpoint>.openai.azure.com/",
    model="gpt-4o",
    api_version="2024-09-01-preview",
    api_key="sk-xxx",
)
```

Read more on [OpenAI Chat Completion Client Docs](https://microsoft.github.io/autogen/dev/reference/python/autogen_ext.models.openai.html)

## Model Client for OpenAI-Compatible APIs

You can use a the `OpenAIChatCompletionClient` to connect to an OpenAI-Compatible API,
but you need to specify the `base_url` and `model_capabilities`.

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

custom_model_client = OpenAIChatCompletionClient(
    model="custom-model-name",
    base_url="https://custom-model.com/reset/of/the/path",
    api_key="placeholder",
    model_capabilities={
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
)
```

> **Note**: We don't test all the OpenAI-Compatible APIs, and many of them
> works differently from the OpenAI API even though they may claim to suppor it.
> Please test them before using them.

Read about [Model Clients](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/models.html)
in AgentChat Tutorial and more detailed information on [Core API Docs](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/model-clients.html)

Support for other hosted models will be added in the future.

## Assistant Agent

In `v0.2`, you create an assistant agent as follows:

```python
from autogen.agentchat import AssistantAgent

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": "sk-xxx"}],
    "seed": 42,
    "temperature": 0,
}

assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config=llm_config,
)
```

In `v0.4`, it is similar, but you need to specify `model_client` instead of `llm_config`.

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key="sk-xxx", seed=42, temperature=0)

assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    model_client=model_client,
)
```

However, the usage is somewhat different. In `v0.4`, instead of calling `assistant.send`,
you call `assistant.on_messages` or `assistant.on_messages_stream` to handle incoming messages.
Furthermore, the `on_messages` and `on_messages_stream` methods are asynchronous,
and the latter returns an async generator to stream the inner thoughts of the agent.

Here is how you can call the assistant agent in `v0.4` directly, continuing from the above example:

```python
import asyncio
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant.",
        model_client=model_client,
    )

    cancellation_token = CancellationToken()
    response = await assistant.on_messages([TextMessage(content="Hello!", source="user")], cancellation_token)
    print(response)

asyncio.run(main())
```

The `CancellationToken` can be used to cancel the request asynchronously
when you call `cancellation_token.cancel()`, which will cause the `await`
on the `on_messages` call to raise a `CancelledError`.

Read more on [Assistant Agent Docs](https://microsoft.github.io/autogen/dev/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.AssistantAgent).


## Multi-Modal Agent

The `AssistantAgent` in `v0.4` supports multi-modal inputs if the model client supports it.
The `vision` capability of the model client is used to determine if the agent supports multi-modal inputs.

```python
import asyncio
from pathlib import Path
from autogen_agentchat.messages import MultiModalMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken, Image
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant.",
        model_client=model_client,
    )

    cancellation_token = CancellationToken()
    message = MultiModalMessage(
        content=["Here is an image:", Image.from_file(Path("test.png"))],
        source="user",
    )
    response = await assistant.on_messages([message], cancellation_token)
    print(response)

asyncio.run(main())
```

## User Proxy

## Custom Agent and Register Reply

## Two-Agent Chat

## Tool Use

## Group Chat

## Group Chat with Custom Selector (Stateflow)

## Nested Chat

## Sequential Chat

## GPTAssistantAgent

## Long-Context Handling

## Observability

## Code Executors
