---
myst:
  html_meta:
    "description lang=en": |
      Tutorial for AutoGen AgentChat, a framework for building multi-agent applications with AI agents.
---

# Tutorial

Get started with AgentChat through this comprehensive tutorial.

::::{grid} 2 2 2 3
:gutter: 3

:::{grid-item-card} {fas}`book-open;pst-color-primary` Models
:link: ./models.html

Setting up model clients for agents and teams.
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Agents
:link: ./agents.html

Building agents that use models, tools, and code executors.
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Teams Intro
:link: ./teams.html

Introduction to teams and task termination.
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Selector Group Chat
:link: ./selector-group-chat.html

A smart team that uses a model-based strategy and custom selector.
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Swarm
:link: ./swarm.html

A dynamic team that uses handoffs to pass tasks between agents.
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Custom Agents
:link: ./custom-agents.html

How to build custom agents.
:::

::::

```{toctree}
:maxdepth: 1
:hidden:

models
agents
teams
selector-group-chat
swarm
termination
custom-agents
```
