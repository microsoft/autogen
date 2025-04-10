---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AutoGen Extensions, a framework for building multi-agent applications with AI agents.
---

# Extensions

```{toctree}
:maxdepth: 3
:hidden:

installation
discover
create-your-own
```

```{toctree}
:maxdepth: 3
:hidden:
:caption: Guides

azure-container-code-executor
```

AutoGen is designed to be extensible. The `autogen-ext` package contains the built-in component implementations maintained by the AutoGen project.

Examples of components include:

- `autogen_ext.agents.*` for agent implementations like {py:class}`~autogen_ext.agents.web_surfer.MultimodalWebSurfer`
- `autogen_ext.models.*` for model clients like {py:class}`~autogen_ext.models.openai.OpenAIChatCompletionClient` and {py:class}`~autogen_ext.models.semantic_kernel.SKChatCompletionAdapter` for connecting to hosted and local models.
- `autogen_ext.tools.*` for tools like GraphRAG {py:class}`~autogen_ext.tools.graphrag.LocalSearchTool` and {py:func}`~autogen_ext.tools.mcp.mcp_server_tools`.
- `autogen_ext.executors.*` for executors like {py:class}`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` and {py:class}`~autogen_ext.code_executors.azure.ACADynamicSessionsCodeExecutor`
- `autogen_ext.runtimes.*` for agent runtimes like {py:class}`~autogen_ext.runtimes.grpc.GrpcWorkerAgentRuntime`

See [API Reference](../../reference/index.md) for the full list of components and their APIs.

We strongly encourage developers to build their own components and publish them as part of the ecosytem.

::::{grid} 2 2 2 2
:gutter: 3

:::{grid-item-card} {fas}`magnifying-glass;pst-color-primary` Discover
:link: ./discover.html
:link-alt: Discover: Discover community extensions and samples

Discover community extensions and samples
:::

:::{grid-item-card} {fas}`code;pst-color-primary` Create your own
:link: ./create-your-own.html
:link-alt: Create your own: Create your own extension

Create your own extension
:::
::::
