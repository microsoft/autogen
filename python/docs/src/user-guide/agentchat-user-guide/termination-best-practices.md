---
myst:
  html_meta:
    "description lang=en": |
      Best practices for choosing termination conditions in AgentChat
---

# Termination Condition Best Practices

When building multi-agent teams, choosing the right termination condition is critical.
This guide helps you select conditions that are reliable and predictable.

## When to Use TextMentionTermination

`TextMentionTermination` stops the team when a specific keyword appears in a message.
This works well when:

- The agent's system prompt explicitly instructs it to output a keyword (e.g., "APPROVE")
- You filter by source: `TextMentionTermination("APPROVE", sources=["user"])`

However, **TextMentionTermination can be unreliable** when agents use tools.
Tool-calling agents may respond with function calls instead of plain text,
so the expected keyword never appears and the team runs indefinitely.

## Recommended: Combine with Deterministic Conditions

Always pair `TextMentionTermination` with a deterministic safety net:

```python
from autogen_agentchat.conditions import (
    TextMentionTermination,
    MaxMessageTermination,
    TimeoutTermination,
)

termination = (
    TextMentionTermination("APPROVE", sources=["user"])
    | MaxMessageTermination(10)
    | TimeoutTermination(max_seconds=120)
)
```

This ensures the team stops even if the model doesn't produce the expected keyword.

## Deterministic Alternatives

### MaxMessageTermination

The simplest and most predictable condition. Stops after a fixed number of messages.

```python
from autogen_agentchat.conditions import MaxMessageTermination
termination = MaxMessageTermination(max_messages=10)
```

### SourceMatchTermination

Stops when a specific agent sends a message. Useful for human-in-the-loop patterns
where you want to stop after the user responds.

```python
from autogen_agentchat.conditions import SourceMatchTermination
termination = SourceMatchTermination(sources=["user"])
```

### HandoffTermination

Stops when an agent hands off to another agent (or back to the user).

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_agentchat.conditions import HandoffTermination

assistant = AssistantAgent(
    "assistant",
    model_client=model_client,
    handoffs=[Handoff(target="user", message="Transfer to user.")],
)
termination = HandoffTermination(target="user")
```

### ExternalTermination

Allows external code to stop the team — for example, from a UI button or API call.

```python
from autogen_agentchat.conditions import ExternalTermination
termination = ExternalTermination()
# Later, from your application:
# termination.set()
```

### TimeoutTermination

A safety net that stops the team after a time limit.

```python
from autogen_agentchat.conditions import TimeoutTermination
termination = TimeoutTermination(max_seconds=300)
```

### TokenUsageTermination

Stops when token usage exceeds a limit. Useful for cost control.

```python
from autogen_agentchat.conditions import TokenUsageTermination
termination = TokenUsageTermination(max_total_token=10000)
```

## Pattern: Stop-and-Resume for Interactive Teams

For interactive applications (web UI, chat bots), the recommended pattern is:

1. Set `max_turns=1` on the team to stop after the assistant responds
2. Collect user input from the UI
3. Run the team again with the new input

```python
from autogen_agentchat.teams import RoundRobinGroupChat

team = RoundRobinGroupChat([assistant], max_turns=1)

# First run
result = await team.run(task="Hello!")

# User provides input from UI
user_input = "Tell me more."

# Resume with user input
result = await team.run(task=user_input)
```

This avoids blocking on `UserProxyAgent.input_func` and works naturally
with web frameworks like Streamlit, FastAPI, or ChainLit.

See the [human-in-the-loop tutorial](tutorial/human-in-the-loop.ipynb) for a complete walkthrough.
