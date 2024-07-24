# Foundation

In this section, we focus on the core concepts of AGNext:
agents, agent runtime, messages, and communication.
You will not find any AI models or tools here, just the foundational
building blocks for building multi-agent applications.

## Agent and Agent Runtime

An agent in AGNext can react to, send, and publish messages.
Messages are the only means through which agents can communicate
with each other.

An agent runtime is the execution environment for agents in AGNext.
Similar to the runtime environment of a programming language,
an agent runtime provides the necessary infrastructure to facilitate communication
between agents, manage agent lifecycles, enforce security boundaries, and support monitoring and
debugging.
For local development, developers can use {py:class}`~agnext.application.SingleThreadedAgentRuntime`,
which can be embedded in a Python application.

```{note}
Agents are not directly instantiated and managed by application code.
Instead, they are created by the runtime when needed and managed by the runtime.
```

### Implementing an Agent

To implement an agent, developer must subclass the {py:class}`~agnext.core.BaseAgent` class,
declare the message types it can handle in the {py:attr}`~agnext.core.AgentMetadata.subscriptions` metadata,
and implement the {py:meth}`~agnext.core.BaseAgent.on_message` method.
This method is invoked when the agent receives a message. For example,
the following agent handles a simple message type and simply prints message it receives:

```python
from dataclasses import dataclass
from agnext.core import BaseAgent, CancellationToken

@dataclass
class MyMessage:
    content: str

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyAgent", subscriptions=[MyMessage])

    async def on_message(self, message: MyMessage, cancellation_token: CancellationToken) -> None:
        print(f"Received message: {message.content}")
```

For convenience, developers can subclass the {py:class}`~agnext.components.TypeRoutedAgent` class
which provides an easy-to use API to implement different message handlers for different message types.
See the section on message handlers below.

### Registering Agents

To make an agent available to the runtime, developers can use the
{py:meth}`~agnext.core.AgentRuntime.register` method.
The process of registration associates a name and a factory function
that creates an instance of the agent in a given namespace.
The factory function is used to allow automatic creation of agents when they are needed.

For example, to register an agent with the {py:class}`~agnext.application.SingleThreadedAgentRuntime`,
the following code can be used:

```python
from agnext.application import SingleThreadedAgentRuntime

runtime = SingleThreadedAgentRuntime()
runtime.register("my_agent", lambda: MyAgent())
```

Once an agent is registered, a reference to the agent can be retrieved by
calling {py:meth}`~agnext.core.AgentRuntime.get` or
{py:meth}`~agnext.core.AgentRuntime.get_proxy`. For example, to
send a message to the agent we just registered:

```python
agent = runtime.get("my_agent")
run_context = runtime.start() # Start processing messages in the background.
await runtime.send_message(MyMessage(content="Hello, World!"), agent)
```

There is a convenience method
{py:meth}`~agnext.core.AgentRuntime.register_and_get` that both registers an agent
and gets a reference.

```{note}
Because the runtime manages the lifecycle of agents, a reference to an agent,
whether it is {py:class}`~agnext.core.AgentId` or {py:class}`~agnext.core.AgentProxy`,
is only used to communicate with the agent or retrieve its metadata (e.g., description).
```

### Running the Agent Runtime

The above code snippet uses `runtime.start()` to start a background task
to process and deliver messages to recepients' message handlers.
This is a feature of the
local embedded runtime {py:class}`~agnext.application.SingleThreadedAgentRuntime`.

To stop the background task immediately, use the `stop()` method:

```python
run_context = runtime.start()
# ... Send messages, publish messages, etc.
await run_context.stop() # This will return immediately but will not cancel
# any in-progress message handling.
```

You can resume the background task by calling `start()` again.

For batch scenarios such as running benchmarks for evaluating agents,
you may want to wait for the background task to stop automatically when
there are no unprocessed messages and no agent is handling messages --
the batch may considered complete.
You can achieve this by using the `stop_when_idle()` method:

```python
run_context = runtime.start()
# ... Send messages, publish messages, etc.
await run_context.stop_when_idle() # This will block until the runtime is idle.
```

You can also directly process messages one-by-one without a background task using:

```python
await runtime.process_next()
```

Other runtime implementations will have their own ways of running the runtime.

## Messages

Agents communicate with each other via messages.
Messages are serializable objects, they can be defined using:

- A subclass of Pydantic's {py:class}`pydantic.BaseModel`, or
- A dataclass

For example:

```python
from dataclasses import dataclass

@dataclass
class TextMessage:
    content: str
    source: str

@dataclass
class ImageMessage:
    url: str
    source: str
```

```{note}
Messages are purely data, and should not contain any logic.
```

### Message Handlers

When an agent receives a message the runtime will invoke the agent's message handler
({py:meth}`~agnext.core.Agent.on_message`) which should implement the agents message handling logic.
If this message cannot be handled by the agent, the agent should raise a
{py:class}`~agnext.core.exceptions.CantHandleException`.

For convenience, the {py:class}`~agnext.components.TypeRoutedAgent` base class
provides the {py:meth}`~agnext.components.message_handler` decorator
for associating message types with message handlers,
so developers do not need to implement the {py:meth}`~agnext.core.Agent.on_message` method.

For example, the following type-routed agent responds to `TextMessage` and `ImageMessage`
using different message handlers:

```python
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken

class MyAgent(TypeRoutedAgent):
    @message_handler
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        print(f"Hello, {message.source}, you said {message.content}!")

    @message_handler
    async def on_image_message(self, message: ImageMessage, cancellation_token: CancellationToken) -> None:
        print(f"Hello, {message.source}, you sent me {message.url}!")

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    agent = await runtime.register_and_get("my_agent", lambda: MyAgent("My Agent"))
    run_context = runtime.start()
    await runtime.send_message(TextMessage(content="Hello, World!", source="User"), agent)
    await runtime.send_message(ImageMessage(url="https://example.com/image.jpg", source="User"), agent)
    await run_context.stop_when_idle()

import asyncio
asyncio.run(main())
```

## Communication

There are two types of communication in AGNext:

- **Direct communication**: An agent sends a direct message to another agent.
- **Broadcast communication**: An agent publishes a message to all agents in the same namespace.

### Direct Communication

To send a direct message to another agent, within a message handler use
the {py:meth}`agnext.core.BaseAgent.send_message` method,
from the runtime use the {py:meth}`agnext.core.AgentRuntime.send_message` method.
Awaiting calls to these methods will return the return value of the
receiving agent's message handler.

```{note}
If the invoked agent raises an exception while the sender is awaiting,
the exception will be propagated back to the sender.
```

#### Request/Response

Direct communication can be used for request/response scenarios,
where the sender expects a response from the receiver.
The receiver can respond to the message by returning a value from its message handler.
You can think of this as a function call between agents.

For example, consider the following type-routed agents:

```python
from dataclasses import dataclass
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken, AgentId

@dataclass
class MyMessage:
    content: str

class InnerAgent(TypeRoutedAgent):
    @message_handler
    async def on_my_message(self, message: MyMessage, cancellation_token: CancellationToken) -> str:
        return MyMessage(content=f"Hello from inner, {message}")

class OuterAgent(TypeRoutedAgent):
    def __init__(self, description: str, inner_agent_id: AgentId):
        super().__init__(description)
        self.inner_agent_id = inner_agent_id

    @message_handler
    async def on_my_message(self, message: MyMessage, cancellation_token: CancellationToken) -> None:
        print(f"Received message: {message.content}")
        # Send a direct message to the inner agent and receves a response.
        response = await self.send_message(MyMessage(f"Hello from outer, {message.content}", self.inner_agent_id))
        print(f"Received inner response: {response.content}")

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    inner = await runtime.register_and_get("inner_agent", lambda: InnerAgent("InnerAgent"))
    outer = await runtime.register_and_get("outer_agent", lambda: OuterAgent("OuterAgent", inner))
    run_context = runtime.start()
    await runtime.send_message(MyMessage("Hello, World!"), outer)
    await run_context.stop_when_idle()

import asyncio
asyncio.run(main())
```

In the above example, upone receving a message,
the `OuterAgent` sends a direct message to the `InnerAgent` and receives
a message in response. The following output will be produced:

```text
Received message: Hello, World!
Received inner response: Hello from inner, Hello from outer, Hello, World!
```

#### Command/Notification

In many scenarios, an agent can commanded another agent to perform an action,
or notify another agent of an event. In this case,
the sender does not need a response from the receiver -- it is a command or notification,
and the receiver does not need to return a value from the message handler.
For example, the `InnerAgent` can be modified to just print the message it receives:

```python
class InnerAgent(TypeRoutedAgent):
    @message_handler
    async def on_my_message(self, message: MyMessage, cancellation_token: CancellationToken) -> None:
        print(f"Hello from inner, {message.content}")
```

### Broadcast Communication

Broadcast communication is effectively the publish/subscribe model.
As part of the base agent ({py:class}`~agnext.core.BaseAgent`) implementation,
it must advertise the message types that
it would like to receive when published ({py:attr}`~agnext.core.AgentMetadata.subscriptions`).
If one of these messages is published, the agent's message handler will be invoked.

The key difference between direct and broadcast communication is that broadcast
communication cannot be used for request/response scenarios.
When an agent publishes a message it is one way only, it cannot receive a response
from any other agent, even if a receiving agent sends a response.

```{note}
An agent receiving a message does not know if it is handling a published or direct message.
So, if a response is given to a published message, it will be thrown away.
```

To publish a message to all agents in the same namespace,
use the {py:meth}`agnext.core.BaseAgent.publish_message` method.
This call must still be awaited to allow the runtime to deliver the message to all agents,
but it will always return `None`.
If an agent raises an exception while handling a published message,
this will be logged but will not be propagated back to the publishing agent.

The following example shows a `BroadcastingAgent` that publishes a message
upong receiving a message. A `ReceivingAgent` that prints the message
it receives.

```python
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken

class BroadcastingAgent(TypeRoutedAgent):
    @message_handler
    async def on_my_message(self, message: MyMessage, cancellation_token: CancellationToken) -> None:
        # Publish a message to all agents in the same namespace.
        await self.publish_message(MyMessage(f"Publishing a message: {message.content}!"))

class ReceivingAgent(TypeRoutedAgent):
    @message_handler
    async def on_my_message(self, message: MyMessage, cancellation_token: CancellationToken) -> None:
        print(f"Received a message: {message.content}")

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    broadcaster = await runtime.register_and_get("broadcasting_agent", lambda: BroadcastingAgent("Broadcasting Agent"))
    await runtime.register("receiving_agent", lambda: ReceivingAgent("Receiving Agent"))
    run_context = runtime.start()
    await runtime.send_message(MyMessage("Hello, World!"), broadcaster)
    await run_context.stop_when_idle()

import asyncio
asyncio.run(main())
```

Running the above code will produce the following output produced by the `ReceivingAgent`:

```text
Received a message: Publishing a message: Hello, World!
```

To publish a message to all agents outside of an agent handling a message,
the message should be published via the runtime with the
{py:meth}`agnext.core.AgentRuntime.publish_message` method.

```python
# ... Replace send_message with publish_message in the above example.
await runtime.publish_message(MyMessage("Hello, World! From the runtime!"), namespace="default")
# ...
```

Running the above code will produce the following output:

```text
Received a message: Hello, World! From the runtime!
Received a message: Publishing a message: Hello, World! From the runtime!
```

The first output is from the `ReceivingAgent` that received a message published
by the runtime. The second output is from the `ReceivingAgent` that received
a message published by the `BroadcastingAgent`.

```{note}
If an agent publishes a message type for which it is subscribed it will not
receive the message it published. This is to prevent infinite loops.
```

## Namespace

Namespace allow for defining logical boundaries between agents.

Namespaces are strings, and the default is `default`.

Two possible use cases of agents are:

- Creating a multi-tenant system where each tenant has its own namespace. For
  example, a chat system where each tenant has its own set of agents.
- Security boundaries between agent groups. For example, a chat system where
  agents in the `admin` namespace can communicate with agents in the `user`
  namespace, but not the other way around.

The {py:class}`~agnext.core.AgentId` is used to address an agent,
it is the combination of the agent's namespace and its name.

When getting an agent reference ({py:meth}`agnext.core.AgentRuntime.get`) or
proxy ({py:meth}`agnext.core.AgentRuntime.get_proxy`) from the runtime the
namespace can be specified.
Agents have an ID property ({py:attr}`agnext.core.Agent.id`) that returns the
agent's id.
Additionally, the register method takes a factory that can optionally accept
the ID as an argument ({py:meth}`agnext.core.AgentRuntime.register`).

By default, there are no restrictions and are left to the application to
enforce. The runtime will however automatically create agents in a
namespace if it does not exist.
