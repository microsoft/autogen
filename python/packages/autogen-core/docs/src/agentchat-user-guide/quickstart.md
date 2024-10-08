---
myst:
  html_meta:
    "description lang=en": |
      Quick Start Guide for AgentChat: Migrating from AutoGen 0.2x to 0.4x.
---

# Quick Start

AgentChat API, introduced in AutoGen 0.4x, offers a similar level of abstraction as the default Agent classes in AutoGen 0.2x.

## Installation

Install the `autogen-agentchat` package using pip:

```bash

pip install autogen-agentchat==0.4.0dev0
```

:::{note}
For further installation instructions, please refer to the [package information](pkg-info-autogen-agentchat).
:::

## Creating a Simple Agent Team

The following example illustrates creating a simple agent team with two agents that interact to solve a task.

1. `CodingAssistantAgent` that generates responses using an LLM model. 2.`CodeExecutorAgent` that executes code snippets and returns the output.

The task is to "Create a plot of NVIDIA and TESLA stock returns YTD from 2024-01-01 and save it to 'nvidia_tesla_2024_ytd.png'."

```{include} stocksnippet.md

```

```{tip}
AgentChat in v0.4x provides similar abstractions to the default agents in v0.2x. The `CodingAssistantAgent` and `CodeExecutorAgent` in v0.4x are equivalent to the `AssistantAgent` and `UserProxyAgent` with code execution in v0.2x.
```

If you are exploring migrating your code from AutoGen 0.2x to 0.4x, the following are some key differences to consider:

1. In v0.4x, agent interactions are managed by `Teams` (e.g., `RoundRobinGroupChat`), replacing direct chat initiation.
2. v0.4x uses async/await syntax for improved performance and scalability.
3. Configuration in v0.4x is more modular, with separate components for code execution and LLM clients.
