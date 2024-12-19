---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AutoGen Extensions, a framework for building multi-agent applications with AI agents.
---

# Installation

First-part maintained extensions are available in the `autogen-ext` package.


```sh
pip install 'autogen-ext==0.4.0.dev11'
```

Extras:

- `langchain` needed for {py:class}`~autogen_ext.tools.langchain.LangChainToolAdapter`
- `azure` needed for {py:class}`~autogen_ext.code_executors.azure.ACADynamicSessionsCodeExecutor`
- `docker` needed for {py:class}`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor`
- `openai` needed for {py:class}`~autogen_ext.models.openai.OpenAIChatCompletionClient`

