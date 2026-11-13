# Memory poisoning (ASI06) — defense in depth

AI agents in AutoGen typically persist state across turns and across sessions: group chat history, tool results, scratchpads, retrieved snippets, durable preferences. Anything that writes into that memory becomes a privileged input on subsequent turns. **Memory poisoning** is the failure mode where untrusted
content gets into agent memory, *survives*, and then influences future reasoning — often across unrelated tasks.

OWASP's
[Top 10 for Agentic Applications](https://owasp.org/www-project-top-10-for-llm-applications/) tracks this risk as **ASI06: Memory Poisoning**. This page describes the three-layer defense architecture and shows how to wire it into an AutoGen
deployment.

## The three layers

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1 — Inline boundary validation                            │
│   OWASP Agent Memory Guard                                      │
│   ↓ synchronous, sub-100µs detectors on every read/write        │
│   ↓ injection, secret leakage, integrity, self-reinforcement    │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2 — Structured audit trail                                │
│   SecurityEvent → OpenTelemetry / SIEM                          │
│   ↓ one structured record per decision                          │
│   ↓ source_class, receipt_uri, agent_id, policy_version, hash   │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3 — Cryptographic provenance & fate-separation            │
│   bilateral receipts (e.g. Ed25519, hash-chained)               │
│   ↓ co-signed by an independent counterparty                    │
│   ↓ auditor independence is structural, not procedural          │
└─────────────────────────────────────────────────────────────────┘
```

Each layer is independent. Layer 1 alone is useful. Add Layer 2 once your SOC is ready, and reach for Layer 3 when you need attestable non-repudiation across organisational boundaries.

## Layer 1 — Inline boundary validation

[OWASP Agent Memory Guard][amg] sits between an AutoGen agent and whatever backs its memory (in-process dict, Redis, CosmosDB, vector store). Every read and every write runs through a detector pipeline plus a declarative policy. Decisions are `ALLOW` / `REDACT` / `QUARANTINE` / `BLOCK`.

[amg]: https://owasp.org/www-project-agent-memory-guard/

```bash
pip install agent-memory-guard

from agent_memory_guard import MemoryGuard, Policy, PolicyViolation, SourceClass

guard = MemoryGuard(policy=Policy.strict())

# A tool result returning from search. Untrusted by default.
guard.write(
    "tool.search.42",
    "Acme Q3 revenue was $42M",
    source_class=SourceClass.EXTERNAL_TOOL,
)

# Agent reasoning over the result — separate provenance class.
try:
    guard.write(
        "agent.belief.acme_revenue",
        "Acme had a strong Q3",
        source_class=SourceClass.AGENT_AUTHORED,
    )
except PolicyViolation as exc:
    # Policy decided to BLOCK; the wrapped store was never mutated.
    print("blocked:", exc)

```
GuardedMemoryStore for AutoGen agents

To make this drop-in for AutoGen, wrap the memory implementation the agent already uses. The MemoryStore protocol the guard depends on is a minimal get / set / delete / items contract that any backend can satisfy:

```bash
from typing import Any
from agent_memory_guard import MemoryGuard, Policy, SourceClass


class GuardedMemoryStore:
    """Drop-in wrapper that runs every AutoGen memory operation through
    Agent Memory Guard before delegating to the underlying backend.

    ``inner`` is your existing dict/Redis/CosmosDB client. ``on_violation``
    decides what to do when the guard blocks a write — drop silently,
    raise to the agent loop, or hand off to your enforcement plane.
    """

    def __init__(self, inner, *, guard: MemoryGuard | None = None,
                 on_violation: str = "drop"):
        self._inner = inner
        self._guard = guard or MemoryGuard(policy=Policy.strict())
        self._on_violation = on_violation

    def write(self, key: str, value: Any, *,
              source_class: SourceClass = SourceClass.AGENT_AUTHORED,
              receipt_uri: str | None = None) -> bool:
        try:
            self._guard.write(key, value,
                              source_class=source_class,
                              receipt_uri=receipt_uri)
        except Exception:
            if self._on_violation == "raise":
                raise
            return False
        self._inner[key] = value
        return True

    def read(self, key: str, default: Any = None) -> Any:
        # ``guard.read`` runs outbound detectors (e.g. integrity verification,
        # cross-task contamination) before returning the value.
        return self._guard.read(key, default=default)
```
Mount it on an AutoGen agent's memory slot the same way you'd mount the raw backend. From the agent's perspective nothing changes — the boundary validation is invisible until a detector fires.

Self-reinforcement (long-running agents)
For agents that elaborate on their own prior writes (a common cause of silent hallucination drift), enable the self-reinforcement detector:
```bash
from agent_memory_guard import MemoryGuard
from agent_memory_guard.detectors import SelfReinforcementDetector

guard = MemoryGuard(detectors=[
    SelfReinforcementDetector(
        cooldown_seconds=60.0,
        max_self_writes=3,
        similarity_threshold=0.85,
    ),
])
```

The detector flags rapid self-similar AGENT_AUTHORED writes to the same key. An EXTERNAL_TOOL or USER_INPUT write on that key resets the counter — independent evidence breaks the loop.

## Layer 2 — Structured audit trail
Every guard decision produces a SecurityEvent suitable for SIEM forwarding. Subscribe a handler when you build the guard:
```bash
from opentelemetry import trace
from agent_memory_guard import MemoryGuard, SecurityEvent

tracer = trace.get_tracer("agent_memory_guard")

def to_otel(event: SecurityEvent) -> None:
    with tracer.start_as_current_span(f"memory_guard.{event.operation}") as span:
        span.set_attribute("amg.detector", event.detector)
        span.set_attribute("amg.severity", event.severity.value)
        span.set_attribute("amg.action", event.action.value)
        span.set_attribute("amg.source_class", event.source_class.value)
        span.set_attribute("amg.key", event.key)
        if event.receipt_uri:
            span.set_attribute("amg.receipt_uri", event.receipt_uri)

guard = MemoryGuard(event_handlers=[to_otel])
```

Worked example in the project repo: examples/opentelemetry_hook.py.

The same SecurityEvent handler interface is how you wire AutoGen's own telemetry hooks to the guard's decisions, so memory events appear in the same trace context as agent message events.

## Layer 3 — Cryptographic provenance
For high-privilege agents (code execution, payment initiation, automated remediation), Layer 2 telemetry isn't enough — the agent and its auditor share fate. Use bilateral receipts co-signed by an independent counterparty
that doesn't share fate with the agent's runtime.

Agent Memory Guard ships a receipt_uri field on every SecurityEvent specifically to anchor this. At write time, capture the receipt from your provenance service and pass the URI through:
```bash
receipt = my_receipts.cosign(
    payload=value,
    agent_id="payment-agent-v3",
    session_id="sess-42",
    policy_version="v1.2.0",
)
guard.write(
    "agent.payment_intent",
    value,
    source_class=SourceClass.AGENT_AUTHORED,
    receipt_uri=receipt.uri,   # ed25519 co-signed, hash-chained
)
```

nobulex is one such provenance service designed for the bilateral-receipt model.

### Cross-agent scenarios
Multi-agent topologies (group chats, hand-offs, shared Redis or CosmosDB
stores) widen the memory surface considerably. Agent B can read something
Agent A wrote into shared memory three turns ago, and the write never
passed through B's policy.

Two precautions:

1. Wrap the shared store, not the agent. Mount GuardedMemoryStore
at the storage layer rather than per-agent so every participant sees
the same boundary checks regardless of who called set / get.
2. Pass current_task per turn. Agent Memory Guard tags writes with
their originating task and emits a cross_task_contamination event
when a read crosses the boundary:

```bash
guard.set_current_task("plan.invoice_check")  # before agent A's turn
guard.write("tool.fetch.42", tool_output,
            source_class=SourceClass.EXTERNAL_TOOL,
            cls=MemoryClass.TOOL_OBSERVATION)

guard.set_current_task("plan.send_email")     # before agent B's turn
guard.read("tool.fetch.42")
# → emits cross_task_contamination event with origin_task=plan.invoice_check
```

### Memory lifecycle governance
Detection catches content attacks. The slower failure mode is content that was clean when written but should now expire — stale tool results, preference candidates that never got confirmed. Use predicate-driven
retirement so retirement is reversible:
```bash
import time
now = time.time()

retired = guard.retire_if(
    lambda key, value: key.startswith("tool.") and _age(key) > 3600,
    reason="tool_observation_ttl_1h",
)
# Each retirement captures a pre-retire snapshot and emits a lifecycle event
# carrying metadata.pre_snapshot_id. ``guard.rollback(snap_id)`` undoes it.
```

### Provenance separation for high-privilege agents
For agents that can take actions (execute code, send payments, mutate
external systems), enforce stricter rules at the boundary:

- Mark every external input explicitly with source_class=SourceClass.EXTERNAL_TOOL or USER_INPUT. The default AGENT_AUTHORED is for agent reasoning only.
- Refuse to promote untrusted content to policy. Agent Memory Guard's promotion graph rejects retrieved_fact → policy and tool_observation → verified_preference even with verified=True. Policy entries can only be written directly by a trusted principal.
- Co-sign before acting. Capture a bilateral receipt (receipt_uri=...) on the write that records the intended action, then have the enforcement plane verify the co-signed receipt before executing.

### Putting it together
A production AutoGen agent running all three layers looks like this:

```bash
from agent_memory_guard import MemoryGuard, Policy, SourceClass
from agent_memory_guard.detectors import SelfReinforcementDetector
import my_receipts, my_otel_handler

guard = MemoryGuard(
    policy=Policy.strict(),
    detectors=[SelfReinforcementDetector(cooldown_seconds=60.0)],
    event_handlers=[my_otel_handler],   # Layer 2
    current_task="session.42",
)

def on_tool_result(tool_name: str, output: str) -> None:
    receipt = my_receipts.cosign(payload=output, tool=tool_name)
    guard.write(
        f"tool.{tool_name}.{next_id()}",
        output,
        source_class=SourceClass.EXTERNAL_TOOL,
        receipt_uri=receipt.uri,        # Layer 3
    )
```

### See also
- [OWASP Top 10 for Agentic Applications — ASI06: Memory Poisoning](https://owasp.org/www-project-top-10-for-llm-applications/)
- [OWASP Agent Memory Guard — reference implementation for Layer 1](https://owasp.org/www-project-agent-memory-guard/)
- [agent-memory-guard on PyPI](https://pypi.org/project/agent-memory-guard/)
- AutoGen discussion tracking the integration: [#7683](https://github.com/microsoft/autogen/issues/7683)
- AutoGen [./telemetry.md](https://github.com/OWASP/www-project-agent-memory-guard/blob/main/telemetry.md) and [./logging.md](https://github.com/OWASP/www-project-agent-memory-guard/blob/main/logging.md) guides for the Layer-2 plumbing.