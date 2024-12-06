# Tutorial: Using Distributed Runtime in AutoGen

In this tutorial you'll learn how to distributed runtime works in AutoGen.
We'll first walk you through how to create your development environment and then we'll guide to to created a two
agent conversation in distributed group chat which is integrated with UI.

## What you'll learn

- How to setup and install AutoGen.
- How to run distributed runtime's host.
- How to connect agents to distributed runtime
- How to get two agents communicating in a distributed runtime
- How to add a UI agent to visualize the conversations

## Requirements and resources

You'll need:

- Linux, Mac, or Windows machine with Python 3.10 or above
- An Azure Open AI Model Deployment for Chat Completion

While this exercise is designed to be self-sufficient, at any time feel free to consult the [source code](https://aka.ms/autogen-gh) or the [documentation](https://microsoft.github.io/autogen/dev/).

## Install the dependencies

Create a python virtual environment. Please feel free to use a virtual environment manager of your choice (e.g., `venv` or `conda`). Once you have created the virtual environment, please install the `agentchat` package using:

```bash
pip install 'autogen-agentchat==0.4.0.dev8' 'autogen-ext==0.4.0.dev8' 'chainlit'
```

### Exercise 1: Run distributed host

Very first step in the distributed runtime is to spin up the host so it listens for gRpc connections from agents on the other processes. You can run it by running `python host.py`

```python
# host.py
import asyncio

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost


async def main(host_address: str):
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    print(f"Host started at {host_address}")
    await host.stop_when_signal()


if __name__ == "__main__":
    asyncio.run(main(host_address="localhost:5000"))


# Run the host
# python host.py
```

### Exercise 2: Single Agent

In this step, we want to create a simple agent that connects to a host and replies to itself :)

#### Exercise 2.1: Common code:

Let's create `common.py` to have some common code in it.

```python
# utils.py

from typing import List

from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    TypeSubscription,
    message_handler,
)
from autogen_core.components.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models import AzureOpenAIChatCompletionClient
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from pydantic import BaseModel

client_config = {
    "model": "gpt-4o",
    # "azure_endpoint": "https://{your-custom-endpoint}.openai.azure.com",
    # "azure_deployment": "{your-azure-deployment}",
    "azure_endpoint": "https://devautogen.openai.azure.com",
    "azure_deployment": "gpt-4o",
    "api_version": "2024-08-01-preview",
    "azure_ad_token_provider": get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    ),
}


class GroupChatMessage(BaseModel):
    """Implements a sample message sent by an LLM agent"""

    body: LLMMessage


class RequestToSpeak(BaseModel):
    """Message type for agents to speak"""

    pass

```

#### Exercise 2.2: Define the agent

Now let's define an agent ...

```python
# agent.py
import asyncio

# TODO: Update imports to import from utils.py

class BaseGroupChatAgent(RoutedAgent):
    """A group chat participant using an LLM."""

    def __init__(
        self,
        description: str,
        group_chat_topic_type: str,
        model_client: ChatCompletionClient,
        system_message: str,
    ) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self._model_client = model_client
        self._system_message = SystemMessage(content=system_message)
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.extend(
            [
                UserMessage(content=f"Transferred to {message.body.source}", source="system"),  # type: ignore[union-attr]
                message.body,
            ]
        )
        print(message)


async def main(host_address: str, agent_id: str):
    agent_runtime = GrpcWorkerAgentRuntime(host_address=host_address)

    print(f"Starting Writer Agent with ID: {agent_id}")

    agent_runtime.start()

    agent_type = await BaseGroupChatAgent.register(
        agent_runtime,
        agent_id,
        lambda: BaseGroupChatAgent(
            description="You are AI agent #1",
            group_chat_topic_type="conversation_topic",
            system_message="You are AI agent #1",
            model_client=AzureOpenAIChatCompletionClient(**client_config),
        ),
    )
    await agent_runtime.add_subscription(TypeSubscription(topic_type="conversation_topic", agent_type=agent_type.type))

    await agent_runtime.publish_message(
        GroupChatMessage(body=UserMessage(content="Hi! This is a start", source="User")),
        topic_id=DefaultTopicId(type="conversation_topic"),
    )

    await agent_runtime.stop_when_signal()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python agent1.py <host_address> <agent_id>")
        sys.exit(1)
    asyncio.run(main(host_address=sys.argv[1], agent_id=sys.argv[2]))


# Run the agent
# python agent.py
```

### Exercise 3: Two Agents Communicating

Now you need to modify `agent.py` so an agent only replies when receives a message from an agent with a different agent_id. After doing so, you should be able to run something like this and see messages printed into the corresponding terminals.

```python
python host.py
python agent.py "localhost:5000" "agent_1"
python agent.py "localhost:5000" "agent_2"
```

### Exercise 4: Adding UI Visualization

In this step, we want to create a UI agent which only listens to the conversation topic, and shows them in the ui

```python
# ui_agent.py
@dataclass
class MessageChunk:
    message_id: str
    text: str
    author: str
    finished: bool

class UIAgent(RoutedAgent):
    def __init__(self, on_message_chunk_func):
        super().__init__("UI Agent")
        self._on_message_chunk = on_message_chunk_func

    @message_handler
    async def on_message_chunk(self, message: MessageChunk, ctx: MessageContext) -> None:
        await self._on_message_chunk(message)

# In run_ui.py
async def send_cl_stream(msg: MessageChunk) -> None:
    await cl.Message(content=msg.text, author=msg.author).send()

@cl.on_chat_start
async def start():
    runtime = GrpcWorkerAgentRuntime(host_address="localhost:50051")
    runtime.start()

    ui_agent = await UIAgent.register(
        runtime,
        "ui_agent",
        lambda: UIAgent(on_message_chunk_func=send_cl_stream)
    )

    await runtime.add_subscription(TypeSubscription(
        topic_type="chat",
        agent_type=ui_agent.type
    ))

# Run `chainlit run ui_agent.py --port 8001`
```

## Whats next?

- You are welcome to continue extending this example. You can try adding a LLM based group chat manager or send stream of messages in topics.
- Share your work! Record screenshots or videos of your example for distributed run time and tweet! You may also upload your solution to GitHub! Make sure to use #AutoGen hashtag and tag @pyautogen so that we can discover your work!

## Need help?

You can check [Distributed Group Chat Sample](hhttps://github.com/microsoft/autogen/tree/c02d87e9cf90f4fd91da6b641f1de8077edb54db/python/packages/autogen-core/samples/distributed-group-chat) implementation to learn what else is possible!
