# Copyright (c) Microsoft. All rights reserved.
# SPDX-License-Identifier: MIT
#
# This sample requires:
#   pip install "autogen-agentchat" "autogen-ext[openai]" "hdp-autogen>=0.1.3" pyyaml
#
# Before running, export your Ed25519 signing key:
#   python -c "
#   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
#   import base64; k = Ed25519PrivateKey.generate()
#   print('HDP_SIGNING_KEY=' + base64.urlsafe_b64encode(k.private_bytes_raw()).decode())
#   "
#   export HDP_SIGNING_KEY=<value>
#
# Create model_config.yaml in this directory — see README.md for format.

"""
HDP Delegation Provenance — Multi-Agent Group Chat

Demonstrates how to attach a cryptographic audit trail to an AutoGen
RoundRobinGroupChat. Every speaker turn is recorded as a delegation hop
signed with Ed25519. The full chain is verifiable offline after the session.

HDP answers the question: "Which human authorised this agent action,
through what delegation chain, and with what scope?"

Reference: https://helixar.ai/about/labs/hdp/
Package:   https://pypi.org/project/hdp-autogen/
"""

import asyncio
import base64
import os
import sys

import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# HDP middleware — pip install hdp-autogen
# Docs: https://github.com/Helixar-AI/HDP/tree/main/packages/hdp-autogen
from hdp_autogen import HdpMiddleware, HdpPrincipal, ScopePolicy, verify_chain


def _load_model_client() -> ChatCompletionClient:
    """Load model client from model_config.yaml in this directory."""
    config_path = os.path.join(os.path.dirname(__file__), "model_config.yaml")
    if not os.path.exists(config_path):
        print("ERROR: model_config.yaml not found. See README.md for setup.")
        sys.exit(1)
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return ChatCompletionClient.load_component(config)


def _load_signing_key() -> Ed25519PrivateKey:
    """Load Ed25519 private key from HDP_SIGNING_KEY env var (base64url)."""
    raw_b64 = os.getenv("HDP_SIGNING_KEY")
    if not raw_b64:
        print(
            "ERROR: HDP_SIGNING_KEY environment variable not set.\n"
            "Generate one with:\n"
            "  python -c \"\n"
            "  from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey\n"
            "  import base64; k = Ed25519PrivateKey.generate()\n"
            "  print('HDP_SIGNING_KEY=' + base64.urlsafe_b64encode(k.private_bytes_raw()).decode())\n"
            "  \"\n"
            "  export HDP_SIGNING_KEY=<value>"
        )
        sys.exit(1)
    raw = base64.urlsafe_b64decode(raw_b64 + "==")
    return Ed25519PrivateKey.from_private_bytes(raw)


async def main() -> None:
    private_key = _load_signing_key()
    model_client = _load_model_client()

    # ── 1. Define what the human is authorising ────────────────────────────
    middleware = HdpMiddleware(
        signing_key=private_key.private_bytes_raw(),
        session_id="research-session-2026",
        principal=HdpPrincipal(id="researcher@example.com", id_type="email"),
        scope=ScopePolicy(
            intent="Research recent LLM papers and write a concise summary",
            authorized_tools=["web_search"],
            max_hops=10,
        ),
    )

    # ── 2. Build agents as normal ──────────────────────────────────────────
    researcher = AssistantAgent(
        name="researcher",
        model_client=model_client,
        system_message=(
            "You are a research assistant. Find key themes in recent LLM papers "
            "and present them as bullet points."
        ),
    )

    writer = AssistantAgent(
        name="writer",
        model_client=model_client,
        system_message=(
            "You are a technical writer. Turn the researcher's bullet points into "
            "a clear, concise two-paragraph summary."
        ),
    )

    team = RoundRobinGroupChat(
        participants=[researcher, writer],
        termination_condition=MaxMessageTermination(max_messages=4),
    )

    # ── 3. Attach HDP — one call, zero changes to agents or team ──────────
    middleware.configure(team)

    # ── 4. Run the team ────────────────────────────────────────────────────
    print("Running group chat with HDP delegation tracking...\n")
    await Console(team.run_stream(task="Summarise key themes in LLM papers from early 2026."))

    # ── 5. Verify the delegation chain offline ─────────────────────────────
    token = middleware.export_token()
    if token is None:
        print("\n[HDP] No token issued — did the team produce any messages?")
        return

    result = verify_chain(token, private_key.public_key())

    print("\n" + "=" * 60)
    print("HDP Delegation Chain Verification")
    print("=" * 60)
    print(f"  Valid:      {result.valid}")
    print(f"  Hops:       {result.hop_count}")
    print(f"  Session:    {token['header']['session_id']}")
    print(f"  Principal:  {token['principal']['display_name']}")
    print(f"  Intent:     {token['scope']['intent']}")

    if result.violations:
        print(f"\n  Violations ({len(result.violations)}):")
        for v in result.violations:
            print(f"    - {v}")
    else:
        print("  Violations: none")

    print("\n  Per-hop results:")
    for hop in result.hop_results:
        status = "✓" if hop.valid else "✗"
        print(f"    {status} Hop {hop.seq}: {hop.agent_id}")

    print("=" * 60)

    if not result.valid:
        print("\n[HDP] WARNING: chain verification failed — see violations above.")
        sys.exit(1)

    print(
        "\n[HDP] Chain verified. Token is suitable for audit storage.\n"
        "      See https://helixar.ai/about/labs/hdp/ for the full protocol spec."
    )


if __name__ == "__main__":
    asyncio.run(main())
