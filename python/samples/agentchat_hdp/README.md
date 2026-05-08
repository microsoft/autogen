# AgentChat — HDP Delegation Provenance

This sample shows how to attach a **cryptographic audit trail** to any AutoGen AgentChat
conversation using [HDP (Human Delegation Provenance)](https://github.com/Helixar-AI/HDP).

When a human authorises an agent to act — and that agent delegates to another agent —
HDP creates a tamper-evident chain of Ed25519 signatures from the authorising human to
every downstream action. The chain is verifiable fully **offline** with a single public key.

## What it covers

| Scenario | File |
|---|---|
| Single `AssistantAgent` with HDP scope enforcement | `single_agent.py` |
| Multi-agent `RoundRobinGroupChat` with per-turn delegation tracking | `group_chat.py` |
| Offline chain verification after a session | both files |

## Setup

Install dependencies:

```bash
pip install "autogen-agentchat" "autogen-ext[openai]" "hdp-autogen>=0.1.3" pyyaml
```

> **`hdp-autogen`** is the AutoGen middleware published by [Helixar](https://github.com/Helixar-AI/HDP).
> It wraps any `ConversableAgent` or `GroupChatManager` with zero changes to your agent code.

Create `model_config.yaml` in this directory (same format as other AgentChat samples):

```yaml
provider: autogen_ext.models.openai.OpenAIChatCompletionClient
config:
  model: gpt-4o
  api_key: YOUR_API_KEY   # or set OPENAI_API_KEY in your environment
```

Generate an Ed25519 signing key once and store it in an environment variable:

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64, os

key = Ed25519PrivateKey.generate()
raw = key.private_bytes_raw()
print("HDP_SIGNING_KEY=" + base64.urlsafe_b64encode(raw).decode())
# → export HDP_SIGNING_KEY=<value>
```

## Run

```bash
# Multi-agent group chat with delegation chain
python group_chat.py

# Single agent with scope enforcement
python single_agent.py
```

## How it works

HDP tokens are compact, self-contained JSON objects signed with Ed25519.
Each delegation hop appends a new signed entry to the chain. `verify_chain()`
validates every signature offline — no network call, no central registry.

```
Human (Alice)
  └── Root token  [signed by Alice's key]
        └── Hop 0: orchestrator-agent  [signed over root]
              └── Hop 1: research-agent  [signed over hop 0]
                    └── Hop 2: writer-agent  [signed over hop 1]
```

The chain records: *who authorised*, *what scope*, *which agents acted*, and *when*.
Any modification of any hop is immediately detectable at verification time.

## Further reading

- [HDP protocol specification and docs](https://helixar.ai/about/labs/hdp/)
- [`hdp-autogen` package on PyPI](https://pypi.org/project/hdp-autogen/)
- [HDP GitHub repository](https://github.com/Helixar-AI/HDP)
- [IETF draft: draft-helixar-hdp-agentic-delegation](https://datatracker.ietf.org/doc/draft-helixar-hdp-agentic-delegation/)
- [Community discussion: accountability in multi-agent systems](https://github.com/microsoft/autogen/discussions/7485)
