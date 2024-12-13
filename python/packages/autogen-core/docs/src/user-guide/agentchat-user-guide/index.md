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
behaviors and **Teams** with predefined [multi-agent design patterns](../core-user-guide/design-patterns/index.md).


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

:::{grid-item-card} {fas}`graduation-cap;pst-color-primary` Tutorial
:link: ./tutorial/index.html

Step-by-step guide to using AgentChat
:::

:::{grid-item-card} {fas}`code;pst-color-primary` Examples
:link: ./examples/index.html

Sample code and use cases
:::
::::

```{toctree}
:maxdepth: 1
:hidden:

installation
quickstart
tutorial/index
examples/index
```
