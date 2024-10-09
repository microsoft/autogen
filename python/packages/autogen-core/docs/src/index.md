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
A framework for developing applications using AI agents
</h3>
</div>
</div>


<div class="row">

<div class="col-sm">
<h2 class="text-center">

{fas}`people-group;pst-color-primary` AgentChat

</h2>

<p>
Task driven, high level APIs for building multi-agent systems. Including group chat, pre-built agents, and more.

Built with <i>core</i>.
<p>

```sh
pip install autogen-agentchat==0.4.0dev0
```

<button onclick="location.href='agentchat-user-guide/guides/quickstart.html'" type="button" class="btn btn-primary">Get Started</button>
<button onclick="location.href='reference/python/autogen_agentchat/autogen_agentchat.html'" type="button" class="btn btn-outline-secondary">API Reference</button>

<div class="versionadded">
<p>Start here if you are looking for an API similar to AutoGen 0.2</p>
</div>

</div>
<div class="col-sm">
<h2 class="text-center">

{fas}`cube;pst-color-primary` Core

</h2>

<p>
Primitive building blocks for creating asynchronous, event driven multi-agent systems.
<p>

```sh
pip install autogen-core==0.4.0dev0
```

<button onclick="location.href='core-user-guide/guides/quickstart.html'" type="button" class="btn btn-primary">Get Started</button>
<button onclick="location.href='reference/python/autogen_core/autogen_core.html'" type="button" class="btn btn-outline-secondary">API Reference</button>

</div>

</div>
</div>

<!--
Key features of AutoGen include:

- Asynchronous messaging: Agents communicate with each other through asynchronous messages, enabling event-driven and request/response communication models.
- Scalable & Distributed: Enable complex scenarios with networks of agents across org boundaries
- Modular, extensible & highly customizable: E.g. custom agents, memory as a service, tools registry, model library
- x-lang support: Python & Dotnet interoperating agents today, others coming soon
- Observable, traceable & debuggable -->

```{toctree}
:maxdepth: 1
:hidden:

agentchat-user-guide/index
core-user-guide/index
```

<!-- ## Community

Information about the community that leads, supports, and develops AutoGen.

```{toctree}
:maxdepth: 2

community/index
``` -->

```{toctree}
:maxdepth: 2
:hidden:
packages/index
```

```{toctree}
:maxdepth: 1
:hidden:
reference/index
```

