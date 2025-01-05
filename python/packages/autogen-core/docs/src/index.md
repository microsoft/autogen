---
myst:
  html_meta:
    "description lang=en": |
      Top-level documentation for AutoGen, a framework for developing applications using AI agents
html_theme.sidebar_secondary.remove: false
sd_hide_title: true
---

<style>
.hero-title {
  font-size: 60px;
  font-weight: bold;
  margin: 2rem auto 0;
}

.wip-card {
  border: 1px solid var(--pst-color-success);
  background-color: var(--pst-color-success-bg);
  border-radius: .25rem;
  padding: 0.3rem;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 1rem;
}
</style>

# AutoGen

<div class="container">
<div class="row text-center">
<div class="col-sm-12">
<h1 class="hero-title">
AutoGen
</h1>
<h3>
A framework for building AI agents and multi-agent applications
</h3>
</div>
</div>
</div>

<div style="margin-top: 2rem;">

::::{grid}
:gutter: 2

:::{grid-item-card}
:shadow: none
:margin: 2 0 0 0
:columns: 12 12 6 6

<div class="sd-card-title sd-font-weight-bold docutils">

{fas}`book;pst-color-primary`
Magentic-One </div>
A multi-agent team for web and file-based tasks.
Built on top of AgentChat.

```bash
% m1 "Find flights from Seattle to Paris and format the result in a table"
```

+++

```{button-ref} user-guide/agentchat-user-guide/magentic-one
:color: secondary

Get Started
```

:::

:::{grid-item-card} {fas}`palette;pst-color-primary` Studio [![PyPi autogenstudio](https://img.shields.io/badge/PyPi-autogen--studio-blue?logo=pypi)](https://pypi.org/project/autogenstudio/)
:shadow: none
:margin: 2 0 0 0
:columns: 12 12 6 6

Prototyping, testing and managing multi-agent teams without writing code.
Built on top of AgentChat.

```bash
% autogenstudio ui --port 8080
```

+++

```{button-ref} user-guide/autogenstudio-user-guide/index
:color: secondary

Get Started
```

:::

:::{grid-item-card}
:shadow: none
:margin: 2 0 0 0
:columns: 12 12 12 12

<div class="sd-card-title sd-font-weight-bold docutils">

{fas}`people-group;pst-color-primary` AgentChat
[![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/0.4.0.dev13/)

</div>
Preset agents and teams for building conversational single and multi-agent applications.
Built on top of Core.

```python
from autogen_agentchat import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

agent = AssistantAgent("assistant", OpenAIChatCompletionClient(model="gpt-4o"))
```

_Migrating from AutoGen 0.2? Read the [guide](./user-guide/agentchat-user-guide/migration-guide.md)._

+++

```{button-ref} user-guide/agentchat-user-guide/quickstart
:color: secondary

Get Started
```

:::

:::{grid-item-card} {fas}`cube;pst-color-primary` Core [![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/0.4.0.dev13/)
:shadow: none
:margin: 2 0 0 0
:columns: 12 12 12 12

Foundational building blocks for asynchronous and event driven multi-agent systems. Examples scenarios:

* Deterministic and dynamic agentic workflows for business processes.
* Research on multi-agent collaboration.
* Parallel training data generation for agentic models.
* Distributed agents for multi-language applications.

+++

```{button-ref} user-guide/core-user-guide/quickstart
:color: secondary

Get Started
```

:::

:::{grid-item-card} {fas}`puzzle-piece;pst-color-primary` Extensions [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/0.4.0.dev13/)
:shadow: none
:margin: 2 0 0 0
:columns: 12 12 12 12

Implementations of Core and AgentChat components that interface with external services or other libraries.
You can find and use community extensions or create your own. Examples of built-in extensions:

* {py:class}`~autogen_ext.tools.langchain.LangChainToolAdapter` for using LangChain tools.
* {py:class}`~autogen_ext.agents.openai.OpenAIAssistantAgent` for using Assistant API.
* {py:class}`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` for running model-generated code in a Docker container.
* {py:class}`~autogen_ext.runtimes.grpc.GrpcWorkerAgentRuntime` for distributed agents.

+++

<a class="sd-sphinx-override sd-btn sd-text-wrap sd-btn-secondary reference internal" href="user-guide/extensions-user-guide/discover.html"><span class="doc">Discover Community Extensions</span></a>
<a class="sd-sphinx-override sd-btn sd-text-wrap sd-btn-secondary reference internal" href="user-guide/extensions-user-guide/create-your-own.html"><span class="doc">Create New Extension</span></a>

:::

::::

</div>

```{toctree}
:maxdepth: 3
:hidden:

user-guide/agentchat-user-guide/index
user-guide/core-user-guide/index
user-guide/extensions-user-guide/index
Studio <user-guide/autogenstudio-user-guide/index>
reference/index
```
