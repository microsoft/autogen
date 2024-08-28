# Topic and Subscription in Broadcast

In AGNext, there are two ways for runtime to deliver messages,
direct messaging or broadcast. Direct messaging is one to one: the sender
must provide the recipient's agent ID. On the other hand,
broadcast is one to many and the sender does not provide recpients'
agent IDs.

Many scenarios are suitable for broadcast.
For example, in event-driven workflows, agents do not always know who
will handle their messages, and a workflow can be composed of agents
with no inter-dependencies.
This section focuses on the core concepts in broadcast: topic and subscription.

## Topic

A topic defines the scope of a broadcast message.
In essence, AGNext agent runtime implements a publish-subscribe model through
its broadcast API: when publishing a message, the topic mus be specified.
It is an indirection over agent IDs.

A topic consists of two components: topic type and topic source.

```{note}
Topic = (Topic Type, Topic Source)
```

Similar to [agent ID](./agent-identity-and-lifecycle.md#agent-id),
which also has two components, topic type is usually defined by
application code to mark the type of messages the topic is for.
For example, a GitHub agent may use `"GitHub_Issues"` as the topic type
when publishing messages about new issues.

Topic source is the unique identifier for a topic within a topic type.
It is typically defined by application data.
For example, the GitHub agent may use `"github.com/{repo_name}/issues/{issue_number}"`
as the topic source to uniquely identifies the topic.
Topic source allows the publisher to limit the scope of messages and create
silos.

## Subscription

A subscription maps topic to agent IDs.

If a topic has no subscription, messages published to this topic will
not be delivered to any agent.
If a topic has many subscriptions, messages will be delivered
following all the subscriptions to every recipient agent only once.
Applications can add or remove subscriptions using agent runtime's API.

### Type-based Subscription

A type-based subscription maps a topic type to an agent type
(see [agent ID](./agent-identity-and-lifecycle.md#agent-id)).
It declares a mapping from topics to agent IDs without knowing the
exact topic sources and agent keys.
The mechanism is simple: any topic matching the type-based subscription's
topic type will be mapped to an agent ID with the subscription's agent type
and the agent key assigned to the value of the topic source.

```{note}
Type-Based Subscription = Topic Type --> Agent Type
```

For example, a type-based subscription maps topic type `"GitHub_Issues"`
to agent type `"Triage_Agent"`.
When a broadcast message is published to the topic
`("GitHub_Issues", "github.com/microsoft/autogen/issues/99"),
the subscription maps the topic to an agent instance with ID
`("Triage_Agent", "github.com/microsoft/autogen/issues/99")`,
and the runtime will deliver the message to that agent, creating it
if not exist.

Generally speaking, type-based subscription is the preferred way to delcare
subscriptions. It is portable and data-independent:
developers do not need to write application code that depends on specific agent IDs.
