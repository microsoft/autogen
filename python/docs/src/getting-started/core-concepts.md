# Core Concepts

## What is Multi-Agent Application?

A wide variety of software applications can be modeled as a collection of independent
agents that communicate with each other through messages:
sensors on a factory floor,
distributed services powering web applications,
business workflows involving multiple stakeholders,
and more recently, generative artificial intelligence (AI) models (e.g., GPT-4) that can write code and interact with
other software systems.
We refer to them as multi-agent applications.

In a multi-agent application, agents can live in the same process, on the same machine,
or on different machines and across organizational boundaries.
They can be implemented using different AI models, instructions, and programming languages.
They can collaborate and work toward a common goal.

Each agent is a self-contained unit:
developers can build, test and deploy it independently, and reuse it for different scenarios.
Agents are composable: simple agents can form complex applications.

## AGNext Overview

AGNext is a framework for building multi-agent applications.
It provides a runtime envionment to facilitate communication between agents,
manage their identities and lifecycles, and enforce boundaries.
It also provides a set of common patterns and components to help developers build
AI agents that can work together.

AGNext is designed to be unopinionated and extensible.
It does not prescribe an abstraction for agents or messages, rather, it provides
a minimal base layer that can be extended to suit the application's needs.
Developers can build agents quickly by using the provided components including
type-routed agent, AI model clients, tools for AI models, code execution sandboxes,
memory stores, and more.
Developers can also make use of the provided multi-agent patterns to build
orchestrated workflows, group chat systems, and more.

The API consists of the following modules:

- {py:mod}`agnext.core` - The core interfaces that defines agent and runtime.
- {py:mod}`agnext.application` - Implementations of the runtime and other modules (e.g., logging) for building applications.
- {py:mod}`agnext.components` - Independent agent-building components: agents, models, memory, and tools.

## Agent and Agent Runtime

An agent in AGNext is an entity that can react to, send, and publish
messages. Messages are the only means through which agents can communicate
with each other.

An agent runtime is the execution environment for agents in AGNext.
Similar to the runtime environment of a programming language, the
agent runtime provides the necessary infrastructure to facilitate communication
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
the following agent handles string messages and simply prints message it receives:

```python
from agnext.core import BaseAgent, CancellationToken

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyAgent", subscriptions=[str])

    async def on_message(self, message: str, cancellation_token: CancellationToken) -> None:
        print(f"Received message: {message}")
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
await runtime.send_message("Hello, World!", agent)
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

The above code snippets will not actually produce any output because the
runtime is not running.
The local embedded runtime {py:class}`~agnext.application.SingleThreadedAgentRuntime`
can be called to process messages until there are no more messages to process.

```python
await runtime.process_until_idle()
```

It can also be called to process a single message:

```python
await runtime.process_next()
```

Other runtime implementations will have their own way of running the runtime.

## Messages

Agents communicate with each other via messages.
Messages are serializable objects, they can be defined using:

- A subclass of Pydantic's {py:class}`pydantic.BaseModel`, or
- A dataclass
- A built-in serializable Python type (e.g., `str`).

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
provides a simple API for associating message types with message handlers,
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
    agent = runtime.register_and_get("my_agent", lambda: MyAgent("My Agent"))
    await runtime.send_message(TextMessage(content="Hello, World!", source="User"), agent)
    await runtime.send_message(ImageMessage(url="https://example.com/image.jpg", source="User"), agent)
    runtime.process_until_idle()

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

Awaiting this method call will return the a `Future[T]` object where `T` is the type
of response of the invoked agent.
The future object can be awaited to get the actual response.

```{note}
If the invoked agent raises an exception while the sender is awaiting on
the future, the exception will be propagated back to the sender.
```

#### Request/Response

Direct communication can be used for request/response scenarios,
where the sender expects a response from the receiver.
The receiver can respond to the message by returning a value from its message handler.
You can think of this as a function call between agents.

For example, consider the following type-routed agents:

```python
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken, AgentId

class InnerAgent(TypeRoutedAgent):
    @message_handler
    async def on_str_message(self, message: str, cancellation_token: CancellationToken) -> str:
        return f"Hello from inner, {message}"

class OuterAgent(TypeRoutedAgent):
    def __init__(self, inner_agent_id: AgentId):
        super().__init__("OuterAgent")
        self.inner_agent_id = inner_agent_id

    @message_handler
    async def on_str_message(self, message: str, cancellation_token: CancellationToken) -> None:
        print(f"Received message: {message}")
        # Send a direct message to the inner agent and receves a response future.
        response_future = await self.send_message(f"Hello from outer, {message}", self.inner_agent_id)
        # Wait for the response to be ready.
        response = await response_future
        print(f"Received inner response: {response}")

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    inner = runtime.register_and_get("inner_agent", lambda: InnerAgent("InnerAgent"))
    outer = runtime.register_and_get("outer_agent", lambda: OuterAgent("OuterAgent", inner))
    await runtime.send_message("Hello, World!", outer)
    runtime.process_until_idle()

import asyncio
asyncio.run(main())
```

In the above example, upone receving a message,
the `OuterAgent` sends a direct string message to the `InnerAgent` and receives
a string message in response. The following output will be produced:

```text
Received message: Hello, World!
Received inner response: Hello from inner, Hello from outer, Hello, World!
```

```{note}
To get the response after sending a message, the sender must await on the 
response future. So you can also write `response = await await self.send_message(...)`.
```

#### Send, No Reply

In many scenarios, the sender does not need a response from the receiver.
In this case, the sender does not need to await on the response future,
and the receiver does not need to return a value from the message handler.
In the following example, the `InnerAgent` does not return a value,
and the `OuterAgent` does not await on the response future:

```python
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken, AgentId

class InnerAgent(TypeRoutedAgent):
    @message_handler
    async def on_str_message(self, message: str, cancellation_token: CancellationToken) -> None:
        # Just print the message.
        print(f"Hello from inner, {message}")

class OuterAgent(TypeRoutedAgent):
    def __init__(self, inner_agent_id: AgentId):
        super().__init__("OuterAgent")
        self.inner_agent_id = inner_agent_id

    @message_handler
    async def on_str_message(self, message: str, cancellation_token: CancellationToken) -> None:
        print(f"Received message: {message}")
        # Send a direct message to the inner agent and move on.
        await self.send_message(f"Hello from outer, {message}", self.inner_agent_id)
        # No need to wait for the response, just do other things.

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    inner = runtime.register_and_get("inner_agent", lambda: InnerAgent("InnerAgent"))
    outer = runtime.register_and_get("outer_agent", lambda: OuterAgent("OuterAgent", inner))
    await runtime.send_message("Hello, World!", outer)
    runtime.process_until_idle()

import asyncio
asyncio.run(main())
```

In the above example, the `OuterAgent` sends a direct string message to the `InnerAgent`
but does not await on the response future. The following output will be produced:

```text
Received message: Hello, World!
Hello from inner, Hello from outer, Hello, World!
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
upong receiving a string message. A `ReceivingAgent` that prints the message
it receives.

```python
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken

class BroadcastingAgent(TypeRoutedAgent):
    @message_handler
    async def on_str_message(self, message: str, cancellation_token: CancellationToken) -> None:
        # Publish a message to all agents in the same namespace.
        await self.publish_message(f"Publishing a message: {message}!")

class ReceivingAgent(TypeRoutedAgent):
    @message_handler
    async def on_str_message(self, message: str, cancellation_token: CancellationToken) -> None:
        print(f"Received a message: {message}")

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    broadcaster = runtime.register_and_get("broadcasting_agent", lambda: BroadcastingAgent("Broadcasting Agent"))
    runtime.register("receiving_agent", lambda: ReceivingAgent("Receiving Agent"))
    await runtime.send_message("Hello, World!", broadcaster)
    runtime.process_until_idle()

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
await runtime.publish_message("Hello, World! From the runtime!", namespace="default")
runtime.process_until_idle()
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
