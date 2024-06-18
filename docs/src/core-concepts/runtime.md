# Agent Runtime

Agent runtime is the execution environment for agents in AGNext.
Similar to the runtime environment of a programming language, the
agent runtime provides the necessary infrastructure to facilitate communication
between agents, manage agent states, and provide API for monitoring and
debugging multi-agent interactions.

Further readings:

1. {py:class}`agnext.core.AgentRuntime`
2. {py:class}`agnext.application.SingleThreadedAgentRuntime`

## Agent Registration

Agents are registered with the runtime using the
{py:meth}`agnext.core.AgentRuntime.register` method. The process of registration
associates some name, which is the `type` of the agent with a factory function
that is able to create an instance of the agent in a given namespace. The reason
for the factory function is to allow automatic creation of agents when they are
needed, including automatic creation of agents for not yet existing namespaces.

Once an agent is registered, a reference to the agent can be retrieved by
calling {py:meth}`agnext.core.AgentRuntime.get` or
{py:meth}`agnext.core.AgentRuntime.get_proxy`. There is a convenience method
{py:meth}`agnext.core.AgentRuntime.register_and_get` that both registers a type
and gets a reference.

A byproduct of this process of `register` + `get` is that
{py:class}`agnext.core.Agent` interface is a purely implementation contract. All
agents must be communicated with via the runtime. This is a key design decision
that allows the runtime to manage the lifecycle of agents, and to provide a
consistent API for interacting with agents. Therefore, to communicate with
another agent the {py:class}`agnext.core.AgentId` must be used. There is a
convenience class {py:meth}`agnext.core.AgentProxy` that bundles an ID and a
runtime together.