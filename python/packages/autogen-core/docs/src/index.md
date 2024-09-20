---
myst:
  html_meta:
    "description lang=en": |
      Top-level documentation for AGNext, a framework for building multi-agent applications with AI agents.
html_theme.sidebar_secondary.remove: false
---

# AGNext

AGNext is a OSS framework for developing intelligent applications using AI Agents patterns.
It offers an easy way to quickly build event-driven, distributed, scalable, resilient AI agent systems. Agents are developed by using the [Actor model](https://en.wikipedia.org/wiki/Actor_model). You can build and run your agent system locally and easily move to a distributed system in the cloud when you are ready.

Key features of AGNext are summarized below.

```{gallery-grid}
:grid-columns: 1 2 2 3

- header: "{fas}`network-wired;pst-color-primary` Asynchronous Messaging"
  content: "Agents communicate through asynchronous messages, enabling event-driven and request/response communication models."
- header: "{fas}`cube;pst-color-primary` Scalable & Distributed"
  content: "Enable complex scenarios with networks of agents across organizational boundaries."
- header: "{fas}`code;pst-color-primary` Multi-Language Support"
  content: "Python & Dotnet interoperating agents today, with more languages coming soon."
- header: "{fas}`globe;pst-color-primary` Modular & Extensible"
  content: "Highly customizable with features like custom agents, memory as a service, tools registry, and model library."
- header: "{fas}`puzzle-piece;pst-color-primary` Observable & Debuggable"
  content: "Easily trace and debug your agent systems."
- header: "{fas}`project-diagram;pst-color-primary` Event-Driven Architecture"
  content: "Build event-driven, distributed, scalable, and resilient AI agent systems."
```

<!--
Key features of AGNext include:

- Asynchronous messaging: Agents communicate with each other through asynchronous messages, enabling event-driven and request/response communication models.
- Scalable & Distributed: Enable complex scenarios with networks of agents across org boundaries
- Modular, extensible & highly customizable: E.g. custom agents, memory as a service, tools registry, model library
- x-lang support: Python & Dotnet interoperating agents today, others coming soon
- Observable, traceable & debuggable -->

```{seealso}
To start quickly, read the [Quick Start](user-guide/guides/quickstart) guide and follow the tutorial sections. To learn about the core concepts of AGNext, begin with [Agent and Multi-Agent Application](user-guide/core-concepts/agent-and-multi-agent-application).
```

```{toctree}
:maxdepth: 1
:hidden:

user-guide/index
```

<!-- ## Community

Information about the community that leads, supports, and develops AGNext.

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

<!-- ````{toctree}
:hidden:

Changelog <https://github.com/your-org/agnext/releases>
```   -->
