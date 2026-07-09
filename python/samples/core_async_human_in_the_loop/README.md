# Async Human-in-the-Loop Example

An example showing human-in-the-loop which waits for human input before making the tool call.

## Optional: Add a Pramagent tool policy gate

This sample pauses for human input before the scheduling tool runs. If you also
want deterministic policy enforcement at the tool boundary, add a policy check
immediately before `tool.run_json(...)`.

For example, [Pramagent](https://github.com/sriram7737/pramagent) can validate
the proposed tool name and arguments before execution:

```python
from pramagent import Pramagent, Verdict
from pramagent.layers import ToolGuardLayer, ToolPolicy
from pramagent.layers.tool_guard import SideEffect

tool_guard = ToolGuardLayer(
    policies=[
        ToolPolicy(
            name="schedule_meeting",
            side_effect=SideEffect.EXTERNAL_MESSAGE,
            action=Verdict.ESCALATE,
            allowed_tenants={"calendar_agent"},
            schema={
                "type": "object",
                "required": ["recipient", "date", "time"],
                "properties": {
                    "recipient": {"type": "string", "minLength": 1},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
                "additionalProperties": False,
            },
        )
    ]
)

armor = Pramagent(tool_guard=tool_guard)
```

Then check the proposed tool call before execution:

```python
arguments = json.loads(call.arguments)
decision = armor.validate_tool(
    call.name,
    arguments,
    tenant_id="calendar_agent",
    session_id=call.id or "calendar-run",
    action_label="schedule_meeting",
)

if decision.verdict == Verdict.BLOCK:
    raise PermissionError(f"Tool call blocked: {decision.reason}")

if decision.verdict == Verdict.ESCALATE:
    raise PermissionError(
        f"Tool call requires human approval before execution: {decision.reason}"
    )

await tool.run_json(arguments, ctx.cancellation_token, call_id=call.id)
```

This keeps the model-generated tool call separate from the execution decision:
AutoGen coordinates the conversation and human-in-the-loop flow, while the
external policy layer decides whether the side effect is allowed to run.

## Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.

```bash
pip install "autogen-ext[openai,azure]" "pyyaml"
```

## Model Configuration

The model configuration should defined in a `model_config.yml` file.
Use `model_config_template.yml` as a template.

## Running the example

```bash
python main.py
```
