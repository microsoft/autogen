# Design Patterns TL;DR

## Overview

Multi-agent design patterns emerge from message protocols — the structured ways agents interact
to solve problems. AutoGen Core lets you implement any pattern; AgentChat bundles the most common
ones as team types. Research (AutoGen paper, MetaGPT, ChatDev) shows multi-agent systems
consistently outperform single-agent systems on complex tasks such as software development.

## Available Patterns

| Pattern | One-line description |
|---------|---------------------|
| **Group Chat** | Multiple agents collaborate on a shared task with a coordinator selecting the next speaker |
| **Handoffs** | An agent delegates (hands off) to another agent best suited for the next step |
| **Sequential Workflow** | Agents run in a fixed pipeline — output of one feeds into the next |
| **Concurrent Agents** | Multiple agents run in parallel on independent subtasks and results are merged |
| **Reflection** | A second agent critiques and refines the output of the first before returning a result |
| **Mixture of Agents** | Multiple agents each produce a response; an aggregator synthesizes the final answer |

## Group Chat (brief)

A coordinator (selector) agent reviews the conversation and decides which participant speaks next.
In AgentChat this is `SelectorGroupChat`. Supports custom selector prompts and the ability to
allow or disallow repeated speakers. Best for task decomposition across specialists.

## Handoffs (brief)

An agent uses a tool call to explicitly pass control to another agent. The receiving agent picks
up where the first left off. In AgentChat this is `Swarm`. Each agent decides locally who to
hand off to — no central coordinator. Best for pipelines with conditional routing.

## Sequential Workflow (brief)

Agents are chained so that agent N's output becomes agent N+1's input. Simple and predictable.
Suitable when subtasks have a clear linear dependency. In AgentChat, use `GraphFlow` with a
linear graph or `RoundRobinGroupChat` with a two-agent setup.

## Reflection (brief)

A generator agent produces a result; a reviewer agent evaluates it and sends feedback for
another round of generation. Continues until the reviewer approves or a termination condition
fires. Improves quality at the cost of extra model calls. Implemented via `RoundRobinGroupChat`
with a critic agent and a `TextMentionTermination` (e.g., "APPROVE").

## Further Reading

- Design patterns intro: `core-user-guide/design-patterns/intro.md`
- Group chat (code): `design-patterns/group-chat.ipynb`
- Handoffs (code): `design-patterns/handoffs.ipynb`
- Sequential workflow (code): `design-patterns/sequential-workflow.ipynb`
- Concurrent agents (code): `design-patterns/concurrent-agents.ipynb`
- Reflection (code): `design-patterns/reflection.ipynb`
- Mixture of agents (code): `design-patterns/mixture-of-agents.ipynb`
