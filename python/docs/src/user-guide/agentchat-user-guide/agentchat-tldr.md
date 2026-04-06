# AgentChat TL;DR

## What Is AgentChat

AgentChat is AutoGen's high-level API for building multi-agent applications quickly. It is built
on top of `autogen-core` and provides preset agents with ready-made behaviors and teams with
predefined coordination patterns. It is the recommended starting point for new users.

**Main agent types:**
- `AssistantAgent` — LLM-powered agent with optional tool use, reflection, and structured output
- `UserProxyAgent` — relays human input as agent responses
- `CodeExecutorAgent` — executes code in a sandboxed environment
- `MultimodalWebSurfer`, `FileSurfer`, `VideoSurfer` — specialized browsing/search agents (via `autogen-ext`)

## Minimal Working Example

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")

async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is 73 degrees and Sunny."

agent = AssistantAgent(
    name="weather_agent",
    model_client=model_client,
    tools=[get_weather],
    system_message="You are a helpful assistant.",
    reflect_on_tool_use=True,
)

# Run and stream output to console
await Console(agent.run_stream(task="What is the weather in New York?"))
await model_client.close()
```

## Team Types

| Team | Description |
|------|-------------|
| `RoundRobinGroupChat` | Agents take turns in fixed order |
| `SelectorGroupChat` | An LLM selects the next speaker based on context |
| `Swarm` | Agents hand off to each other via tool calls (localized selection) |
| `GraphFlow` | Directed graph of agents — explicit workflow edges |

## Termination Conditions

Conversations stop when a condition is met. Combine with `|` (OR) or `&` (AND):

```python
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination

termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(20)
```

Other conditions: `TokenUsageTermination`, `TimeoutTermination`, `StopMessageTermination`,
`HandoffTermination`, `SourceMatchTermination`.

## Further Reading

- First working app (code): `quickstart.ipynb`
- Agents in depth: `tutorial/agents.ipynb`
- Teams in depth: `tutorial/teams.ipynb`
- Custom agents: `custom-agents.ipynb`
- Memory: `memory.ipynb`
- Human-in-the-loop: `tutorial/human-in-the-loop.ipynb`
