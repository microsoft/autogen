"""Action Gate & Cryptographic Action Ledger Module for Microsoft AutoGen.

Provides deterministic execution boundaries, simulation fallbacks, and
append-only SHA-256 hash-chained action ledgers for AutoGen agent tools and workbenches.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class ToolTier(str, Enum):
    READ = "read"
    WRITE_IDEMPOTENT = "write_idempotent"
    WRITE_MUTATING = "write_mutating"
    DESTRUCTIVE = "destructive"


class Disposition(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    SIMULATE = "simulate"


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    disposition: Disposition
    tier: ToolTier
    reason: str
    tool_name: str
    receipt_hash: str
    simulation_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "disposition": self.disposition.value,
            "tier": self.tier.value,
            "reason": self.reason,
            "tool_name": self.tool_name,
            "receipt_hash": self.receipt_hash,
            "simulation_mode": self.simulation_mode,
        }


class ActionLedger:
    """Append-only SHA-256 hash-chained action ledger for compliance audit readiness."""

    GENESIS_HASH = "0" * 64

    def __init__(self, ledger_path: Path | str = "artifacts/action_ledger.jsonl") -> None:
        self.ledger_path = Path(ledger_path)
        self.last_hash = self._recover_last_hash()

    def _recover_last_hash(self) -> str:
        if not self.ledger_path.exists():
            return self.GENESIS_HASH
        last_hash = self.GENESIS_HASH
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        last_hash = record.get("receipt_hash", last_hash)
        except Exception:
            return self.GENESIS_HASH
        return last_hash

    def record(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        decision: GateDecision,
        agent_id: Optional[str] = None,
    ) -> str:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        canonical_args = json.dumps(arguments, sort_keys=True, default=str)

        payload = f"{self.last_hash}|{timestamp}|{tool_name}|{canonical_args}|{decision.disposition.value}|{agent_id or ''}"
        receipt_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        entry = {
            "timestamp": timestamp,
            "prev_hash": self.last_hash,
            "receipt_hash": receipt_hash,
            "tool_name": tool_name,
            "arguments": arguments,
            "decision": decision.to_dict(),
            "agent_id": agent_id,
        }

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

        self.last_hash = receipt_hash
        return receipt_hash


class ActionGate:
    """Deterministic security gate enforcing 'never_equate_intent_to_approval: true'."""

    DEFAULT_TIER_RULES: Dict[str, ToolTier] = {
        # Read operations
        "search": ToolTier.READ,
        "read": ToolTier.READ,
        "get": ToolTier.READ,
        "list": ToolTier.READ,
        "query": ToolTier.READ,
        "inspect": ToolTier.READ,
        "fetch": ToolTier.READ,
        # Idempotent writes
        "upsert": ToolTier.WRITE_IDEMPOTENT,
        "put": ToolTier.WRITE_IDEMPOTENT,
        "set": ToolTier.WRITE_IDEMPOTENT,
        # Mutating writes
        "post": ToolTier.WRITE_MUTATING,
        "create": ToolTier.WRITE_MUTATING,
        "update": ToolTier.WRITE_MUTATING,
        "send": ToolTier.WRITE_MUTATING,
        # Destructive
        "delete": ToolTier.DESTRUCTIVE,
        "drop": ToolTier.DESTRUCTIVE,
        "terminate": ToolTier.DESTRUCTIVE,
        "destroy": ToolTier.DESTRUCTIVE,
        "exec": ToolTier.DESTRUCTIVE,
        "bash": ToolTier.DESTRUCTIVE,
        "shell": ToolTier.DESTRUCTIVE,
    }

    def __init__(
        self,
        prove_token: Optional[str] = None,
        ledger: Optional[ActionLedger] = None,
        custom_tier_rules: Optional[Dict[str, ToolTier]] = None,
        allow_simulation: bool = True,
    ) -> None:
        self.prove_token = prove_token or os.environ.get("AAG_PROVE_TOKEN")
        self.ledger = ledger or ActionLedger()
        self.tier_rules = dict(self.DEFAULT_TIER_RULES)
        if custom_tier_rules:
            self.tier_rules.update(custom_tier_rules)
        self.allow_simulation = allow_simulation

    def classify_tool(self, tool_name: str) -> ToolTier:
        tool_lower = tool_name.lower()
        for pattern, tier in self.tier_rules.items():
            if pattern in tool_lower:
                return tier
        return ToolTier.WRITE_MUTATING

    def is_kill_switch_active(self) -> bool:
        if os.environ.get("AAG_KILL_SWITCH", "").strip() in ("1", "true", "TRUE"):
            return True
        if Path("artifacts/KILL").exists():
            return True
        return False

    def evaluate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        prove_token: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> GateDecision:
        if self.is_kill_switch_active():
            decision = GateDecision(
                allowed=False,
                disposition=Disposition.DENY,
                tier=ToolTier.DESTRUCTIVE,
                reason="Kill-switch engaged (AAG_KILL_SWITCH active or artifacts/KILL present)",
                tool_name=tool_name,
                receipt_hash="",
                simulation_mode=False,
            )
            receipt_hash = self.ledger.record(tool_name, arguments, decision, agent_id)
            return GateDecision(**{**asdict(decision), "receipt_hash": receipt_hash})

        tier = self.classify_tool(tool_name)
        active_token = prove_token or self.prove_token

        if tier == ToolTier.READ:
            decision = GateDecision(
                allowed=True,
                disposition=Disposition.ALLOW,
                tier=tier,
                reason="Read-only operation allowed",
                tool_name=tool_name,
                receipt_hash="",
                simulation_mode=False,
            )
        elif tier in (ToolTier.WRITE_IDEMPOTENT, ToolTier.WRITE_MUTATING):
            if active_token:
                decision = GateDecision(
                    allowed=True,
                    disposition=Disposition.ALLOW,
                    tier=tier,
                    reason="Mutating write authorized with prove token",
                    tool_name=tool_name,
                    receipt_hash="",
                    simulation_mode=False,
                )
            elif self.allow_simulation:
                decision = GateDecision(
                    allowed=True,
                    disposition=Disposition.SIMULATE,
                    tier=tier,
                    reason="Unapproved mutating write downgraded to simulation mode",
                    tool_name=tool_name,
                    receipt_hash="",
                    simulation_mode=True,
                )
            else:
                decision = GateDecision(
                    allowed=False,
                    disposition=Disposition.DENY,
                    tier=tier,
                    reason="Mutating write rejected: missing prove token and simulation disabled",
                    tool_name=tool_name,
                    receipt_hash="",
                    simulation_mode=False,
                )
        elif tier == ToolTier.DESTRUCTIVE:
            if active_token:
                decision = GateDecision(
                    allowed=True,
                    disposition=Disposition.ALLOW,
                    tier=tier,
                    reason="Destructive operation explicitly authorized with prove token",
                    tool_name=tool_name,
                    receipt_hash="",
                    simulation_mode=False,
                )
            else:
                decision = GateDecision(
                    allowed=False,
                    disposition=Disposition.DENY,
                    tier=tier,
                    reason="Destructive operation blocked by ActionGate (never_equate_intent_to_approval)",
                    tool_name=tool_name,
                    receipt_hash="",
                    simulation_mode=False,
                )
        else:
            decision = GateDecision(
                allowed=False,
                disposition=Disposition.DENY,
                tier=ToolTier.DESTRUCTIVE,
                reason="Unknown tool classification",
                tool_name=tool_name,
                receipt_hash="",
                simulation_mode=False,
            )

        receipt_hash = self.ledger.record(tool_name, arguments, decision, agent_id)
        return GateDecision(
            allowed=decision.allowed,
            disposition=decision.disposition,
            tier=decision.tier,
            reason=decision.reason,
            tool_name=decision.tool_name,
            receipt_hash=receipt_hash,
            simulation_mode=decision.simulation_mode,
        )


class ActionBoundary:
    """Tool wrapper & boundary decorator for AutoGen tools and workbenches."""

    def __init__(
        self,
        gate: Optional[ActionGate] = None,
        prove_token: Optional[str] = None,
        ledger_path: str = "artifacts/action_ledger.jsonl",
    ) -> None:
        self.gate = gate or ActionGate(prove_token=prove_token, ledger=ActionLedger(ledger_path))

    def guard(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to wrap any function or AutoGen tool execution with ActionGate policy."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tool_name = getattr(func, "name", func.__name__)
            decision = self.gate.evaluate(tool_name=tool_name, arguments=kwargs)

            if not decision.allowed:
                raise PermissionError(
                    f"ActionGate blocked tool '{tool_name}': {decision.reason} [receipt={decision.receipt_hash}]"
                )

            if decision.simulation_mode:
                return {
                    "simulation_mode": True,
                    "disposition": "simulate",
                    "tool": tool_name,
                    "receipt_hash": decision.receipt_hash,
                    "message": "Simulated tool execution (no state mutation occurred).",
                }

            return func(*args, **kwargs)

        return wrapper
