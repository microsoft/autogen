---
myst:
  html_meta:
    "description lang=en": |
      Installing AutoGen AgentChat
---

# Installation

## Create a virtual environment (optional)

When installing AgentChat locally, we recommend using a virtual environment for the installation. This will ensure that the dependencies for AgentChat are isolated from the rest of your system.

``````{tab-set}

`````{tab-item} venv

Create and activate:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

To deactivate later, run:

```bash
deactivate
```

`````

`````{tab-item} conda

[Install Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html) if you have not already.


Create and activate:

```bash
conda create -n autogen python=3.10
conda activate autogen
```

To deactivate later, run:

```bash
conda deactivate
```


`````



``````

## Intall the AgentChat package using pip

Install the `autogen-agentchat` package using pip:

```bash

pip install 'autogen-agentchat==0.4.0.dev7'
```

```{note}
Python 3.10 or later is required.
```

## Install OpenAI for Model Client

To use the OpenAI and Azure OpenAI models, you need to install the following
extensions:

```bash
pip install 'autogen-ext[openai]==0.4.0.dev7'
```

## Install Docker for Code Execution

We recommend using Docker for code execution.
To install Docker, follow the instructions for your operating system on the [Docker website](https://docs.docker.com/get-docker/).

A simple example of how to use Docker for code execution is shown below:

<!-- ```{include} stocksnippet.md

``` -->

To learn more about agents that execute code, see the [agents tutorial](./tutorial/agents.ipynb).
