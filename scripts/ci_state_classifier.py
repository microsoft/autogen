#!/usr/bin/env python3
"""Classify GitHub check states into deterministic triage categories."""

from __future__ import annotations

import json
import sys
from typing import Any

_PENDING = {"pending", "queued", "in_progress", "requested", "waiting"}
_FAILED = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
_POLICY = {
    "resource not accessible by integration",
    "insufficient permission",
    "insufficient permissions",
    "not authorized",
    "forbidden",
    "cla",
}


def classify(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "no checks"

    policy_blocked = False
    failed = False
    pending = False

    for check in checks:
        status = str(check.get("status", "")).lower()
        conclusion = str(check.get("conclusion", "")).lower()
        summary = " ".join(
            str(check.get(key, "")) for key in ("name", "context", "details", "title", "summary", "text")
        ).lower()

        if any(marker in summary for marker in _POLICY):
            policy_blocked = True

        if status in _PENDING:
            pending = True
        if conclusion in _FAILED:
            failed = True

    if policy_blocked:
        return "policy-blocked"
    if failed:
        return "failed"
    if pending:
        return "pending"
    return "passed"


def main() -> int:
    payload = json.load(sys.stdin)
    checks = payload if isinstance(payload, list) else payload.get("checks", [])
    print(json.dumps({"state": classify(checks)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
