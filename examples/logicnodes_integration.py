"""
LogicNodes MCP Integration for AutoGen
======================================
Demonstrates how to connect AutoGen agents to LogicNodes — a deterministic
compute layer providing 2,300+ cryptographically-signed microservices for
autonomous agents (gas oracles, USDC balances, ZK attestation, compliance
sentries, DeFi quotes, and more).

Install:
    pip install pyautogen mcp

Usage:
    export LOGICNODES_API_KEY="your_key_from_https://logicnodes.io/checkout"
    python examples/logicnodes_integration.py
"""

import asyncio
import os
from typing import Any

# AutoGen imports
import autogen
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent

# MCP client (pip install mcp)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

LOGICNODES_API_KEY = os.environ.get("LOGICNODES_API_KEY", "")
LOGICNODES_MCP_URL = "https://logicnodes.io/mcp"

# ---------------------------------------------------------------------------
# Option A: Direct REST calls via AutoGen function tools (no MCP server needed)
# ---------------------------------------------------------------------------

import requests

def logicnodes_gas_oracle(chain: str = "ethereum") -> dict:
    """
    Query the LogicNodes gas oracle for deterministic EIP-1559 gas estimates.
    Returns cryptographically-signed base fee + priority fee data.
    """
    headers = {}
    if LOGICNODES_API_KEY:
        headers["Authorization"] = f"Bearer {LOGICNODES_API_KEY}"
    resp = requests.post(
        "https://logicnodes.io/call/gas-oracle",
        json={"chain": chain},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def logicnodes_compliance_sentry(agent_id: str, action: str) -> dict:
    """
    Run a compliance check via the LogicNodes compliance sentry worker.
    Returns an on-chain verifiable compliance attestation.
    """
    headers = {}
    if LOGICNODES_API_KEY:
        headers["Authorization"] = f"Bearer {LOGICNODES_API_KEY}"
    resp = requests.post(
        "https://logicnodes.io/call/compliance-sentry",
        json={"agent_id": agent_id, "action": action},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def logicnodes_eth_price() -> dict:
    """Fetch the current ETH/USD price from LogicNodes (cryptographically signed)."""
    headers = {}
    if LOGICNODES_API_KEY:
        headers["Authorization"] = f"Bearer {LOGICNODES_API_KEY}"
    resp = requests.get(
        "https://logicnodes.io/call/eth-price",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def logicnodes_zk_attest(content: str) -> dict:
    """
    Anchor content via LogicNodes ZK attestation.
    Returns a verifiable on-chain proof of existence.
    """
    headers = {}
    if LOGICNODES_API_KEY:
        headers["Authorization"] = f"Bearer {LOGICNODES_API_KEY}"
    resp = requests.post(
        "https://logicnodes.io/x402/zk-attest",
        json={"content": content},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Build AutoGen agents with LogicNodes tools
# ---------------------------------------------------------------------------

# LLM config — replace with your preferred model
llm_config = {
    "config_list": [
        {
            "model": "gpt-4o",
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
        }
    ],
    "functions": [
        {
            "name": "logicnodes_gas_oracle",
            "description": (
                "Query the LogicNodes gas oracle for deterministic EIP-1559 gas "
                "estimates on Ethereum or compatible chains. Returns a "
                "cryptographically-signed payload with base fee and priority fee."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chain": {
                        "type": "string",
                        "description": "Chain name, e.g. 'ethereum', 'base', 'polygon'",
                        "default": "ethereum",
                    }
                },
                "required": [],
            },
        },
        {
            "name": "logicnodes_compliance_sentry",
            "description": (
                "Run an on-chain compliance check for an autonomous agent action "
                "using the LogicNodes compliance sentry. Returns a verifiable "
                "attestation of whether the action is permitted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Unique identifier for the agent being checked.",
                    },
                    "action": {
                        "type": "string",
                        "description": "Description of the action to compliance-check.",
                    },
                },
                "required": ["agent_id", "action"],
            },
        },
        {
            "name": "logicnodes_eth_price",
            "description": "Fetch the current ETH/USD price from LogicNodes (signed output).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "logicnodes_zk_attest",
            "description": (
                "Anchor arbitrary content on-chain via LogicNodes ZK attestation. "
                "Returns a verifiable proof of existence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text or JSON content to anchor.",
                    }
                },
                "required": ["content"],
            },
        },
    ],
}

# Map function names to callables
function_map = {
    "logicnodes_gas_oracle": logicnodes_gas_oracle,
    "logicnodes_compliance_sentry": logicnodes_compliance_sentry,
    "logicnodes_eth_price": logicnodes_eth_price,
    "logicnodes_zk_attest": logicnodes_zk_attest,
}


def build_agents():
    """Instantiate an AutoGen AssistantAgent + UserProxyAgent with LogicNodes tools."""

    assistant = AssistantAgent(
        name="LogicNodesAgent",
        system_message=(
            "You are an autonomous on-chain agent powered by LogicNodes deterministic "
            "compute. Before executing any transaction, call logicnodes_compliance_sentry "
            "to verify compliance. Use logicnodes_gas_oracle to price transactions and "
            "logicnodes_eth_price for current ETH value. Anchor important decisions with "
            "logicnodes_zk_attest."
        ),
        llm_config=llm_config,
    )

    user_proxy = UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", ""),
        function_map=function_map,
        code_execution_config=False,
    )

    return assistant, user_proxy


# ---------------------------------------------------------------------------
# Option B: LogicNodes via MCP stdio server (npx @logicnodes/mcp-server)
# ---------------------------------------------------------------------------

async def run_with_mcp_server():
    """
    Alternative: connect AutoGen to LogicNodes via the official MCP server.

    Requires Node.js installed. The npx command downloads and runs
    @logicnodes/mcp-server which exposes all 2,300+ workers as MCP tools.
    """
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@logicnodes/mcp-server"],
        env={"LOGICNODES_API_KEY": LOGICNODES_API_KEY},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"LogicNodes MCP tools available: {len(tools.tools)}")
            for tool in tools.tools[:5]:
                print(f"  - {tool.name}: {tool.description[:60]}...")

            # Example: call gas oracle via MCP
            result = await session.call_tool(
                "gas-oracle", arguments={"chain": "ethereum"}
            )
            print("Gas oracle result:", result)


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    print("=== LogicNodes + AutoGen Integration Demo ===\n")

    # Direct REST demo (no MCP server needed)
    assistant, user_proxy = build_agents()

    user_proxy.initiate_chat(
        assistant,
        message=(
            "Check the current ETH price and gas oracle for Ethereum. "
            "Then run a compliance check for agent 'demo-agent-001' performing "
            "a 'transfer 0.5 ETH' action. Summarize the results. TERMINATE when done."
        ),
    )


if __name__ == "__main__":
    main()

    # Uncomment to use MCP server instead:
    # asyncio.run(run_with_mcp_server())
