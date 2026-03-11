# Architecture TL;DR

## Core vs AgentChat: Which to Use

**AutoGen Core** is the low-level foundation: an actor-model, event-driven runtime for building
multi-agent applications from scratch. Use Core when you need full control over agent behavior,
message protocols, pub/sub routing, or distributed deployment across processes and languages.
Core is unopinionated — it does not prescribe agent abstractions or multi-agent patterns.

**AgentChat** is the high-level API built on top of Core. It provides preset agents
(`AssistantAgent`, `UserProxyAgent`, `CodeExecutorAgent`) and predefined team patterns
(`RoundRobinGroupChat`, `SelectorGroupChat`, `Swarm`, `GraphFlow`). Use AgentChat for
rapid prototyping, standard multi-agent workflows, and when you want sensible defaults
without wiring message protocols by hand. Beginners should start here.

## Standalone Runtime

Suitable for single-process applications where all agents share the same programming language
and process. The `SingleThreadedAgentRuntime` is the primary Python implementation. Agents
communicate via messages routed through the runtime; the runtime manages agent lifecycle.
This covers the majority of use cases.

## Distributed Runtime

Suitable for multi-process and multi-machine deployments, including agents written in different
languages. A **host servicer** coordinates communication across **workers**; each worker runs
agents and connects to the host via a **gateway**. Agent implementation is identical to the
standalone case — switching runtimes requires no changes to agent code.

## Actor Model Fundamentals

- Every agent has a unique **AgentId** (type + key); the runtime routes messages to it
- Agents communicate exclusively by passing **messages** — no shared state
- Agents process one message at a time (single-threaded per agent), preventing race conditions
- The runtime manages agent **lifecycle**: creation, activation, and teardown

## Key Components

| Component | Role |
|-----------|------|
| Runtime | Message routing, agent lifecycle, security boundaries |
| Agent | Message handler registered with a type in the runtime |
| Message | Typed data exchanged between agents |
| Topic | Named broadcast channel for pub/sub delivery |
| Subscription | Declares which topics an agent listens to |

## Further Reading

- Full architecture details: `core-concepts/architecture.md`
- Application stack and message protocols: `core-concepts/application-stack.md`
- Runtime mechanics (code): `framework/agent-and-agent-runtime.ipynb`
- Pub/sub model: `core-concepts/topic-and-subscription.md`
