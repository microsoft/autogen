# Runtime Security with Vaultak

[Vaultak](https://vaultak.com) is a runtime security platform that adds real-time protection to
AutoGen agents. It intercepts every tool call and inter-agent message, scores risk on a 0–10 scale,
enforces your policy rules, masks PII in tool outputs, and blocks or drops dangerous actions before
they execute — with no changes to your existing agent or team logic.

## Installation

```bash
pip install autogen-ext-vaultak
```

Sign up at [vaultak.com](https://vaultak.com) to get your API key (starts with `vtk_`).

## How It Works

Vaultak integrates through AutoGen's native {py:class}`~autogen_core.DefaultInterventionHandler`.
The runtime calls the handler on every `on_send` and `on_publish` event _before_ the message
reaches its recipient. The Vaultak handler inspects {py:class}`~autogen_agentchat.messages.ToolCallRequestEvent`
messages, scores the requested tool call, and returns
{py:class}`~autogen_core.DropMessage` to block execution if the risk score exceeds your threshold.

```{note}
{py:class}`~autogen_core.SingleThreadedAgentRuntime` is the only runtime that currently
supports intervention handlers.
```

## Quick Start

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_core import SingleThreadedAgentRuntime
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext_vaultak import VaultakInterventionHandler


async def main() -> None:
    # Initialize the Vaultak handler
    vaultak = VaultakInterventionHandler(
        api_key="vtk_...",
        agent_name="my-autogen-crew",
        block_on_high_risk=True,
        risk_threshold=7.0,
    )

    # Pass the handler to the runtime — every message is now monitored
    runtime = SingleThreadedAgentRuntime(
        intervention_handlers=[vaultak]
    )
    runtime.start()

    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    def search_web(query: str) -> str:
        """Search the web for information."""
        return f"Results for: {query}"

    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[search_web],
    )

    termination = TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat([agent], termination_condition=termination)

    await Console(team.run_stream(task="Research the latest AI safety developments."))
    await runtime.stop()
    await model_client.close()


asyncio.run(main())
```

## Configuration

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | — | Your Vaultak API key — required |
| `agent_name` | `str` | `"autogen-agent"` | Label for this runtime in the Vaultak dashboard |
| `block_on_high_risk` | `bool` | `True` | Drop messages whose risk score exceeds the threshold |
| `risk_threshold` | `float` | `7.0` | Score (0–10) above which tool calls are blocked |
| `verbose` | `bool` | `False` | Log every scored action to stdout |

### Stricter threshold for sensitive workloads

```python
vaultak = VaultakInterventionHandler(
    api_key="vtk_...",
    agent_name="prod-db-agent",
    risk_threshold=5.0,  # Block anything above medium risk
)
```

## What Gets Monitored

| AutoGen event | Vaultak action |
|---|---|
| `ToolCallRequestEvent` published | Risk-scores the tool call (0–10); drops message if above threshold |
| `ToolCallRequestEvent` published | Checks tool call against your policy rules |
| `ToolCallExecutionEvent` received | Scans tool output for PII and masks it |
| Runtime `on_publish` / `on_send` | All messages pass through the handler |
| Exception / error message | Sends alert to your Vaultak dashboard |

## Dashboard

Every intercepted action is visible at [app.vaultak.com](https://app.vaultak.com):
real-time risk scores, full message history, policy violations, and alerts.
Policy rules can be configured there without changing your code.

## Combining with OpenTelemetry Tracing

Vaultak and AutoGen's built-in [OpenTelemetry tracing](tracing.ipynb) are fully compatible.
Use OTel for performance traces and distributed debugging; use Vaultak for security enforcement
and policy compliance. Pass both to the runtime:

```python
from opentelemetry import trace

runtime = SingleThreadedAgentRuntime(
    tracer_provider=trace.get_tracer_provider(),   # OTel tracing
    intervention_handlers=[vaultak],               # Vaultak security
)
```

## Links

- [Vaultak documentation](https://docs.vaultak.com)
- [PyPI package](https://pypi.org/project/autogen-ext-vaultak)
- [GitHub](https://github.com/vaultak/autogen-ext-vaultak)
- [AutoGen InterventionHandler reference](../core-user-guide/framework/agent-and-agent-runtime.ipynb)
