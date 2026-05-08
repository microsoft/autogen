# Copyright (c) Microsoft. All rights reserved.
# SPDX-License-Identifier: MIT
#
# This sample requires:
#   pip install "autogen-agentchat" "autogen-ext[openai]" "hdp-autogen>=0.1.3" pyyaml
#
# See README.md for key generation and model_config.yaml setup.

"""
HDP Delegation Provenance — Single Agent with Scope Enforcement

Demonstrates HDP attached to a single AssistantAgent. The middleware records
every tool call as a delegation hop and optionally raises on scope violations.

Reference: https://helixar.ai/about/labs/hdp/
Package:   https://pypi.org/project/hdp-autogen/
"""

import asyncio
import base64
import os
import sys

import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import FunctionTool
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hdp_autogen import HdpMiddleware, HdpPrincipal, ScopePolicy, verify_chain


def _load_model_client() -> ChatCompletionClient:
    config_path = os.path.join(os.path.dirname(__file__), "model_config.yaml")
    if not os.path.exists(config_path):
        print("ERROR: model_config.yaml not found. See README.md for setup.")
        sys.exit(1)
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return ChatCompletionClient.load_component(config)


def _load_signing_key() -> Ed25519PrivateKey:
    raw_b64 = os.getenv("HDP_SIGNING_KEY")
    if not raw_b64:
        print("ERROR: HDP_SIGNING_KEY not set. See README.md.")
        sys.exit(1)
    raw = base64.urlsafe_b64decode(raw_b64 + "==")
    return Ed25519PrivateKey.from_private_bytes(raw)


# ── Tools available to the agent ──────────────────────────────────────────


def fetch_sales_data(region: str, quarter: str) -> str:
    """Simulate fetching sales data for a region and quarter."""
    return f"[MOCK] Sales data for {region} in {quarter}: revenue $2.4M, units 1,200."


def write_report(title: str, content: str) -> str:
    """Simulate writing a report to a file."""
    return f"[MOCK] Report '{title}' written ({len(content)} chars)."


async def main() -> None:
    private_key = _load_signing_key()
    model_client = _load_model_client()

    # ── HDP: declare what the human is authorising ─────────────────────────
    #
    # authorized_tools lists the tool names this agent is permitted to use.
    # In strict=True mode, any tool call outside this list raises immediately.
    # In default mode, violations are logged and recorded in the token for audit.
    middleware = HdpMiddleware(
        signing_key=private_key.private_bytes_raw(),
        session_id="sales-analysis-2026-q1",
        principal=HdpPrincipal(id="analyst@corp.example.com", id_type="email"),
        scope=ScopePolicy(
            intent="Analyse Q1 EMEA sales and write a one-page summary",
            authorized_tools=["fetch_sales_data", "write_report"],
            data_classification="confidential",
            network_egress=False,
            persistence=True,
            max_hops=5,
        ),
        strict=False,  # set True to raise HDPScopeViolationError on violations
    )

    agent = AssistantAgent(
        name="sales_analyst",
        model_client=model_client,
        tools=[
            FunctionTool(fetch_sales_data, description="Fetch sales data for a region and quarter."),
            FunctionTool(write_report, description="Write a report to a file."),
        ],
        system_message=(
            "You are a sales analyst. Use fetch_sales_data to retrieve data, "
            "then use write_report to save a concise one-page summary."
        ),
    )

    # ── Attach HDP — zero changes to agent ────────────────────────────────
    middleware.configure(agent)

    print("Running agent with HDP scope enforcement...\n")
    await Console(
        agent.run_stream(
            task="Analyse Q1 EMEA sales and produce a one-page written summary."
        )
    )

    # ── Offline verification ───────────────────────────────────────────────
    token = middleware.export_token()
    if token is None:
        print("\n[HDP] No token issued.")
        return

    result = verify_chain(token, private_key.public_key())

    print("\n" + "=" * 60)
    print("HDP Delegation Chain Verification")
    print("=" * 60)
    print(f"  Valid:      {result.valid}")
    print(f"  Hops:       {result.hop_count}")
    print(f"  Intent:     {token['scope']['intent']}")
    print(f"  Classification: {token['scope']['data_classification']}")

    if result.violations:
        print(f"\n  Violations ({len(result.violations)}):")
        for v in result.violations:
            print(f"    - {v}")

    print("=" * 60)
    print(
        "\n[HDP] See https://helixar.ai/about/labs/hdp/ for the protocol spec\n"
        "      and https://github.com/Helixar-AI/HDP for the full SDK."
    )


if __name__ == "__main__":
    asyncio.run(main())
