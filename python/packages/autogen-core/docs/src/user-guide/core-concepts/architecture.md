# Agent Runtime Environments

At the foundation level, the framework provides a _runtime envionment_, which facilitates
communication between agents, manages their identities and lifecycles,
and enforce security and privacy boundaries.

It supports two types of runtime environment: *standalone* and *distributed*.
Both types provide a common set of APIs for building multi-agent applications,
so you can switch between them without changing your agent implementation.
Each type can also have multiple implementations.

## Standalone Agent Runtime

Standalone runtime is suitable for single-process applications where all agents
are implemented in the same programming language and running in the same process.
In the Python API, an example of standalone runtime is the {py:class}`~autogen_core.application.SingleThreadedAgentRuntime`.

The following diagram shows the standalone runtime in the framework.

![Standalone Runtime](architecture-standalone.svg)

Here, agents communicate via messages through the runtime, and the runtime manages
the _lifecycle_ of agents.

Developers can build agents quickly by using the provided components including
_routed agent_, AI model _clients_, tools for AI models, code execution sandboxes,
model context stores, and more.
They can also implement their own agents from scratch, or use other libraries.

## Distributed Agent Runtime

Distributed runtime is suitable for multi-process applications where agents
may be implemented in different programming languages and running on different
machines.

![Distributed Runtime](architecture-distributed.svg)

A distributed runtime, as shown in the diagram above,
consists of a _host servicer_ and multiple _workers_.
The host servicer facilitates communication between agents across workers
and maintains the states of connections.
The workers run agents and communicate with the host servicer via _gateways_.
They advertise to the host servicer the agents they run and manage the agents' lifecycles.

Agents work the same way as in the standalone runtime so that developers can
switch between the two runtime types with no change to their agent implementation.

