---
myst:
  html_meta:
    "description lang=en": |
      AutoGen packages provide a set of functionality for building multi-agent applications with AI agents.
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

(pkg-info-autogen-agentchat)=

:::{card} {fas}`people-group;pst-color-primary` AutoGen AgentChat
:class-title: card-title
:shadow: none

Library that is at a similar level of abstraction as AutoGen 0.2, including default agents and group chat.

```sh
pip install autogen-agentchat==0.4.0.dev2
```

[{fas}`circle-info;pst-color-primary` User Guide](/user-guide/agentchat-user-guide/index.md) | [{fas}`file-code;pst-color-primary` API Reference](/reference/python/autogen_agentchat/autogen_agentchat.rst) | [{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-agentchat/0.4.0.dev2/) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-agentchat)
:::

(pkg-info-autogen-core)=

:::{card} {fas}`cube;pst-color-primary` AutoGen Core
:class-title: card-title
:shadow: none

Implements the core functionality of the AutoGen framework, providing basic building blocks for creating multi-agent systems.

```sh
pip install autogen-core==0.4.0.dev2
```

[{fas}`circle-info;pst-color-primary` User Guide](/user-guide/core-user-guide/index.md) | [{fas}`file-code;pst-color-primary` API Reference](/reference/python/autogen_core/autogen_core.rst) | [{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-core/0.4.0.dev2/) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-core)
:::

(pkg-info-autogen-ext)=

:::{card} {fas}`puzzle-piece;pst-color-primary` AutoGen Extensions
:class-title: card-title
:shadow: none

Implementations of core components that interface with external services, or use extra dependencies. For example, Docker based code execution.

```sh
pip install autogen-ext==0.4.0.dev2
```

Extras:

- `langchain` needed for {py:class}`~autogen_ext.tools.LangChainToolAdapter`
- `azure` needed for {py:class}`~autogen_ext.code_executors.ACADynamicSessionsCodeExecutor`
- `docker` needed for {py:class}`~autogen_ext.code_executors.DockerCommandLineCodeExecutor`
- `openai` needed for {py:class}`~autogen_ext.models.OpenAIChatCompletionClient`

[{fas}`circle-info;pst-color-primary` User Guide](/user-guide/extensions-user-guide/index.md) | [{fas}`file-code;pst-color-primary` API Reference](/reference/python/autogen_ext/autogen_ext.rst) | [{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogen-ext/0.4.0.dev2/) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-ext)
:::

(pkg-info-autogen-magentic-one)=

:::{card} {fas}`users;pst-color-primary` Magentic One
:class-title: card-title
:shadow: none

A generalist multi-agent softbot utilizing five agents to tackle intricate tasks involving multi-step planning and real-world actions.

```{note}
Not yet available on PyPI.
```

[{fab}`github;pst-color-primary` Source](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-magentic-one)
:::

(pkg-info-autogenbench)=

:::{card} {fas}`chart-bar;pst-color-primary` AutoGen Bench
:class-title: card-title
:shadow: none

AutoGenBench is a tool for repeatedly running pre-defined AutoGen tasks in tightly-controlled initial conditions.

```sh
pip install autogenbench
```

[{fab}`python;pst-color-primary` PyPI](https://pypi.org/project/autogenbench/) | [{fab}`github;pst-color-primary` Source](https://github.com/microsoft/autogen/tree/main/python/packages/agbench)
:::
