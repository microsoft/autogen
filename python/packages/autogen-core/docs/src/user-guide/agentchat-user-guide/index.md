---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AgentChat, a high-level api for AutoGen
---

# AgentChat

AgentChat is a high-level package for building multi-agent applications built on top of the [ `autogen-core`](../core-user-guide/index.md) package. For beginner users, AgentChat is the recommended starting point. For advanced users, [ `autogen-core`](../core-user-guide/index.md) provides more flexibility and control over the underlying components.

AgentChat aims to provide intuitive defaults, such as **Agents** with preset behaviors and **Teams** with predefined communication protocols, to simplify building multi-agent applications.

```{include} warning.md

```

```{tip}
If you are interested in implementing complex agent interaction behaviours, defining custom messaging protocols, or orchestration mechanisms, consider using the [ `autogen-core`](../core-user-guide/index.md) package.

```

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
