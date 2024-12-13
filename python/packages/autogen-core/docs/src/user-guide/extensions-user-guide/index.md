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

azure-container-code-executor
```


## Discover community projects:

::::{grid} 1 2 2 2
:margin: 4 4 0 0
:gutter: 1

:::{grid-item-card} {fas}`globe;pst-color-primary` <br> Ecosystem
:link: https://github.com/topics/autogen
:class-item: api-card
:columns: 12

Find samples, services and other things that work with AutoGen

:::

:::{grid-item-card} {fas}`puzzle-piece;pst-color-primary` <br> Community Extensions
:link: https://github.com/topics/autogen-extension
:class-item: api-card

Find AutoGen extensions for 3rd party tools, components and services

:::

:::{grid-item-card} {fas}`vial;pst-color-primary` <br> Community Samples
:link: https://github.com/topics/autogen-sample
:class-item: api-card

Find community samples and examples of how to use AutoGen

:::

::::


### List of community projects

| Name | Package | Description |
|---|---|---|
| [autogen-watsonx-client](https://github.com/tsinggggg/autogen-watsonx-client)  | [PyPi](https://pypi.org/project/autogen-watsonx-client/) | Model client for [IBM watsonx.ai](https://www.ibm.com/products/watsonx-ai) |
| [autogen-openaiext-client](https://github.com/vballoli/autogen-openaiext-client)  | [PyPi](https://pypi.org/project/autogen-openaiext-client/) | Model client for other LLMs like Gemini, etc. through the OpenAI API |

<!-- Example -->
<!-- | [My Model Client](https://github.com/example)  | [PyPi](https://pypi.org/project/example) | Model client for my custom model service | -->
<!-- - Name should link to the project page or repo
- Package should link to the PyPi page
- Description should be a brief description of the project. 1 short sentence is ideal. -->


## Built-in extensions

Read docs for built in extensions:

```{note}
WIP
```

<!-- ::::{grid} 1 2 3 3
:margin: 4 4 0 0
:gutter: 1

:::{grid-item-card} LangChain Tools
:link: python/autogen_agentchat/autogen_agentchat
:link-type: doc
:::

:::{grid-item-card} ACA Dynamic Sessions Code Executor
:link: python/autogen_agentchat/autogen_agentchat
:link-type: doc
:::

:::: -->


## Creating your own community extension

With the new package structure in 0.4, it is easier than ever to create and publish your own extension to the AutoGen ecosystem. This page details some best practices so that your extension package  integrates well with the AutoGen ecosystem.

### Best practices

#### Naming

There is no requirement about naming. But prefixing the package name with `autogen-` makes it easier to find.

#### Common interfaces

Whenever possible, extensions should implement the provided interfaces from the `autogen_core` package. This will allow for a more consistent experience for users.

##### Dependency on AutoGen

To ensure that the extension works with the version of AutoGen that it was designed for, it is recommended to specify the version of AutoGen the dependency section of the `pyproject.toml` with adequate constraints.

```toml
[project]
# ...
dependencies = [
    "autogen-core>=0.4,<0.5"
]
```

#### Usage of typing

AutoGen embraces the use of type hints to provide a better development experience. Extensions should use type hints whenever possible.

### Discovery

To make it easier for users to find your extension, sample, service or package, you can [add the topic](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics) [`autogen`](https://github.com/topics/autogen) to the GitHub repo.

More specific topics are also available:

- [`autogen-extension`](https://github.com/topics/autogen-extension) for extensions
- [`autogen-sample`](https://github.com/topics/autogen-sample) for samples

### Changes from 0.2

In AutoGen 0.2 it was common to merge 3rd party extensions and examples into the main repo. We are super appreciative of all of the users who have contributed to the ecosystem notebooks, modules and pages in 0.2. However, in general we are moving away from this model to allow for more flexibility and to reduce maintenance burden.

There is the `autogen-ext` package for 1st party supported extensions, but we want to be selective to manage maintenance load. If you would like to see if your extension makes sense to add into `autogen-ext`, please open an issue and let's discuss. Otherwise, we encourage you to publish your extension as a separate package and follow the guidance under [discovery](#discovery) to make it easy for users to find.
