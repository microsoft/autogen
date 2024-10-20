---
myst:
  html_meta:
    "description lang=en": |
      Tutorial for AutoGen AgentChat, a framework for building multi-agent applications with AI agents.
---

# Tutorial

::::{grid} 2 2 2 3
:gutter: 3
:padding-bottom: 2

:::{grid-item-card} {fas}`book-open;pst-color-primary` Introduction
:link: ./introduction.html

Overview of agents and teams in AgentChat
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Agents
:link: ./agents.html

Building agents that use LLMs, tools, and execute code.
:::

:::{grid-item-card} {fas}`users;pst-color-primary` Teams  
:link: ./teams.html

Coordinating multiple agents in teams.
:::

:::{grid-item-card} {fas}`flag-checkered;pst-color-primary` Chat Termination
:link: ./termination.html

Determining when to end a task.
:::

<!-- :::{grid-item-card} {fas}`toolbox;pst-color-primary` Using Tools
:link: ./tool_use.html

Adding tools to agents
:::

:::{grid-item-card} {fas}`code;pst-color-primary` Code Execution
:link: ./code-execution.html

Agents that execute code snippets.
:::

:::: -->

```{toctree}
:maxdepth: 1
:hidden:

introduction
agents
teams
termination
```
