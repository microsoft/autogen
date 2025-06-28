---
myst:
  html_meta:
    "description lang=en": |
      Tutorial for AgentChat, a high-level API for AutoGen
---

# Introduction

This tutorial provides a step-by-step guide to using AgentChat.
Make sure you have first followed the [installation instructions](../installation.md)
to prepare your environment.

At any point you are stuck, feel free to ask for help on
[GitHub Discussions](https://github.com/microsoft/autogen/discussions)
or [Discord](https://aka.ms/autogen-discord).

```{note}
If you are coming from AutoGen v0.2, please read the [migration guide](../migration-guide.md).
```

::::{grid} 2 2 2 2
:gutter: 3

:::{grid-item-card} {fas}`brain;pst-color-primary` Models
:link: ./models.html
:link-alt: Models: How to use LLM model clients

How to use LLM model clients
:::

:::{grid-item-card} {fas}`envelope;pst-color-primary` Messages
:link: ./messages.html
:link-alt: Messages: Understand the message types

Understand the message types
:::

:::{grid-item-card} {fas}`robot;pst-color-primary` Agents
:link: ./agents.html
:link-alt: Agents: Work with AgentChat agents and get started with autogen_agentchat.agents.AssistantAgent

Work with AgentChat agents and get started with {py:class}`~autogen_agentchat.agents.AssistantAgent`
:::

:::{grid-item-card} {fas}`exclamation-triangle;pst-color-primary` Tools and Error Handling
:link: ../../core-user-guide/components/tools.ipynb
:link-alt: Tools and Error Handling: Best practices for using tools and handling errors

Best practices for using tools, handling errors, and providing meaningful feedback
:::

:::{grid-item-card} {fas}`sitemap;pst-color-primary` Teams
:link: ./teams.html
:link-alt: Teams: Work with teams of agents and get started with autogen_agentchat.teams.RoundRobinGroupChat.

Work with teams of agents and get started with {py:class}`~autogen_agentchat.teams.RoundRobinGroupChat`.
:::

:::{grid-item-card} {fas}`person-chalkboard;pst-color-primary` Human-in-the-Loop
:link: ./human-in-the-loop.html
:link-alt: Human-in-the-Loop: Best practices for providing feedback to a team

Best practices for providing feedback to a team
:::

:::{grid-item-card} {fas}`circle-stop;pst-color-primary` Termination
:link: ./termination.html
:link-alt: Termination: Control a team using termination conditions

Control a team using termination conditions
:::

:::{grid-item-card} {fas}`code;pst-color-primary` Custom Agents
:link: ./custom-agents.html
:link-alt: Custom Agents: Create your own agents

Create your own agents
:::

:::{grid-item-card} {fas}`database;pst-color-primary` Managing State
:link: ./state.html
:link-alt: Managing State: Save and load agents and teams for persistent sessions

Save and load agents and teams for persistent sessions
:::
::::
