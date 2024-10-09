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


::::{grid} 1 1 2 2

:::{grid-item-card} {fas}`people-group;pst-color-primary` AgentChat
:shadow: none
:margin: 2 0 0 0

High-level API that includes preset agents and teams for building multi-agent systems.

```sh
pip install autogen-agentchat==0.4.0dev0
```

💡 *Start here if you are looking for an API similar to AutoGen 0.2*

+++

```{button-ref} user-guide/agentchat-user-guide/quickstart
:color: secondary

Get Started
```

:::
:::{grid-item-card} {fas}`cube;pst-color-primary` Core
:shadow: none
:margin: 2 0 0 0

Provides building blocks for creating asynchronous, event driven multi-agent systems.

```sh
pip install autogen-core==0.4.0dev0
```

+++

```{button-ref} user-guide/core-user-guide/quickstart
:color: secondary

Get Started
```

:::
::::

</div>

```{toctree}
:maxdepth: 3
:hidden:

user-guide/index
packages/index
reference/index
```
