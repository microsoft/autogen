# autogen OPA Tool Authorization

Open Policy Agent (OPA) authorization for AutoGen tool calls and agent handoffs.

## Overview

`autogen_ext.tools.opa` wraps any `BaseTool` — including agent handoff tools
(`transfer_to_<Agent>`) — and evaluates every call against an OPA policy
**before** execution. Zero changes to `autogen-core` or `autogen-agentchat`.

```
LLM → AssistantAgent → OPAAuthorizedTool.run_json()
                              ↓
                  POST /v1/data/autogen/tools/allow
                              ↓
              {"result": true}  →  inner_tool.run_json()
              {"result": false} →  OPAAuthorizationError
```

## Quick Start

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool
from autogen_ext.tools.opa import opa_authorize_tools

def web_search(query: str) -> str: ...
def delete_file(path: str) -> str: ...

agent = AssistantAgent(
    name="PlannerAgent",
    model_client=...,
    tools=opa_authorize_tools(
        [FunctionTool(web_search, ...), FunctionTool(delete_file, ...)],
        opa_url="http://localhost:8181",
        context={"user": "alice", "role": "analyst"},
    ),
)
```

## Behavior When OPA Is Unreachable

| `fail_open` | OPA down | Result |
|---|---|---|
| `False` (default) | OPA down | `OPAConnectionError` raised |
| `True` | OPA down | Tool call proceeds (warning logged) |

## Loading the Sample Policy

```bash
opa run --server &
curl -X PUT http://localhost:8181/v1/policies/autogen_tools \
  -H "Content-Type: text/plain" \
  --data-binary @policies/autogen_tools.rego
```
