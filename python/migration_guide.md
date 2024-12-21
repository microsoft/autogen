# Migration Guide for v0.2 to v0.4
This is a migration guide for users of the `v0.2.*` versions of `autogen-agentchat`
to the `v0.4` version, which introduces a new set of APIs and features.
The `v0.4` version contains breaking changes. Please read this guide carefully.
We still maintain the `v0.2` version in the `0.2` branch; however, 
we highly recommend you upgrade to the `v0.4` version.

> **Note**: We no longer have admin access to the `pyautogen` PyPI package, and
> the releases from that package are no longer from Microsoft since version 0.2.34.
> To continue use the `v0.2` version of AutoGen, install it using `autogen-agentchat~=0.2`.
> Please read our [clarification statement](https://github.com/microsoft/autogen/discussions/4217) regarding forks.

## What is `v0.4`?

Since the release of AutoGen in 2023, we have intensively listened to our community and users from small startups and large enterprises, gathering much feedback. Based on that feedback, we built AutoGen `v0.4`, a from-the-ground-up rewrite adopting an asynchronous, event-driven architecture to address issues such as observability, flexibility, interactive control, and scale.

The `v0.4` API is layered:
the [Core API](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/index.html) is the foundation layer offering a scalable, event-driven actor framework for creating agentic workflows;
the [AgentChat API](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/index.html) is built on Core, offering a task-driven, high-level framework for building interactive agentic applications. It is a replacement for AutoGen `v0.2`.

Most of this guide focuses on `v0.4`'s AgentChat API; however, you can also build your own high-level framework using just the Core API.

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

We will update this guide when the missing features become available.

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

Read more on [Agent Tutorial](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/agents.html)
and
[Assistant Agent Docs](https://microsoft.github.io/autogen/dev/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.AssistantAgent).


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
and implement the `on_messages`, `on_reset`, and `produced_message_types` methods.

```python
from typing import Sequence, List
from autogen_core import CancellationToken
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_agentchat.base import Response

class CustomAgent(BaseChatAgent):
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(chat_message=TextMessage(content="Custom reply", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]
```

You can then use the custom agent in the same way as the `AssistantAgent`.
See [Custom Agent Tutorial](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/custom-agents.html)
for more details.

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
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
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
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)

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
    max_consecutive_auto_reply=1, # Set to 1 so that we return to the application after each assistant reply as we are building a chatbot.
)

tool_executor = UserProxyAgent(
    name="tool_executor",
    human_input_mode="NEVER",
    code_execution_config=False,
    llm_config=False,
)

def get_weather(city: str) -> str:
    return f"The weather in {city} is 72 degree and sunny."

# Register the tool function to the tool caller and executor.
register_function(get_weather, caller=tool_caller, executor=tool_executor)

while True:
    user_input = input("User: ")
    if user_input == "exit":
        break
    chat_result = tool_executor.initiate_chat(
        tool_caller, 
        message=user_input,
        summary_method="reflection_with_llm", # To let the model reflect on the tool use, set to "last_msg" to return the tool call result directly.
    )
    print("Assistant:", chat_result.summary)
```

In `v0.4`, you really just need one agent -- the `AssistantAgent` -- to handle 
both the tool calling and tool execution.

```python
import asyncio
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage

def get_weather(city: str) -> str: # Async tool is possible too.
    return f"The weather in {city} is 72 degree and sunny."

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)
    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant. You can call tools to help user.",
        model_client=model_client,
        tools=[get_weather],
        reflect_on_tool_use=True, # Set to True to have the model reflect on the tool use, set to False to return the tool call result directly.
    )
    while True:
        user_input = input("User: ")
        if user_input == "exit":
            break
        response = await assistant.on_messages([TextMessage(content=user_input, source="user")], CancellationToken())
        print("Assistant:", response.chat_message.content)

asyncio.run(main())
```

## Group Chat

In `v0.2`, you need to create a `GroupChat` dataclass and pass it into a
`GroupChatManager`, and have a participant that is a user proxy to initiate the chat.
For a simple scenario of a writer and a critic, you can do the following:

```python
from autogen.agentchat import AssistantAgent, GroupChat, GroupChatManager

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": "sk-xxx"}],
    "seed": 42,
    "temperature": 0,
}

writer = AssistantAgent(
    name="writer",
    description="A writer.",
    system_message="You are a writer.",
    llm_config=llm_config,
)

critic = AssistantAgent(
    name="critic",
    description="A critic.",
    system_message="You are a critic, provide feedback on the writing. Reply only 'APPROVE' if the task is done.",
    llm_config=llm_config,
)

# Create a group chat with the writer and critic.
groupchat = GroupChat(agents=[writer, critic], messages=[], max_round=12)

# Create a group chat manager to manage the group chat, use round-robin selection method.
manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config, speaker_selection_method="round_robin")

# Initiate the chat with the editor, intermediate messages are printed to the console directly.
result = editor.initiate_chat(
    manager,
    message="Write a short story about a robot that discovers it has feelings.",
)
print(result.summary)
```

In `v0.4`, you can use the `RoundRobinGroupChat` to achieve the same behavior.

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)

    writer = AssistantAgent(
        name="writer",
        description="A writer.",
        system_message="You are a writer.",
        model_client=model_client,
    )

    critic = AssistantAgent(
        name="critic",
        description="A critic.",
        system_message="You are a critic, provide feedback on the writing. Reply only 'APPROVE' if the task is done.",
        model_client=model_client,
    )

    # The termination condition is a text termination, which will cause the chat to terminate when the text "APPROVE" is received.
    termination = TextMentionTermination("APPROVE")

    # The group chat will alternate between the writer and the critic.
    group_chat = RoundRobinGroupChat([writer, critic], termination_condition=termination)

    # `run_stream` returns an async generator to stream the intermediate messages.
    stream = group_chat.run_stream(task="Write a short story about a robot that discovers it has feelings.")
    # `Console` is a simple UI to display the stream.
    await Console(stream)

asyncio.run(main())
```

For LLM-based speaker selection, you can use the `SelectorGroupChat` instead.
See [Selector Group Chat Tutorial](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/selector-group-chat.html)
and 
[Selector Group Chat Docs](https://microsoft.github.io/autogen/dev/reference/python/autogen_agentchat.teams.html#autogen_agentchat.teams.SelectorGroupChat)
for more details.

> **Note**: In `v0.4`, you do not need to register functions on a user proxy to use tools
> in a group chat. You can simply pass the tool functions to the `AssistantAgent` as shown in the [Tool Use](#tool-use) section.
> The agent will automatically call the tools when needed.
> If your tool doesn't output well formed response, you can use the `reflect_on_tool_use` parameter to have the model reflect on the tool use.

## Group Chat with Resume

In `v0.2`, group chat with resume is a bit complicated. You need to explicitly
save the group chat messages and load them back when you want to resume the chat.
See [Resuming Group Chat in v0.2](https://microsoft.github.io/autogen/0.2/docs/topics/groupchat/resuming_groupchat) for more details.

In `v0.4`, you can simply call `run` or `run_stream` again with the same group chat object to resume the chat. To export and load the state, you can use 
`save_state` and `load_state` methods.

```python
import asyncio
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

def create_team() -> RoundRobinGroupChat:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)

    writer = AssistantAgent(
        name="writer",
        description="A writer.",
        system_message="You are a writer.",
        model_client=model_client,
    )

    critic = AssistantAgent(
        name="critic",
        description="A critic.",
        system_message="You are a critic, provide feedback on the writing. Reply only 'APPROVE' if the task is done.",
        model_client=model_client,
    )

    # The termination condition is a text termination, which will cause the chat to terminate when the text "APPROVE" is received.
    termination = TextMentionTermination("APPROVE")

    # The group chat will alternate between the writer and the critic.
    group_chat = RoundRobinGroupChat([writer, critic], termination_condition=termination)

    return group_chat


async def main() -> None:
    # Create team.
    group_chat = create_team()

    # `run_stream` returns an async generator to stream the intermediate messages.
    stream = group_chat.run_stream(task="Write a short story about a robot that discovers it has feelings.")
    # `Console` is a simple UI to display the stream.
    await Console(stream)

    # Save the state of the group chat and all participants.
    state = await group_chat.save_state()
    with open("group_chat_state.json", "w") as f:
        json.dump(state, f)
    
    # Create a new team with the same participants configuration.
    group_chat = create_team()

    # Load the state of the group chat and all participants.
    with open("group_chat_state.json", "r") as f:
        state = json.load(f)
    await group_chat.load_state(state)

    # Resume the chat.
    stream = group_chat.run_stream(task="Translate the story into Chinese.")
    await Console(stream)

asyncio.run(main())
```

## Group Chat with Custom Selector (Stateflow)

In `v0.2` group chat, when the `speaker_selection_method` is set to a custom function,
it can override the default selection method. This is useful for implementing
a state-based selection method.
For more details, see [Custom Sepaker Selection in v0.2](https://microsoft.github.io/autogen/0.2/docs/topics/groupchat/customized_speaker_selection).

In `v0.4`, you can use the `SelectorGroupChat` with `selector_func` to achieve the same behavior.
The `selector_func` is a function that takes the current message thread of the group chat
and returns the next speaker's name. If `None` is returned, the LLM-based
selection method will be used.

Here is an example of using the state-based selection method to implement
a web search/analysis scenario.

```python
import asyncio
from typing import Sequence
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Note: This example uses mock tools instead of real APIs for demonstration purposes
def search_web_tool(query: str) -> str:
    if "2006-2007" in query:
        return """Here are the total points scored by Miami Heat players in the 2006-2007 season:
        Udonis Haslem: 844 points
        Dwayne Wade: 1397 points
        James Posey: 550 points
        ...
        """
    elif "2007-2008" in query:
        return "The number of total rebounds for Dwayne Wade in the Miami Heat season 2007-2008 is 214."
    elif "2008-2009" in query:
        return "The number of total rebounds for Dwayne Wade in the Miami Heat season 2008-2009 is 398."
    return "No data found."


def percentage_change_tool(start: float, end: float) -> float:
    return ((end - start) / start) * 100

def create_team() -> SelectorGroupChat:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    planning_agent = AssistantAgent(
        "PlanningAgent",
        description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
        model_client=model_client,
        system_message="""
        You are a planning agent.
        Your job is to break down complex tasks into smaller, manageable subtasks.
        Your team members are:
            Web search agent: Searches for information
            Data analyst: Performs calculations

        You only plan and delegate tasks - you do not execute them yourself.

        When assigning tasks, use this format:
        1. <agent> : <task>

        After all tasks are complete, summarize the findings and end with "TERMINATE".
        """,
    )

    web_search_agent = AssistantAgent(
        "WebSearchAgent",
        description="A web search agent.",
        tools=[search_web_tool],
        model_client=model_client,
        system_message="""
        You are a web search agent.
        Your only tool is search_tool - use it to find information.
        You make only one search call at a time.
        Once you have the results, you never do calculations based on them.
        """,
    )

    data_analyst_agent = AssistantAgent(
        "DataAnalystAgent",
        description="A data analyst agent. Useful for performing calculations.",
        model_client=model_client,
        tools=[percentage_change_tool],
        system_message="""
        You are a data analyst.
        Given the tasks you have been assigned, you should analyze the data and provide results using the tools provided.
        """,
    )

    # The termination condition is a combination of text mention termination and max message termination.
    text_mention_termination = TextMentionTermination("TERMINATE")
    max_messages_termination = MaxMessageTermination(max_messages=25)
    termination = text_mention_termination | max_messages_termination

    # The selector function is a function that takes the current message thread of the group chat
    # and returns the next speaker's name. If None is returned, the LLM-based selection method will be used.
    def selector_func(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        if messages[-1].source != planning_agent.name:
            return planning_agent.name # Always return to the planning agent after the other agents have spoken.
        return None

    team = SelectorGroupChat(
        [planning_agent, web_search_agent, data_analyst_agent],
        model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"), # Use a smaller model for the selector.
        termination_condition=termination,
        selector_func=selector_func,
    )
    return team

async def main() -> None:
    team = create_team()
    task = "Who was the Miami Heat player with the highest points in the 2006-2007 season, and what was the percentage change in his total rebounds between the 2007-2008 and 2008-2009 seasons?"
    await Console(team.run_stream(task=task))

asyncio.run(main())
```

## Nested Chat

Nested chat allows you to nest a whole team or another agent inside
an agent. This is useful for creating a hierarchical structure of agents
or "information silos", as the nested agents cannot communicate directly
with other agents outside of the same group.

In `v0.2`, nested chat is supported by using the `register_nested_chats` method
on the `ConversableAgent` class.
You need to specify the nested sequence of agents using dictionaries,
See [Nested Chat in v0.2](https://microsoft.github.io/autogen/0.2/docs/tutorial/conversation-patterns#nested-chats)
for more details.

In `v0.4`, nested chat is an implementation detail of a custom agent.
You can create a custom agent that takes a team or another agent as a parameter
and implements the `on_messages` method to trigger the nested team or agent.
It is up to the application to decide how to pass or transform the messages from
and to the nested team or agent.

The following example shows a simple nested chat that counts numbers.

```python
from typing import Sequence, List
from autogen_core import CancellationToken
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_agentchat.base import Response

class CountingAgent(BaseChatAgent):
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        if len(messages) == 0:
            last_number = 0 # Start from 0 if no messages are given.
        else:
            assert isinstance(messages[-1], TextMessage)
            last_number = int(messages[-1].content) # Otherwise, start from the last number.
        return Response(chat_message=TextMessage(content=str(last_number + 1), source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

class NestedCountingAgent(BaseChatAgent):
    def __init__(self, name: str, counting_team: RoundRobinGroupChat) -> None:
        super().__init__(name, description="An agent that counts numbers.")
        self._counting_team = counting_team

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        # Run the inner team with the given messages and returns the last message produced by the team.
        result = await self._counting_team.run(task=list(messages), cancellation_token=cancellation_token)
        # To stream the inner messages, implement `on_messages_stream` and use that to implement `on_messages`.
        assert isinstance(result.messages[-1], TextMessage)
        return Response(chat_message=result.messages[-1], inner_messages=list(result.messages[len(messages):-1]))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        # Reset the inner team.
        await self._counting_team.reset()

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

async def main() -> None:
    # Create a team of two counting agents as the inner team.
    counting_agent_1 = CountingAgent("counting_agent_1", description="An agent that counts numbers.")
    counting_agent_2 = CountingAgent("counting_agent_2", description="An agent that counts numbers.")
    counting_team = RoundRobinGroupChat([counting_agent_1, counting_agent_2], max_turns=5)
    # Create a nested counting agent that takes the inner team as a parameter.
    nested_counting_agent = NestedCountingAgent("nested_counting_agent", counting_team)
    response = await nested_counting_agent.on_messages([TextMessage(content="1", source="user")], CancellationToken())
    print(response.inner_messages)
    print(response.chat_message)
```

You can take a look at [Society of Mind Agent (Experimental)](https://microsoft.github.io/autogen/dev/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.SocietyOfMindAgent) for a more complex implementation.

## Sequential Chat

In `v0.2`, sequential chat is supported by using the `initiate_chats` function.
It takes input a list of dictionary configurations for each step of the sequence.
See [Sequential Chat in v0.2](https://microsoft.github.io/autogen/0.2/docs/tutorial/conversation-patterns#sequential-chats)
for more details. 

Base on the feedback from the community, the `initiate_chats` function
is too opinionated and not flexible enough to support the diverse set of scenarios that
users want to implement. We often find users struggling to get the `initiate_chats` function
to work when they can easily glue the steps together usign basic Python code.
Therefore, in `v0.4`, we do not provide a built-in function for sequential chat in the AgentChat API.

Instead, you can create an event-driven sequential workflow using the Core API,
and use the other components provided the AgentChat API to implement each step of the workflow.
See an example of sequential workflow in the [Core API Tutorial](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/sequential-workflow.html).

We recognize that the concept of workflow is at the heart of many applications,
and we will provide more built-in support for workflows in the future.

## GPTAssistantAgent

In `v0.2`, `GPTAssistantAgent` is a special agent class that is backed by the OpenAI Assistant API.

In `v0.4`, the equivalent is the `OpenAIAssistantAgent` class.
It supports the same set of features as the `GPTAssistantAgent` in `v0.2` with
more such as customizable threads and file uploads.
See [OpenAI Assistant Agent Docs](https://microsoft.github.io/autogen/dev/reference/python/autogen_ext.agents.openai.html#autogen_ext.agents.openai.OpenAIAssistantAgent) for more details.

## Long Context Handling

In `v0.2`, long context that overflows the model's context window can be handled
by using the `transforms` capability that is added to an `ConversableAgent`
after which is contructed.

The feedbacks from our community has led us to believe this feature is essential
and should be a built-in component of `AssistantAgent`, and can be used for
every custom agent.

In `v0.4`, we introduce the `ChatCompletionContext` base class that manages
message history and provides a virtual view of the history. Applications can use
built-in implementations such as `BufferedChatCompletionContext` to 
limit the message history sent to the model, or provide their own implementations
that creates different virtual views.

To use `BufferedChatCompletionContext` in an `AssistantAgent` in a chatbot scenario.

```python
import asyncio
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant.",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10), # Model can only view the last 10 messages.
    )
    while True:
        user_input = input("User: ")
        if user_input == "exit":
            break
        response = await assistant.on_messages([TextMessage(content=user_input, source="user")], CancellationToken())
        print("Assistant:", response.chat_message.content)

asyncio.run(main())
```

In this example, the chatbot can only read the last 10 messages in the history.

## Observability and Control

In `v0.4` AgentChat, you can observe the agents by using the `on_messages_stream` method
which returns an async generator to stream the inner thoughts and actions of the agent.
For teams, you can use the `run_stream` method to stream the inner conversation among the agents in the team.
Your application can use these streams to observe the agents and teams in real-time.

Both the `on_messages_stream` and `run_stream` methods takes a `CancellationToken` as a parameter
which can be used to cancel the output stream asynchronously and stop the agent or team.
For teams, you can also use termination conditions to stop the team when a certain condition is met.
See [Termination Condition Tutorial](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/termination.html)
for more details.

Unlike the `v0.2` which comes with a special logging module, the `v0.4` API 
simply uses Python's `logging` module to log events such as model client calls.
See [Logging](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/logging.html)
in the Core API documentation for more details.

## Code Executors

The code executors in `v0.2` and `v0.4` are nearly identical except
the `v0.4` executors support async API. You can also use
`CancellationToken` to cancel a code execution if it takes too long.
See [Command Line Code Executors Tutorial](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/command-line-code-executors.html)
in the Core API documentation.

We also added `AzureContainerCodeExecutor` that can use Azure Container Apps (ACA)
dynamic sessions for code execution.
See [ACA Dynamic Sessions Code Executor Docs](https://microsoft.github.io/autogen/dev/user-guide/extensions-user-guide/azure-container-code-executor.html).