# Agent Identity and Lifecycle

The agent runtime manages agents' identities
and lifecycles.
Application does not create agents directly, rather,
it registers an agent type with a factory function for
agent instances.
In this section, we explain how agents are identified
and created by the runtime.

## Agent ID

Agent ID uniquely identifies an agent instance within
an agent runtime -- including distributed runtime.
It is the "address" of the agent instance for receiving messages.
It has two components: agent type and agent key.

```{note}
Agent ID = (Agent Type, Agent Key)
```

The agent type is not an agent class.
It associates an agent with a specific
factory function, which produces instances of agents
of the same agent type.
For example, different factory functions can produce the same
agent class but with different constructor perameters.
The agent key is an instance identifier
for the given agent type.
Agent IDs can be converted to and from strings. the format of this string is:
```{note}
Agent_Type/Agent_Key
```
Types and Keys are considered valid if they only contain alphanumeric letters (a-z) and (0-9), or underscores (_). A valid identifier cannot start with a number, or contain any spaces.

In a multi-agent application, agent types are
typically defined directly by the application, i.e., they
are defined in the application code.
On the other hand, agent keys are typically generated given
messages delivered to the agents, i.e., they are defined
by the application data.

For example, a runtime has registered the agent type `"code_reviewer"`
with a factory function producing agent instances that perform
code reviews. Each code review request has a unique ID `review_request_id`
to mark a dedicated
session.
In this case, each request can be handled by a new instance
with an agent ID, `("code_reviewer", review_request_id)`.

## Agent Lifecycle

When a runtime delivers a message to an agent instance given its ID,
it either fetches the instance,
or creates it if it does not exist.

![Agent Lifecycle](agent-lifecycle.svg)

The runtime is also responsible for "paging in" or "out" agent instances
to conserve resources and balance load across multiple machines.
This is not implemented yet.
