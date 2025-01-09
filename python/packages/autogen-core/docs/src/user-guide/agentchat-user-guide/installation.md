---
myst:
  html_meta:
    "description lang=en": |
      Installing AutoGen AgentChat
---

# Installation

## Create a Virtual Environment (optional)

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
conda create -n autogen python=3.12
conda activate autogen
```

To deactivate later, run:

```bash
conda deactivate
```


`````



``````

## Install Using pip

Install the `autogen-agentchat` package using pip:

```bash

pip install -U "autogen-agentchat"
```

```{note}
Python 3.10 or later is required.
```

## Install OpenAI for Model Client

To use the OpenAI and Azure OpenAI models, you need to install the following
extensions:

```bash
pip install "autogen-ext[openai]"
```

If you are using Azure OpenAI with AAD authentication, you need to install the following:

```bash
pip install "autogen-ext[azure]==0.4.0.dev13"
```
