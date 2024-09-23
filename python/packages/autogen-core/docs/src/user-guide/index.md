---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AutoGen, a framework for building multi-agent applications with AI agents.
---

# User Guide

AutoGen is a flexible framework for building multi-agent systems. Begin with the [installation](guides/installation.md) guide to set up the framework on your machine. Then, follow the [quickstart](guides/quickstart) guide to get started with building your first multi-agent application.

```{danger}
This project and documentation is a work in progress. If you have any questions or need help, please reach out to us on GitHub.
```

```{toctree}
:caption: Getting Started
:maxdepth: 1
:hidden:

guides/installation
guides/quickstart
```

```{toctree}
:caption: Core Concepts
:maxdepth: 1
:hidden:


core-concepts/agent-and-multi-agent-application
core-concepts/architecture
core-concepts/api-layers
core-concepts/application-stack
core-concepts/agent-identity-and-lifecycle
core-concepts/topic-and-subscription
core-concepts/faqs

```

```{toctree}
:caption: Framework
:maxdepth: 1
:hidden:

guides/agent-and-agent-runtime
guides/message-and-communication
guides/model-clients
guides/tools
guides/logging
guides/distributed-agent-runtime
guides/telemetry
guides/command-line-code-executors
```

```{toctree}
:caption: Multi-Agent Design Patterns
:maxdepth: 1
:hidden:

guides/multi-agent-design-patterns
guides/group-chat
guides/reflection
```

```{toctree}
:caption: Cookbook
:maxdepth: 1
:hidden:

cookbook/azure-openai-with-aad-auth
cookbook/termination-with-intervention
cookbook/extracting-results-with-an-agent
cookbook/openai-assistant-agent
cookbook/langgraph-agent
cookbook/llamaindex-agent
cookbook/local-llms-ollama-litellm

```
