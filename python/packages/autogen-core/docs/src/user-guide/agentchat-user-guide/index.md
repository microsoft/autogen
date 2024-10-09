---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AgentChat, a high-level api for AutoGen
---

# AgentChat

AgentChat is a high-level package for building multi-agent applications built on top of the [ `autogen-core`](../core-user-guide/index.md) package. For beginner users, AgentChat is the recommended starting point. For advanced users, [ `autogen-core`](../core-user-guide/index.md) provides more flexibility and control over the underlying components.

AgentChat aims to provide intuitive defaults, such as **Agents** with preset behaviors and **Teams** with predefined communication protocols, to simplify building multi-agent applications.

```{tip}
If you are interested in implementing complex agent interaction behaviours, defining custom messaging protocols, or orchestration mechanisms, consider using the [ `autogen-core`](../core-user-guide/index.md) package.

```

## Agents

Agents provide presets for how an agent might respond to received messages. The following Agents are currently supported:

- `CodingAssistantAgent` - Generates responses using an LLM on receipt of a message
- `CodeExecutionAgent` - Extracts and executes code snippets found in received messages and returns the output
- `ToolUseAssistantAgent` - Responds with tool call messages based on received messages and a list of tool schemas provided at initialization

## Teams

Teams define how groups of agents communicate to address tasks. The following Teams are currently supported:

- `RoundRobinGroupChat` - A team where agents take turns sending messages (in a round robin fashion) until a termination condition is met
- `SelectorGroupChat` - A team where a model is used to select the next agent to send a message based on the current conversation history.

```{toctree}
:maxdepth: 1
:hidden:

quickstart
guides/index
examples/index
```
