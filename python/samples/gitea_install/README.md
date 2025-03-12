# Gitea Install Example

Agentic installation of Gitea on Kubernetes using local Kubectl/Helm CLIs. 

## Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.
- Use VSCode to start the DevContainer defined in `/.devcontainer/`.

- Then install Python dependencies:
```bash
pip install "autogen-ext[openai,azure]"
```

## LLM Configuration

The LLM configuration should be defined in a `.env` file. 
Use `.env_example.yml` as a template.

## Kubernetes Configuration

The cluster configuration should be defined in a `kubeconfig` file. 
Use `kubeconfig_example` as a template.

## Running the example

- Navigate to `/workspaces/autogen/python/samples/gitea_install/` and execute: 

```bash
python main.py
```
