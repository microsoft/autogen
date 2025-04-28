---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AgentChat, a high-level API for AutoGen
---

# AgentChat

AgentChat is a high-level API for building multi-agent applications.
It is built on top of the [`autogen-core`](../core-user-guide/index.md) package.
For beginner users, AgentChat is the recommended starting point.
For advanced users, [`autogen-core`](../core-user-guide/index.md)'s event-driven
programming model provides more flexibility and control over the underlying components.

AgentChat provides intuitive defaults, such as **Agents** with preset
behaviors and **Teams** with predefined [multi-agent design patterns](../core-user-guide/design-patterns/intro.md).

::::{grid} 2 2 2 2
:gutter: 3

:::{grid-item-card} {fas}`download;pst-color-primary` Installation
:link: ./installation.html
:link-alt: Installation: How to install AgentChat

How to install AgentChat
:::

:::{grid-item-card} {fas}`rocket;pst-color-primary` Quickstart
:link: ./quickstart.html
:link-alt: Quickstart: Build your first agent

Build your first agent
:::

:::{grid-item-card} {fas}`school;pst-color-primary` Tutorial
:link: ./tutorial/index.html
:link-alt: Tutorial: Step-by-step guide to using AgentChat, learn about agents, teams, and more

Step-by-step guide to using AgentChat, learn about agents, teams, and more
:::

:::{grid-item-card} {fas}`wrench;pst-color-primary` Custom Agents
:link: ./custom-agents.html
:link-alt: Custom Agents: Create your own agents with custom behaviors

Create your own agents with custom behaviors
:::

:::{grid-item-card} {fas}`sitemap;pst-color-primary` Selector Group Chat
:link: ./selector-group-chat.html
:link-alt: Selector Group Chat: Multi-agent coordination through a shared context and centralized, customizable selector

Multi-agent coordination through a shared context and centralized, customizable selector
:::

:::{grid-item-card} {fas}`dove;pst-color-primary` Swarm
:link: ./swarm.html
:link-alt: Swarm: Multi-agent coordination through a shared context and localized, tool-based selector

Multi-agent coordination through a shared context and localized, tool-based selector
:::

:::{grid-item-card} {fas}`book;pst-color-primary` Magentic-One
:link: ./magentic-one.html
:link-alt: Magentic-One: Get started with Magentic-One

Get started with Magentic-One
:::

:::{grid-item-card} {fas}`brain;pst-color-primary` Memory
:link: ./memory.html
:link-alt: Memory: Add memory capabilities to your agents

Add memory capabilities to your agents
:::

:::{grid-item-card} {fas}`file;pst-color-primary` Logging
:link: ./logging.html
:link-alt: Logging: Log traces and internal messages

Log traces and internal messages
:::

:::{grid-item-card} {fas}`save;pst-color-primary` Serialize Components
:link: ./serialize-components.html
:link-alt: Serialize Components: Serialize and deserialize components

Serialize and deserialize components
:::

:::{grid-item-card} {fas}`code;pst-color-primary` Examples
:link: ./examples/index.html
:link-alt: Examples: Sample code and use cases

Sample code and use cases
:::

:::{grid-item-card} {fas}`truck-moving;pst-color-primary` Migration Guide
:link: ./migration-guide.html
:link-alt: Migration Guide: How to migrate from AutoGen 0.2.x to 0.4.x.

How to migrate from AutoGen 0.2.x to 0.4.x.
:::
::::

```{toctree}
:maxdepth: 1
:hidden:

installation
quickstart
migration-guide
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Tutorial

tutorial/index
tutorial/models
tutorial/messages
tutorial/agents
tutorial/teams
tutorial/graph
tutorial/human-in-the-loop
tutorial/termination
tutorial/state

```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Advanced

custom-agents
selector-group-chat
swarm
magentic-one
memory
logging
serialize-components
tracing

```

```{toctree}
:maxdepth: 1
:hidden:
:caption: More

examples/index
```
