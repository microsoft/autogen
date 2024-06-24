# Namespace

Namespace allow for defining logical boundaries between agents.

Namespaces are strings, and the default is `default`.

Two possible use cases of agents are:

- Creating a multi-tenant system where each tenant has its own namespace. For
  example, a chat system where each tenant has its own set of agents.
- Security boundaries between agent groups. For example, a chat system where
  agents in the `admin` namespace can communicate with agents in the `user`
  namespace, but not the other way around.

The {py:class}`agnext.core.AgentId` is used to address an agent, it is the combination of the agent's namespace and its name.

When getting an agent reference ({py:meth}`agnext.core.AgentRuntime.get`) or proxy ({py:meth}`agnext.core.AgentRuntime.get_proxy`) from the runtime the namespace can be specified. Agents have an ID property ({py:attr}`agnext.core.Agent.id`) that returns the agent's id. Additionally, the register method takes a factory that can optionally accept the ID as an argument ({py:meth}`agnext.core.AgentRuntime.register`).

By default, there are no restrictions and are left to the application to enforce. The runtime will however automatically create agents in a namespace if it does not exist.
