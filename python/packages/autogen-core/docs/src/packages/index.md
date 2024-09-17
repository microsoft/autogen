---
myst:
  html_meta:
    "description lang=en": |
      AGNext packages provide a set of functionality for building multi-agent applications with AI agents.
html_theme.nosidebar: true
---

<style>
.card-title {
  font-size: 1.2rem;
  font-weight: bold;
}

.card-title svg {
  font-size: 2rem;
  vertical-align: bottom;
  margin-right: 5px;
}
</style>

# Packages

:::{card} {fas}`cube;pst-color-primary` AutoGen Core
:class-title: card-title

Implements the core functionality of the AGNext framework, providing basic building blocks for creating multi-agent systems.

```sh
pip install autogen-core
```

[{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-core/) | [{fas}`file-code;pst-color-primary` API Reference](/reference/index.md) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/agnext/tree/main/python/packages/autogen-core)
:::

:::{card} {fas}`people-group;pst-color-primary` AutoGen AgentChat
:class-title: card-title

Library that is at a similar level of abstraction as AutoGen 0.2, including default agents and group chat.

```sh
pip install autogen-agentchat
```

[{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-agentchat/) | [{fas}`file-code;pst-color-primary` API Reference](/reference/index.md) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/agnext/tree/main/python/packages/autogen-agentchat)
:::


:::{card} {fas}`puzzle-piece;pst-color-primary` AutoGen Extensions
:class-title: card-title

Implementations of core components that interface with external services, or use extra dependencies. For example, Docker based code execution.

```sh
pip install autogen-ext
```

[{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-ext/) | [{fas}`file-code;pst-color-primary` API Reference](/reference/index.md) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/agnext/tree/main/python/packages/autogen-ext)
:::


:::{card} {fas}`users;pst-color-primary` TeamOne
:class-title: card-title

A generalist multi-agent softbot utilizing five agents to tackle intricate tasks involving multi-step planning and real-world actions.

```sh
pip install autogen-team-one
```

[{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-team-one/) | [{fas}`file-code;pst-color-primary` API Reference](/reference/index.md) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/agnext/tree/main/python/packages/team-one)
:::

:::{card} {fas}`chart-bar;pst-color-primary` AutoGen Bench
:class-title: card-title

AutoGenBench is a tool for repeatedly running pre-defined AutoGen tasks in tightly-controlled initial conditions.

```sh
pip install autogenbench
```

[{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogenbench/) | [{fas}`file-code;pst-color-primary` API Reference](/reference/index.md) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/agnext/tree/main/python/packages/agbench)
:::
