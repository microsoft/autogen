# Agent-OS Governance Extension for AutoGen

This extension provides kernel-level governance for AutoGen multi-agent conversations using [Agent-OS](https://github.com/imran-siddique/agent-os).

## Features

- **Policy Enforcement**: Define rules for agent behavior
- **Tool Filtering**: Control which tools agents can use
- **Content Filtering**: Block dangerous patterns (SQL injection, shell commands)
- **Rate Limiting**: Limit messages and tool calls
- **Audit Trail**: Full logging of all agent interactions

## Installation

```bash
pip install autogen-ext[governance]
# or
pip install agent-os-kernel
```

## Quick Start

```python
from autogen_ext.governance import GovernedTeam, GovernancePolicy
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Create policy
policy = GovernancePolicy(
    max_tool_calls=10,
    max_messages=50,
    blocked_patterns=["DROP TABLE", "rm -rf", "DELETE FROM"],
    blocked_tools=["shell_execute"],
    require_human_approval=False,
)

# Create agents
model = OpenAIChatCompletionClient(model="gpt-4o")
analyst = AssistantAgent("analyst", model_client=model)
reviewer = AssistantAgent("reviewer", model_client=model)

# Create governed team
team = GovernedTeam(
    agents=[analyst, reviewer],
    policy=policy,
)

# Run with governance
result = await team.run("Analyze Q4 sales data")

# Get audit log
audit = team.get_audit_log()
print(f"Total events: {len(audit)}")
```

## Policy Options

```python
GovernancePolicy(
    # Limits
    max_messages=100,        # Max messages per session
    max_tool_calls=50,       # Max tool invocations
    timeout_seconds=300,     # Session timeout
    
    # Tool Control
    allowed_tools=["code_executor", "web_search"],  # Whitelist
    blocked_tools=["shell_execute"],                 # Blacklist
    
    # Content Filtering
    blocked_patterns=["DROP TABLE", "rm -rf"],
    max_message_length=50000,
    
    # Approval
    require_human_approval=False,
    approval_tools=["database_write"],  # Tools needing approval
    
    # Audit
    log_all_messages=True,
)
```

## Handling Violations

```python
def on_violation(error):
    print(f"BLOCKED: {error.policy_name} - {error.description}")
    # Send alert, log to SIEM, etc.

team = GovernedTeam(
    agents=[agent1, agent2],
    policy=policy,
    on_violation=on_violation,
)
```

## Integration with Agent-OS Kernel

For full kernel-level governance with signals, checkpoints, and policy languages:

```python
from agent_os import KernelSpace
from agent_os.policies import SQLPolicy, CostControlPolicy

# Create kernel with policies
kernel = KernelSpace(policy=[
    SQLPolicy(allow=["SELECT"], deny=["DROP", "DELETE"]),
    CostControlPolicy(max_cost_usd=100),
])

# Wrap AutoGen team in kernel
@kernel.register
async def run_team(task: str):
    return await team.run(task)

# Execute with full governance
result = await kernel.execute(run_team, "Analyze data")
```

## Links

- [Agent-OS GitHub](https://github.com/imran-siddique/agent-os)
- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [Governance Best Practices](https://github.com/imran-siddique/agent-os/blob/main/docs/governance.md)
