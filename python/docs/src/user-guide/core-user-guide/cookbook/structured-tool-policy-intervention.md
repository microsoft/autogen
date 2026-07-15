# Structured Tool Policy Decisions with an Intervention Handler

An intervention handler can enforce policy at the tool execution boundary before a side-effecting
tool receives a call. For an agent loop to react correctly, a denial should also distinguish between:

- missing authority that the agent may request and retry;
- a permanent policy prohibition that must not be retried; and
- an accepted action that may continue to the tool executor.

This recipe uses {py:class}`~autogen_core.DefaultInterventionHandler` to return machine-readable
policy failures in {py:class}`~autogen_core.tool_agent.ToolException`. It requires no model client,
API key, or tool runtime.

## Define a small policy and intervention handler

The example policy is deliberately synthetic. A production policy should replace the in-memory
grant set with its authority service and should derive `actionRef` from a canonical representation of
the exact tool call.

```python
import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, cast

from autogen_core import (
    AgentId,
    CancellationToken,
    DefaultInterventionHandler,
    DropMessage,
    FunctionCall,
    MessageContext,
)
from autogen_core.tool_agent import ToolException


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str
    message: str
    action_ref: str
    can_request_authority: bool


class InMemoryToolPolicy:
    """Synthetic policy store for this recipe, not a production authority service."""

    def __init__(self, permanently_forbidden_tools: set[str] | None = None) -> None:
        self._permanently_forbidden_tools = permanently_forbidden_tools or set()
        self._authorized_actions: set[str] = set()

    @staticmethod
    def action_ref(call: FunctionCall) -> str:
        return f"tool:{call.name}:{call.id}"

    def grant(self, action_ref: str) -> None:
        self._authorized_actions.add(action_ref)

    def decide(self, call: FunctionCall) -> PolicyDecision:
        action_ref = self.action_ref(call)
        if call.name in self._permanently_forbidden_tools:
            return PolicyDecision(
                allowed=False,
                code="ACTION_FORBIDDEN",
                message="The orchestrator policy permanently forbids this action.",
                action_ref=action_ref,
                can_request_authority=False,
            )
        if action_ref not in self._authorized_actions:
            return PolicyDecision(
                allowed=False,
                code="AUTHORITY_REQUIRED",
                message="Matching pre-action authority is required.",
                action_ref=action_ref,
                can_request_authority=True,
            )
        return PolicyDecision(
            allowed=True,
            code="AUTHORITY_ACCEPTED",
            message="Matching pre-action authority is present.",
            action_ref=action_ref,
            can_request_authority=False,
        )


class StructuredToolPolicyHandler(DefaultInterventionHandler):
    """Intercept FunctionCall messages before ToolAgent execution."""

    def __init__(self, policy: Callable[[FunctionCall], PolicyDecision]) -> None:
        self._policy = policy

    async def on_send(
        self,
        message: Any,
        *,
        message_context: MessageContext,
        recipient: AgentId,
    ) -> Any | type[DropMessage]:
        if not isinstance(message, FunctionCall):
            return message

        decision = self._policy(message)
        if decision.allowed:
            return message

        denial = {
            "actionRef": decision.action_ref,
            "canRequestAuthority": decision.can_request_authority,
            "code": decision.code,
            "enforcementPointKind": "orchestrator_policy",
            "message": decision.message,
        }
        raise ToolException(
            call_id=message.id,
            content=json.dumps(denial, separators=(",", ":"), sort_keys=True),
            name=message.name,
        )


def message_context(message_id: str) -> MessageContext:
    return MessageContext(
        sender=None,
        topic_id=None,
        is_rpc=True,
        cancellation_token=CancellationToken(),
        message_id=message_id,
    )


async def evaluate(handler: StructuredToolPolicyHandler, call: FunctionCall) -> dict[str, object]:
    try:
        await handler.on_send(
            call,
            message_context=message_context(f"message-{call.id}"),
            recipient=AgentId("tool_executor_agent", "default"),
        )
        return {"action": call.name, "code": "AUTHORITY_ACCEPTED", "outcome": "allowed"}
    except ToolException as error:
        denial = cast(dict[str, object], json.loads(error.content))
        return {"action": call.name, "outcome": "denied", **denial}


async def main() -> None:
    policy = InMemoryToolPolicy(permanently_forbidden_tools={"delete_production"})
    handler = StructuredToolPolicyHandler(policy.decide)
    recoverable = FunctionCall(id="call-1", name="write_file", arguments='{"path":"fixture.txt"}')
    forbidden = FunctionCall(id="call-2", name="delete_production", arguments="{}")

    print(json.dumps(await evaluate(handler, recoverable), sort_keys=True))
    policy.grant(policy.action_ref(recoverable))
    print(json.dumps(await evaluate(handler, recoverable), sort_keys=True))
    print(json.dumps(await evaluate(handler, forbidden), sort_keys=True))

    status_message = {"kind": "status"}
    status_result = await handler.on_send(
        status_message,
        message_context=message_context("message-status"),
        recipient=AgentId("tool_executor_agent", "default"),
    )
    assert status_result is status_message


asyncio.run(main())
```

The three results let an agent loop branch without parsing natural language:

| Policy state | `code` | `canRequestAuthority` | Agent behavior |
|---|---|---:|---|
| Missing authority | `AUTHORITY_REQUIRED` | `true` | Request authority once, then retry |
| Accepted authority | `AUTHORITY_ACCEPTED` | n/a | Continue to the tool executor |
| Permanent prohibition | `ACTION_FORBIDDEN` | `false` | Stop without requesting authority or retrying |

The denial payload intentionally omits raw tool arguments. A production adapter can attach an opaque,
digest-bound `actionRef` and record post-call evidence separately after successful tool execution.
Messages that are not `FunctionCall` instances pass through unchanged, as the final assertion demonstrates.
