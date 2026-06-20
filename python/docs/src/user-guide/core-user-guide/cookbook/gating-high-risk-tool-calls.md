# Gating high-risk tool calls

Agents that can use tools to move money, change infrastructure, or call production APIs should not rely on a separate "check first" instruction alone. The safer pattern is to put the check inside the tool that performs the action, so the action fails closed even if the model forgets to call a safety tool.

This recipe uses a DeFi token swap as the example because token safety checks are a common pre-flight step for trading agents. The same pattern applies to any high-risk action: validate the requested action, return a structured block reason when validation fails, and only then build or execute the action.

```python
from dataclasses import dataclass
from typing import Literal

from autogen_core import CancellationToken
from autogen_core.tools import FunctionTool


@dataclass(frozen=True)
class TokenSafetyReport:
    token_address: str
    chain: str
    safety_score: int
    verdict: Literal["allow", "block"]
    reasons: list[str]


@dataclass(frozen=True)
class SwapRequest:
    token_address: str
    chain: str
    amount: float
    safety_score: int
    status: Literal["ready"]


# In production, replace this deterministic example with a scanner you control,
# a vetted provider, or your own on-chain simulation. Keep the schema stable so
# the action tool can make a simple allow/block decision.
def scan_token_safety(token_address: str, chain: str = "base") -> TokenSafetyReport:
    """Return a token safety report before a trading tool prepares a swap."""
    blocked_tokens = {"0x0000000000000000000000000000000000000000"}
    if token_address.lower() in blocked_tokens:
        return TokenSafetyReport(
            token_address=token_address,
            chain=chain,
            safety_score=0,
            verdict="block",
            reasons=["token address is on the local blocklist"],
        )

    return TokenSafetyReport(
        token_address=token_address,
        chain=chain,
        safety_score=95,
        verdict="allow",
        reasons=[],
    )


def create_swap_request(token_address: str, amount: float, chain: str = "base") -> SwapRequest:
    """Create a swap request only after the token passes the safety gate."""
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    report = scan_token_safety(token_address=token_address, chain=chain)
    if report.verdict != "allow" or report.safety_score < 80:
        reason = "; ".join(report.reasons) or "safety score is below the required threshold"
        raise ValueError(f"blocked unsafe token swap: {reason}")

    return SwapRequest(
        token_address=token_address,
        chain=chain,
        amount=amount,
        safety_score=report.safety_score,
        status="ready",
    )


scan_token_safety_tool = FunctionTool(
    scan_token_safety,
    description="Check token safety before a DeFi agent considers a swap.",
)
create_swap_request_tool = FunctionTool(
    create_swap_request,
    description="Create a DeFi swap request after enforcing the token safety gate.",
)


async def main() -> None:
    safe_request = await create_swap_request_tool.run_json(
        {"token_address": "0x1111111111111111111111111111111111111111", "amount": 1.0},
        CancellationToken(),
    )
    assert isinstance(safe_request, SwapRequest)
    assert safe_request.status == "ready"

    try:
        await create_swap_request_tool.run_json(
            {"token_address": "0x0000000000000000000000000000000000000000", "amount": 1.0},
            CancellationToken(),
        )
    except ValueError as exc:
        assert "blocked unsafe token swap" in str(exc)
    else:
        raise AssertionError("unsafe token swap was not blocked")
```

You can expose both tools to an agent: the scanner tool gives the model explainable risk information, and the action tool enforces the gate. The enforcement belongs in the action tool because model instructions are advisory, while tool code is a hard boundary.

For real deployments:

- Treat third-party scanner output as untrusted input. Validate its schema, set request timeouts, and decide whether scanner outages should block or require human approval.
- Keep a local denylist for known unsafe assets and emergency shutdowns.
- Log the safety report alongside the proposed action so a human reviewer can audit why the agent proceeded or stopped.
- Require a human approval step for large trades or newly observed tokens even when the score is above the threshold.
