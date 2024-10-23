# Topic and Subscription

There are two ways for runtime to deliver messages,
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
In essence, agent runtime implements a publish-subscribe model through
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

Topic IDs can be converted to and from strings. the format of this string is:
```{note}
Topic_Type/Topic_Source
```
Types are considered valid if they are in UTF8 and only contain alphanumeric letters (a-z) and (0-9), or underscores (_). A valid identifier cannot start with a number, or contain any spaces.
Sources are considered valid if they are in UTF8 and only contain characters between (inclusive) ascii 32 (space) and 126 (~).

## Subscription

A subscription maps topic to agent IDs.

![Subscription](subscription.svg)

The diagram above shows the relationship between topic and subscription.
An agent runtime keeps track of the subscriptions and uses them to deliver
messages to agents.

If a topic has no subscription, messages published to this topic will
not be delivered to any agent.
If a topic has many subscriptions, messages will be delivered
following all the subscriptions to every recipient agent only once.
Applications can add or remove subscriptions using agent runtime's API.

## Type-based Subscription

A type-based subscription maps a topic type to an agent type
(see [agent ID](./agent-identity-and-lifecycle.md#agent-id)).
It declares an unbounded mapping from topics to agent IDs without knowing the
exact topic sources and agent keys.
The mechanism is simple: any topic matching the type-based subscription's
topic type will be mapped to an agent ID with the subscription's agent type
and the agent key assigned to the value of the topic source.
For Python API, use {py:class}`~autogen_core.components.TypeSubscription`.

```{note}
Type-Based Subscription = Topic Type --> Agent Type
```

Generally speaking, type-based subscription is the preferred way to declare
subscriptions. It is portable and data-independent:
developers do not need to write application code that depends on specific agent IDs.

### Scenarios of Type-Based Subscription

Type-based subscriptions can be applied to many scenarios when the exact
topic or agent IDs are data-dependent.
The scenarios can be broken down by two considerations:
(1) whether it is single-tenant or multi-tenant, and
(2) whether it is a single topic or multiple topics per tenant.
A tenant typically refers to a set of agents that handle a specific 
user session or a specific request. 

#### Single-Tenant, Single Topic

In this scenario, there is only one tenant and one topic for the entire
application.
It is the simplest scenario and can be used in many cases
like a command line tool or a single-user application.

To apply type-based subscription for this scenario, create one type-based
subscription for each agent type, and use the same topic type for all
the type-based subscriptions.
When you publish, always use the same topic, i.e., the same topic type and topic source.

For example, assuming there are three agent types: `"triage_agent"`,
`"coder_agent"` and `"reviewer_agent"`, and the topic type is `"default"`,
create the following type-based subscriptions:

```python
# Type-based Subscriptions for single-tenant, single topic scenario
TypeSubscription(topic_type="default", agent_type="triage_agent")
TypeSubscription(topic_type="default", agent_type="coder_agent")
TypeSubscription(topic_type="default", agent_type="reviewer_agent")
```

With the above type-based subscriptions, use the same topic source 
`"default"` for all messages. So the topic is always `("default", "default")`.
A message published to this topic will be delivered to all the agents of
all above types. Specifically, the message will be sent to the following agent IDs:

```python
# The agent IDs created based on the topic source
AgentID("triage_agent", "default")
AgentID("coder_agent", "default")
AgentID("reviewer_agent", "default")
```

The following figure shows how type-based subscription works in this example.

![Type-Based Subscription Single-Tenant, Single Topic Scenario Example](type-subscription-single-tenant-single-topic.svg)

If the agent with the ID does not exist, the runtime will create it.


#### Single-Tenant, Multiple Topics

In this scenario, there is only one tenant but you want to control
which agent handles which topic. This is useful when you want to
create silos and have different agents specialized in handling different topics.

To apply type-based subscription for this scenario, 
create one type-based subscription for each agent type but with different
topic types. You can map the same topic type to multiple agent types if
you want these agent types to share a same topic.
For topic source, still use the same value for all messages when you publish.

Continuing the example above with same agent types, create the following
type-based subscriptions:

```python
# Type-based Subscriptions for single-tenant, multiple topics scenario
TypeSubscription(topic_type="triage", agent_type="triage_agent")
TypeSubscription(topic_type="coding", agent_type="coder_agent")
TypeSubscription(topic_type="coding", agent_type="reviewer_agent")
```

With the above type-based subscriptions, any message published to the topic
`("triage", "default")` will be delivered to the agent with type
`"triage_agent"`, and any message published to the topic
`("coding", "default")` will be delivered to the agents with types
`"coder_agent"` and `"reviewer_agent"`. 

The following figure shows how type-based subscription works in this example.

![Type-Based Subscription Single-Tenant, Multiple Topics Scenario Example](type-subscription-single-tenant-multiple-topics.svg)


#### Multi-Tenant Scenarios

In single-tenant scenarios, the topic source is always the same (e.g., `"default"`)
-- it is hard-coded in the application code.
When moving to multi-tenant scenarios, the topic source becomes data-dependent.

```{note}
A good indication that you are in a multi-tenant scenario is that you need 
multiple instances of the same agent type. For example, you may want to have
different agent instances to handle different user sessions to 
keep private data isolated, or, you may want to distribute a heavy workload
across multiple instances of the same agent type and have them work on it concurrently.
```

Continuing the example above, if you want to have dedicated instances of agents
to handle a specific GitHub issue, you need to set the topic source to be a
unique identifier for the issue. 

For example, let's say there is one type-based subscription for the agent type
`"triage_agent"`:

```python
TypeSubscription(topic_type="github_issues", agent_type="triage_agent")
```

When a message is published to the topic
`("github_issues", "github.com/microsoft/autogen/issues/1")`,
the runtime will deliver the message to the agent with ID
`("triage_agent", "github.com/microsoft/autogen/issues/1")`.
When a message is published to the topic
`("github_issues", "github.com/microsoft/autogen/issues/9")`,
the runtime will deliver the message to the agent with ID
`("triage_agent", "github.com/microsoft/autogen/issues/9")`.

The following figure shows how type-based subscription works in this example.

![Type-Based Subscription Multi-Tenant Scenario Example](type-subscription-multi-tenant.svg)

Note the agent ID is data-dependent, and the runtime will create a new instance
of the agent
if it does not exist.

To support multiple topics per tenant, you can use different topic types,
just like the single-tenant, multiple topics scenario.
