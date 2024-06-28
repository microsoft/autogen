# Agent

An agent in AGNext is an entity that can react to, send, and publish
messages. Messages are the only means through which agents can communicate
with each other.

## Messages

Messages are typed, and serializable (to JSON) objects that agents use to communicate. The type of a message is used to determine which agents a message should be delivered to, if an agent can handle a message and the handler that should be invoked when the message is received by an agent. If an agent is invoked with a message it is not able to handle, it must raise {py:class}`~agnext.core.exceptions.CantHandleException`.

Generally, messages are one of:

- A subclass of Pydantic's {py:class}`pydantic.BaseModel`
- A dataclass

Messages are purely data, and should not contain any logic.

```{tip}
It is *strongly* recommended that messages are Pydantic models. This allows for easy serialization and deserialization of messages, and provides a clear schema for the message.
```

<!-- ### Required Message Types

At the core framework level there is *no requirement* of which message types are handled by an agent. However, some behavior patterns require agents understand certain message types. For an agent to participate in these patterns, it must understand any such required message types.

For example, the chat layer in AGNext has the following required message types:

- {py:class}`agnext.chat.types.PublishNow`
- {py:class}`agnext.chat.types.Reset`

These are purely behavioral messages that are used to control the behavior of agents in the chat layer and do not represent any content.

Agents should document which message types they can handle. Orchestrating agents should document which message types they require.

```{tip}
An important part of designing an agent or choosing which agents to use is understanding which message types are required by the agents you are using.
``` -->

## Communication

There are two forms of communication in AGNext:

- **Direct communication**: An agent sends a direct message to another agent.
- **Broadcast communication**: An agent publishes a message to all agents in the same namespace.

### Message Handling

When an agent receives a message the runtime will invoke the agent's message handler ({py:meth}`agnext.core.Agent.on_message`) which should implement the agents message handling logic. If this message cannot be handled by the agent, the agent should raise a {py:class}`~agnext.core.exceptions.CantHandleException`. For the majority of custom agent's {py:meth}`agnext.core.Agent.on_message` will not be directly implemented, but rather the agent will use the {py:class}`~agnext.components.TypeRoutedAgent` base class which provides a simple API for associating message types with message handlers.

### Direct Communication

Direct communication is effectively an RPC call directly to another agent. When sending a direct message to another agent, the receiving agent can respond to the message with another message, or simply return `None`. To send a message to another agent, within a message handler use the {py:meth}`agnext.core.BaseAgent.send_message` method. Awaiting this call will return the response of the invoked agent. If the receiving agent raises an exception, this will be propagated back to the sending agent.

To send a message to an agent outside of agent handling a message the message should be sent via the runtime with the {py:meth}`agnext.core.AgentRuntime.send_message` method. This is often how an application might "start" a workflow or conversation.

### Broadcast Communication

Broadcast communication is effectively the publish-subscribe model.
As part of the agent's implementation it must advertise the message types that it would like to receive when published ({py:attr}`agnext.core.Agent.subscriptions`). If one of these messages is published, the agent's message handler will be invoked. The key difference between direct and broadcast communication is that broadcast communication is not a request/response model. When an agent publishes a message it is one way, it is not expecting a response from any other agent. In fact, they cannot respond to the message.

To publish a message to all agents, use the {py:meth}`agnext.core.BaseAgent.publish_message` method. This call must still be awaited to allow the runtime to deliver the message to all agents, but it will always return `None`. If an agent raises an exception while handling a published message, this will be logged but will not be propagated back to the publishing agent.

To publish a message to all agents outside of an agent handling a message, the message should be published via the runtime with the {py:meth}`agnext.core.AgentRuntime.publish_message` method.

If an agent publishes a message type for which it is subscribed it will not receive the message it published. This is to prevent infinite loops.

```{note}
Currently an agent does not know if it is handling a published or direct message. So, if a response is given to a published message, it will be thrown away.
```
