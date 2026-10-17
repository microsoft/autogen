# Governance Workbench

A governance wrapper for AutoGen workbenches that enforces structural authority separation on tool calls.

## The Problem

In a GroupChat, agents propose and execute tool calls with no authorization boundary between intent and action. An agent tasked with "research competitors" can call any tool its workbench exposes — file writes, shell commands, network requests — without policy evaluation.

## The Solution: PROPOSE / DECIDE / PROMOTE

`GovernanceWorkbench` wraps any existing `Workbench` and interposes deterministic policy evaluation on every `call_tool` invocation:

| Phase | What Happens | Who Decides |
|-------|-------------|-------------|
| **PROPOSE** | Convert tool call into structured intent with SHA-256 hash | Automatic |
| **DECIDE** | Evaluate intent against policy rules (pure function, no LLM) | Policy |
| **PROMOTE** | Forward approved calls; return error `ToolResult` for denied | Verdict |

Denied calls return `ToolResult(is_error=True)` — no exception, no disruption to the GroupChat loop. The agent sees a denial message and adjusts.

## Usage

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.tools.langchain import LangChainToolAdapter
from governance_workbench import GovernanceWorkbench

# Your existing workbench
inner_workbench = ...

# Define policy: fail-closed, explicit approvals
policy = {
    "default": "deny",
    "rules": [
        {"tools": ["search", "read_file"], "verdict": "approve"},
        {"tools": ["write_file"], "verdict": "deny"},
        {
            "tools": ["shell"],
            "verdict": "approve",
            "constraints": {"blocked_patterns": ["rm -rf", "sudo"]},
        },
    ],
}

# Wrap it
governed = GovernanceWorkbench(
    inner=inner_workbench,
    policy=policy,
    witness_path="./governance_witness.jsonl",
)

# Use with any agent
agent = AssistantAgent(
    name="researcher",
    model_client=model_client,
    workbench=governed,  # <-- governance applied here
)
```

## Design Principles

1. **Deterministic** — `_decide()` is a pure function. Same intent + policy = same verdict.
2. **Fail-closed** — unknown tools default to `deny`.
3. **Non-disruptive** — denied calls return error results, not exceptions. The GroupChat continues.
4. **Auditable** — hash-chained witness log records every verdict.

## Going Further

For a standalone implementation with YAML policy files, multiple presets, and adversarial test coverage, see [Governance-Guard](https://github.com/MetaCortex-Dynamics/governance-guard).
