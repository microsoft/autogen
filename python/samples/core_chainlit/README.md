# Core ChainLit Integration Sample

In this sample, we will demonstrate how to build simple chat interface that
interacts with a [Core](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/index.html)
agent or a team, using [Chainlit](https://github.com/Chainlit/chainlit),
and support streaming messages.

## Overview

The `core_chainlit` sample is designed to illustrate a simple use case of ChainLit integrated with a single-threaded agent runtime. It includes the following components:

- **Single Agent**: A single agent that operates within the ChainLit environment.
- **Group Chat**: A group chat setup featuring two agents:
  - **Assistant Agent**: This agent responds to user inputs.
  - **Critic Agent**: This agent reflects on and critiques the responses from the Assistant Agent.
- **Closure Agent**: Utilizes a closure agent to aggregate output messages into an output queue.
- **Token Streaming**: Demonstrates how to stream tokens to the user interface.
- **Session Management**: Manages the runtime and output queue within the ChainLit user session.

## Requirements

To run this sample, you will need:
- Python 3.8 or higher
- Installation of necessary Python packages as listed in `requirements.txt`

## Installation

To run this sample, you will need to install the following packages:

```shell

```

To use other model providers, you will need to install a different extra
for the `autogen-ext` package.
See the [Models documentation](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html) for more information.

## Model Configuration

Create a configuration file named `model_config.yaml` to configure the model
you want to use. Use `model_config_template.yaml` as a template.


## Running the Agent Sample

The first sample demonstrate how to interact with a single AssistantAgent
from the chat interface.

```shell
chainlit run app_agent.py -h
```

