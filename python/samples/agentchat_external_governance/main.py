"""Demonstrate an external governance checkpoint around an AutoGen tool call.

The sample uses ReplayChatCompletionClient so it can run without a model API
key. Replace the mock checkpoint with EXTERNAL_GOVERNANCE_URL to call a real
policy or approval service before executing high-risk tools.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import urllib.request
from typing import Any, Literal, TypedDict

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import FunctionCall
from autogen_core.models import CreateResult, RequestUsage
from autogen_core.tools import FunctionTool
from autogen_ext.models.replay import ReplayChatCompletionClient


class GovernanceActionEnvelope(TypedDict):
    action_hash: str
    tool_name: str
    proposed_action: str
    arguments: dict[str, Any]


class GovernanceDecision(TypedDict):
    verdict: Literal["allow", "require_approval", "deny"]
    reason: str
    decision_id: str
    action_hash: str


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_action_envelope(
    *,
    account_id: str,
    destination: str,
    record_limit: int,
    contains_pii: bool,
) -> GovernanceActionEnvelope:
    tool_name = "governed_export_customer_records"
    arguments = {
        "account_id": account_id,
        "destination": destination,
        "record_limit": record_limit,
        "contains_pii": contains_pii,
    }
    proposed_action = (
        f"Export up to {record_limit} customer records for account "
        f"{account_id} to {destination}."
    )
    action_hash = sha256(
        stable_json(
            {
                "tool_name": tool_name,
                "proposed_action": proposed_action,
                "arguments": arguments,
            }
        )
    )
    return {
        "action_hash": action_hash,
        "tool_name": tool_name,
        "proposed_action": proposed_action,
        "arguments": arguments,
    }


async def call_external_governance(
    envelope: GovernanceActionEnvelope,
) -> GovernanceDecision:
    endpoint = os.environ.get("EXTERNAL_GOVERNANCE_URL")
    if endpoint:
        body = stable_json(envelope).encode("utf-8")

        def send_request() -> GovernanceDecision:
            request = urllib.request.Request(
                endpoint,
                data=body,
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)

        return await asyncio.to_thread(send_request)

    high_risk = (
        bool(envelope["arguments"]["contains_pii"])
        or int(envelope["arguments"]["record_limit"]) > 10
    )
    verdict: Literal["allow", "require_approval"] = (
        "require_approval" if high_risk else "allow"
    )

    return {
        "verdict": verdict,
        "reason": (
            "Customer data export requires approval."
            if high_risk
            else "The proposed action is within the local low-risk policy."
        ),
        "decision_id": f"local-{envelope['action_hash'][:12]}",
        "action_hash": envelope["action_hash"],
    }


async def governed_export_customer_records(
    account_id: str,
    destination: str,
    record_limit: int,
    contains_pii: bool,
) -> dict[str, str | int | bool]:
    envelope = build_action_envelope(
        account_id=account_id,
        destination=destination,
        record_limit=record_limit,
        contains_pii=contains_pii,
    )
    decision = await call_external_governance(envelope)

    print("\nExternal governance decision")
    print(f"- verdict: {decision['verdict']}")
    print(f"- decision_id: {decision['decision_id']}")
    print(f"- action_hash: {decision['action_hash']}")
    print(f"- reason: {decision['reason']}\n")

    if decision["verdict"] == "deny":
        return {
            "status": "blocked",
            "executed": False,
            "decision_id": decision["decision_id"],
            "action_hash": decision["action_hash"],
            "reason": decision["reason"],
        }

    if (
        decision["verdict"] == "require_approval"
        and os.environ.get("AUTO_APPROVE_EXTERNAL_GOVERNANCE") != "1"
    ):
        return {
            "status": "approval_required",
            "executed": False,
            "decision_id": decision["decision_id"],
            "action_hash": decision["action_hash"],
            "reason": decision["reason"],
        }

    return {
        "status": "executed",
        "executed": True,
        "decision_id": decision["decision_id"],
        "action_hash": decision["action_hash"],
        "account_id": account_id,
        "destination": destination,
        "record_limit": record_limit,
    }


async def main() -> None:
    tool = FunctionTool(
        governed_export_customer_records,
        name="governed_export_customer_records",
        description=(
            "Build an action envelope, review it with an external governance "
            "checkpoint, and export customer records only if allowed."
        ),
    )

    model_client = ReplayChatCompletionClient(
        chat_completions=[
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(
                        id="call_1",
                        name="governed_export_customer_records",
                        arguments=stable_json(
                            {
                                "account_id": "acme-123",
                                "destination": "internal-compliance-drive",
                                "record_limit": 25,
                                "contains_pii": True,
                            }
                        ),
                    )
                ],
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            (
                "The export was not executed. The governance checkpoint "
                "returned approval_required, so the workflow should pause "
                "until an authorized reviewer approves the action."
            ),
        ],
        model_info={
            "family": "gpt-4.1-nano",
            "function_calling": True,
            "json_output": True,
            "vision": False,
            "structured_output": True,
        },
    )

    agent = AssistantAgent(
        "governed_operations_agent",
        model_client=model_client,
        tools=[tool],
        reflect_on_tool_use=True,
        system_message=(
            "You help operations teams handle customer data exports. "
            "Use governed tools before taking any action that touches "
            "customer data."
        ),
    )

    await Console(
        agent.run_stream(
            task=(
                "Export 25 customer records for account acme-123 to the "
                "internal compliance drive. The export contains PII."
            )
        )
    )

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
