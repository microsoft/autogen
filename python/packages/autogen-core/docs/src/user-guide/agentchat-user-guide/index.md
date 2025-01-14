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

How to install AgentChat
:::

:::{grid-item-card} {fas}`rocket;pst-color-primary` Quickstart
:link: ./quickstart.html

Build your first agent
:::

:::{grid-item-card} {fas}`school;pst-color-primary` Tutorial
:link: ./tutorial/index.html

Step-by-step guide to using AgentChat, learn about agents, teams, and more
:::

:::{grid-item-card} {fas}`sitemap;pst-color-primary` Selector Group Chat
:link: ./selector-group-chat.html

Multi-agent coordination through a shared context and centralized, customizable selector
:::

:::{grid-item-card} {fas}`dove;pst-color-primary` Swarm
:link: ./swarm.html

Multi-agent coordination through a shared context and localized, tool-based selector
:::

:::{grid-item-card} {fas}`book;pst-color-primary` Magentic-One
:link: ./magentic-one.html

Get started with Magentic-One
:::

:::{grid-item-card} {fas}`code;pst-color-primary` Examples
:link: ./examples/index.html

Sample code and use cases
:::

:::{grid-item-card} {fas}`truck-moving;pst-color-primary` Migration Guide
:link: ./migration-guide.html

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
tutorial/human-in-the-loop
tutorial/termination
tutorial/custom-agents
tutorial/state
tutorial/declarative
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Advanced

selector-group-chat
swarm
magentic-one
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: More

examples/index
```
