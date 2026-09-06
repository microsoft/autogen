# Security extension points

AutoGen does not ship a built-in content threat rules wrapper. If you need prompt injection, credential leakage, exfiltration, or dangerous-command detection, build it as an external extension and compose it at the boundary where the untrusted content enters your application.

This keeps AutoGen's maintenance-mode surface small while still giving existing users a clear path for policy engines such as Agent Threat Rules, allowlist validators, or organization-specific scanners.

## Choose the boundary to inspect

| Boundary | Use when | Existing API |
|---|---|---|
| Incoming chat messages | You need to filter or tag messages before an agent receives them. | Wrap a {py:class}`~autogen_agentchat.agents.BaseChatAgent`, following the same wrapper shape as {py:class}`~autogen_agentchat.agents.MessageFilterAgent`. |
| Tool arguments and return values | You need to inspect the operation an agent is about to run, or the content returned by that operation. | Wrap an {py:class}`~autogen_core.tools.Tool` and delegate to the original tool after your policy check. |
| Workbench tool calls | You need one policy layer across dynamic tools from an MCP server or another shared resource. | Wrap a {py:class}`~autogen_core.tools.Workbench` and inspect {py:meth}`~autogen_core.tools.Workbench.call_tool` arguments and {py:class}`~autogen_core.tools.ToolResult` values. |

For tool-calling agents, prefer the tool or workbench boundary over only scanning chat messages. Tool outputs from web pages, files, MCP servers, and other external systems are often where prompt injection and data exfiltration instructions first enter the run.

## Recommended behavior for a scanner extension

A scanner extension should be deterministic and explicit:

- Do not call another model from the scanner by default. Regex rules, allowlists, and static policy checks are easier to audit and cheaper to run.
- Return or raise a clear denial result when blocking. Silent drops can leave multi-agent workflows waiting for a response that will never arrive.
- Include the tool name, call ID, matched rule, and severity in the denial metadata so the application can log or route the event.
- Default to tagging or returning structured errors for medium-confidence findings, then let the application decide whether to block.
- Keep the rule pack outside AutoGen when rules change frequently. A separate package can release rule updates without tying them to AutoGen's release cadence.

## Minimal tool wrapper pattern

The {py:class}`~autogen_core.tools.Tool` protocol is enough to adapt an existing tool without changing AutoGen itself:

```python
from collections.abc import Mapping
from typing import Any

from autogen_core import CancellationToken
from autogen_core.tools import Tool, ToolSchema


class ScannedTool:
    def __init__(self, wrapped: Tool, scanner: Any) -> None:
        self._wrapped = wrapped
        self._scanner = scanner

    @property
    def name(self) -> str:
        return self._wrapped.name

    @property
    def description(self) -> str:
        return self._wrapped.description

    @property
    def schema(self) -> ToolSchema:
        return self._wrapped.schema

    def args_type(self) -> type[Any]:
        return self._wrapped.args_type()

    def return_type(self) -> type[Any]:
        return self._wrapped.return_type()

    def state_type(self) -> type[Any] | None:
        return self._wrapped.state_type()

    def return_value_as_string(self, value: Any) -> str:
        return self._wrapped.return_value_as_string(value)

    async def run_json(
        self,
        args: Mapping[str, Any],
        cancellation_token: CancellationToken,
        call_id: str | None = None,
    ) -> Any:
        self._scanner.raise_if_blocked(tool_name=self.name, arguments=args, call_id=call_id)
        result = await self._wrapped.run_json(args, cancellation_token, call_id=call_id)
        self._scanner.raise_if_blocked(tool_name=self.name, result=self.return_value_as_string(result), call_id=call_id)
        return result

    async def save_state_json(self) -> Mapping[str, Any]:
        return await self._wrapped.save_state_json()

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        await self._wrapped.load_state_json(state)
```

This pattern is intentionally external. It lets security packages depend on `autogen-core`, pin their own rule sets, and decide whether matches should tag, block, redact, or escalate.

## Notes for MCP and browser tools

When a workbench exposes tools from an MCP server, scan both directions:

1. Inspect `call_tool()` arguments before they leave the agent process.
2. Inspect the returned `ToolResult` text before the model receives it.
3. Keep a hostname or command allowlist in the application when the tool can browse, fetch URLs, read files, or execute shell commands.

Only connect AutoGen to MCP servers and browser tools that you trust. A scanner can reduce risk, but it is not a sandbox and does not replace container isolation, least-privilege credentials, or human approval for high-impact actions.
