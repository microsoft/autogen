# ArgoCD Install Example

Agentic installation of ArgoCD on Kubernetes using local Kubectl/Helm CLIs. 

## Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.
- Use VSCode to start the DevContainer defined in `/.devcontainer/`.

- Then install Python dependencies:
```bash
pip install "autogen-ext[openai,azure]"
python3 -m pip install python-dotenv
pip install autogen_agentchat playwright
```

## LLM Configuration

The LLM configuration should be defined in a `.env` file. 
Use `.env_example.yml` as a template.

## Other Environment Variables

In your `.env` file, also include the following: 
- REPO_URL - Git repo used for storing ArgoCD App configs
- REPO_PAT - Token (Fine-grained recommended) for accessing your Git repo at REPO_URL. 
- KUBECONFIG - path to your kubeconfig file in the following section

## Kubernetes Configuration

The cluster configuration should be defined in a `kubeconfig` file. 
Use `kubeconfig_example` as a template.

## Running the example

- Navigate to `/workspaces/autogen/python/samples/argocd_install/` and execute: 

```bash
python main.py
```
