"""Governance Workbench — PROPOSE / DECIDE / PROMOTE for AutoGen tool calls.

A wrapper around any AutoGen Workbench that interposes deterministic policy
evaluation between an agent's tool selection and tool execution. The wrapped
workbench's tools are exposed unchanged, but every ``call_tool`` invocation
is authorized against a user-defined policy before execution proceeds.

Denied calls return a ``ToolResult`` with ``is_error=True`` — no exception,
no disruption to the GroupChat loop. The agent sees a structured denial
message and can adjust its plan.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, AsyncGenerator, List, Mapping, Optional

from autogen_core import CancellationToken
from autogen_core.tools import ToolResult, ToolSchema, TextResultContent, Workbench


class GovernanceWorkbench(Workbench):
    """Wraps an existing Workbench with deterministic governance policy enforcement.

    Three-phase authorization pipeline:

    - **PROPOSE**: Convert each ``call_tool`` invocation into a structured intent
      with a SHA-256 content hash.
    - **DECIDE**: Evaluate the intent against user-defined policy rules.
      Pure function — no LLM, no interpretation ambiguity.
    - **PROMOTE**: Forward approved calls to the inner workbench. Return a
      structured error ``ToolResult`` for denied calls.

    Args:
        inner: The workbench to wrap. All tool listing and lifecycle methods
            delegate to it.
        policy: Governance policy dict. Structure::

            {
                "default": "approve" | "deny",
                "rules": [
                    {
                        "tools": ["tool_name", ...],
                        "verdict": "approve" | "deny",
                        "constraints": {  # optional
                            "blocked_patterns": ["rm -rf", ...],
                        },
                    },
                ],
            }

        witness_path: Optional path for hash-chained audit log.
    """

    component_type = "workbench"

    def __init__(
        self,
        inner: Workbench,
        policy: dict[str, Any],
        witness_path: str | Path | None = None,
    ) -> None:
        super().__init__()
        self._inner = inner
        self._policy = policy

        self._witness_file: Path | None = None
        if witness_path is not None:
            self._witness_file = Path(witness_path)
            self._witness_file.parent.mkdir(parents=True, exist_ok=True)

        self._prev_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        """Resume chain from existing log, or start from genesis."""
        if self._witness_file is None or not self._witness_file.exists():
            return "0" * 64
        last_line = ""
        with open(self._witness_file, encoding="utf-8") as f:
            for last_line in f:
                pass
        if last_line.strip():
            return json.loads(last_line)["hash"]
        return "0" * 64

    # --- PROPOSE ---

    @staticmethod
    def _propose(name: str, arguments: Mapping[str, Any] | None) -> dict[str, Any]:
        """Convert a tool call into a structured, hashable intent."""
        intent: dict[str, Any] = {
            "tool": name,
            "arguments": dict(arguments) if arguments else {},
        }
        payload = json.dumps(intent, sort_keys=True, default=str).encode()
        intent["content_hash"] = hashlib.sha256(payload).hexdigest()
        return intent

    # --- DECIDE ---

    @staticmethod
    def _decide(intent: dict[str, Any], policy: dict[str, Any]) -> str:
        """Pure function: ``(intent, policy) -> 'approve' | 'deny'``.

        No LLM involvement. No interpretation ambiguity.
        """
        tool_name = intent["tool"]
        args_str = json.dumps(intent.get("arguments", {}), default=str).lower()

        for rule in policy.get("rules", []):
            if tool_name not in rule.get("tools", []):
                continue

            constraints = rule.get("constraints", {})
            if constraints:
                for pattern in constraints.get("blocked_patterns", []):
                    if pattern.lower() in args_str:
                        return "deny"

            return rule.get("verdict", policy.get("default", "deny"))

        return policy.get("default", "deny")

    # --- Witness ---

    def _record(self, entry: dict[str, Any]) -> None:
        if self._witness_file is None:
            return
        entry["prev_hash"] = self._prev_hash
        entry["timestamp"] = time.time()
        payload = json.dumps(entry, sort_keys=True, default=str)
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()
        entry["hash"] = entry_hash
        with open(self._witness_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        self._prev_hash = entry_hash

    # --- Workbench interface ---

    async def list_tools(self) -> List[ToolSchema]:
        return await self._inner.list_tools()

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        cancellation_token: CancellationToken | None = None,
        call_id: str | None = None,
    ) -> ToolResult:
        # PROPOSE
        intent = self._propose(name, arguments)

        # DECIDE
        verdict = self._decide(intent, self._policy)

        # PROMOTE
        self._record({
            "phase": "promote",
            "verdict": verdict,
            "tool": name,
            "content_hash": intent["content_hash"],
            "call_id": call_id or "",
        })

        if verdict == "deny":
            return ToolResult(
                name=name,
                result=[TextResultContent(
                    content=f"GOVERNANCE DENIED: Tool '{name}' blocked by policy. "
                    f"Adjust your approach or use an approved tool."
                )],
                is_error=True,
            )

        # Approved — delegate to inner workbench
        result = await self._inner.call_tool(
            name, arguments, cancellation_token, call_id
        )

        self._record({
            "phase": "audit",
            "tool": name,
            "call_id": call_id or "",
            "is_error": result.is_error,
        })

        return result

    async def start(self) -> None:
        await self._inner.start()

    async def stop(self) -> None:
        await self._inner.stop()

    async def reset(self) -> None:
        await self._inner.reset()

    async def save_state(self) -> Mapping[str, Any]:
        return await self._inner.save_state()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        await self._inner.load_state(state)

    def _to_config(self) -> Any:
        raise NotImplementedError("GovernanceWorkbench is not serializable")

    @classmethod
    def _from_config(cls, config: Any) -> "GovernanceWorkbench":
        raise NotImplementedError("GovernanceWorkbench is not serializable")
