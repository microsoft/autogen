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
- [Group Chat with Resume](#group-chat-with-resume)
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

In `v0.2`, you create a user proxy as follows:

```python
from autogen.agentchat import UserProxyAgent

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config=False,
    llm_config=False,
)
```

This user proxy would take input from the user through console, and would terminate
if the incoming message ends with "TERMINATE".

In `v0.4`, a user proxy is simply an agent that takes user input only, there is no
other special configuration needed. You can create a user proxy as follows:

```python
from autogen_agentchat.agents import UserProxyAgent

user_proxy = UserProxyAgent("user_proxy")
```

See [User Proxy Agent Docs](https://microsoft.github.io/autogen/dev/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.UserProxyAgent)
for more details and how to customize the input function with timeout.

## Conversable Agent and Register Reply

In `v0.2`, you can create a conversable agent and register a reply function as follows:

```python
from typing import Any, Dict, List, Optional, Tuple, Union
from autogen.agentchat import ConversableAgent

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": "sk-xxx"}],
    "seed": 42,
    "temperature": 0,
}

conversable_agent = ConversableAgent(
    name="conversable_agent",
    system_message="You are a helpful assistant.",
    llm_config=llm_config,
    code_execution_config={"work_dir": "coding"},
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
)

def reply_func(
    recipient: ConversableAgent, 
    messages: Optional[List[Dict]] = None, 
    sender: Optional[Agent] = None, 
    config: Optional[Any] = None,
) -> Tuple[bool, Union[str, Dict, None]]:
    # Custom reply logic here
    return True, "Custom reply"

# Register the reply function
conversable_agent.register_reply([ConversableAgent], reply_func, position=0)

# NOTE: An async reply function will only be invoked with async send.
```

Rather than guessing what the `reply_func` does, all its parameters, 
and what the `position` should be, in `v0.4`, we can simply create a custom agent
and implement the `on_messages` method.

```python
from typing import Sequence
from autogen_core import CancellationToken
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import Response

class CustomAgent(BaseChatAgent):
    async def on_messages(self, messages: Sequence[TextMessage], cancellation_token: CancellationToken) -> Response:
        # Custom reply logic here
        return Response(chat_message=TextMessage(content="Custom reply", source=self.name))
```

You can then use the custom agent in the same way as the `AssistantAgent`.

## Two-Agent Chat

In `v0.2`, you can create a two-agent chat for code execution as follows:

```python
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.agentchat import AssistantAgent, UserProxyAgent

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": "sk-xxx"}],
    "seed": 42,
    "temperature": 0,
}

assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant. Write all code in python. Reply only 'TERMINATE' if the task is done.",
    llm_config=llm_config,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={"code_executor": LocalCommandLineCodeExecutor(work_dir="coding")},
    llm_config=False,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
)

chat_result = user_proxy.initiate_chat(assistant, message="Write a python script to print 'Hello, world!'")
# Intermediate messages are printed to the console directly.
print(chat_result)
```

To get the same behavior in `v0.4`, you can use the `AssistantAgent` 
and `CodeExecutorAgent` together in a `RoundRobinGroupChat`.

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant. Write all code in python. Reply only 'TERMINATE' if the task is done.",
        model_client=model_client,
    )

    code_executor = CodeExecutorAgent(
        name="code_executor",
        code_executor=LocalCommandLineCodeExecutor(work_dir="coding"),
    )

    # The termination condition is a combination of text termination and max message termination, either of which will cause the chat to terminate.
    termination = TextTermination("TERMINATE") | MaxMessageTermination(10)

    # The group chat will alternate between the assistant and the code executor.
    group_chat = RoundRobinGroupChat([assistant, code_executor], termination_condition=termination)

    # `run_stream` returns an async generator to stream the intermediate messages.
    stream = group_chat.run_stream(task="Write a python script to print 'Hello, world!'")
    # `Console` is a simple UI to display the stream.
    await Console(stream)

asyncio.run(main())
```

## Tool Use

In `v0.2`, to create a tool use chatbot, you must have two agents, one for calling the tool and one for executing the tool.
You need to initiate a two-agent chat for every user request.

```python
from autogen.agentchat import AssistantAgent, UserProxyAgent, register_function

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": "sk-xxx"}],
    "seed": 42,
    "temperature": 0,
}

tool_caller = AssistantAgent(
    name="tool_caller",
    system_message="You are a helpful assistant. You can call tools to help user.",
    llm_config=llm_config,
)

tool_executor = UserProxyAgent(
    name="tool_executor",
    human_input_mode="NEVER",
    code_execution_config=False,
    max_consecutive_auto_reply=1, # Only one or a batch of tool calls at a time.
    llm_config=False,
)

def get_weather(city: str) -> str:
    return f"The weather in {city} is 72 degree and sunny."

# Register the tool function to the tool caller and executor.
register_function(get_weather, caller=tool_caller, executor=tool_executor)

chat_result = tool_executor.initiate_chat(
    tool_caller, 
    message="What's the weather in Seattle?",
    summary_method="reflection_with_llm", # To let the model reflect on the tool use, set to "last_msg" to return the tool call result directly.
)
print(chat_result)
```

In `v0.4`, you really just need one agent -- the `AssistantAgent` -- to handle 
both the tool calling and tool execution.

```python
import asyncio
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent

def get_weather(city: str) -> str: # Async tool is possible too.
    return f"The weather in {city} is 72 degree and sunny."

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)
    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant. You can call tools to help user.",
        model_client=model_client,
        tools=[get_weather],
        reflect_on_tool_use=False, # Set to True to have the model reflect on the tool use.
    )
    response = await assistant.on_messages([TextMessage(content="What's the weather in Seattle?", source="user")], CancellationToken())
    print(response)

asyncio.run(main())
```

## Group Chat

## Group Chat with Resume

## Group Chat with Custom Selector (Stateflow)

## Nested Chat

## Sequential Chat

## GPTAssistantAgent

## Long-Context Handling

## Observability

## Code Executors
