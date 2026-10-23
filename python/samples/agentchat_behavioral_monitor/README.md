# agentchat_behavioral_monitor

Detect vocabulary drift across repeated AgentChat runs.

When a long-running agent shifts away from earlier task vocabulary, the failure
often shows up first as a change in outputs rather than an explicit error. This
sample shows how to watch for that drift on the public AgentChat surface.

The demo is deterministic: it uses `ReplayChatCompletionClient` together with a
real `AssistantAgent`, then monitors the resulting `TaskResult.messages`
history. In production, replace the replay model with a real model client and
keep the same monitor.

This sample detects drift using **Ghost Consistency Score (CCS)**: the fraction
of vocabulary from the earliest runs still present in the most recent runs. A
score below 0.40 indicates likely behavioral drift.

## How it works

```
Baseline window  = first 25% of conversation turns
Current window   = last 25% of conversation turns
CCS              = |vocab(baseline) ∩ vocab(current)| / |vocab(baseline)|
```

A "ghost term" is a task-relevant word (`jwt`, `bcrypt`, `foreign_key`,
`redis`, etc.)
that appeared in the baseline window but has disappeared from the current
window. Ghost terms are the most direct signal of forgotten context.

## Running the demo

```bash
python main.py
```

Expected output:

```
=== AutoGen AgentChat behavioral monitor demo ===

Turn 1
CCS: 1.0
Ghost terms: []
Drift detected: False

Turn 3
CCS: 0.25
Ghost terms: ['bcrypt', 'foreign_key', 'jwt', 'redis']
Drift detected: True
```

## Integrating into your agent loop

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.replay import ReplayChatCompletionClient
from main import BehavioralMonitor

monitor = BehavioralMonitor(
    ccs_threshold=0.40,
    min_messages=3,
)

history = []
agent = AssistantAgent(
    "assistant",
    model_client=ReplayChatCompletionClient([
        "Use jwt and bcrypt for auth.",
        "Keep jwt auth intact for the profile endpoint.",
        "Add endpoint rate limiting.",
    ]),
)

# Check after each public AgentChat run
task_result = await agent.run(task="Use jwt and bcrypt for auth", output_task_messages=False)
result = monitor.observe_result(history, task_result)
if result["drift_detected"]:
    print("Drift at turn", result["turn"], "ghost:", result["ghost_terms"])

# Later runs keep extending the same external history
task_result = await agent.run(task="Now add a profile endpoint", output_task_messages=False)
result = monitor.observe_result(history, task_result)
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `ccs_threshold` | 0.40 | Flag drift when CCS drops below this value |
| `min_messages` | 3 | Minimum number of tracked AgentChat results before checks run |
| `ghost_lexicon` | built-in list | Domain terms to watch for disappearance |

## Connection to AutoGen issue #7265

This sample addresses the production reliability pattern discussed in
https://github.com/microsoft/autogen/issues/7265 — specifically the
ghost-lexicon pattern for detecting when long-running agent outputs silently
drift away from earlier task vocabulary.

## Related

- [compression-monitor](https://github.com/agent-morrow/compression-monitor) — the standalone toolkit this sample is adapted from
