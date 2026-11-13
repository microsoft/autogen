"""
Agoragentic × AutoGen (AgentChat) — Marketplace Router Example

Route tasks through the Agoragentic capability router. The router finds
the best provider and settles payment in USDC on Base L2.

Install:
    pip install "autogen-agentchat" "autogen-ext[openai]" requests

Run:
    export AGORAGENTIC_API_KEY="amk_your_key"
    export OPENAI_API_KEY="sk-..."
    python main.py
"""

import asyncio
import json
import os

import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

AGORAGENTIC_API = "https://agoragentic.com"
API_KEY = os.environ.get("AGORAGENTIC_API_KEY", "")


def _headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }


async def agoragentic_execute(task: str, input_json: str = "{}", max_cost: float = 1.0) -> str:
    """Route a task to the best provider on the Agoragentic marketplace.

    The router finds, scores, and invokes the highest-ranked provider.
    Payment is automatic in USDC on Base L2.

    Args:
        task: What you need done (e.g., "summarize", "translate").
        input_json: JSON string with the input payload for the provider.
        max_cost: Maximum price in USDC you're willing to pay per call.
    """
    try:
        resp = requests.post(
            f"{AGORAGENTIC_API}/api/execute",
            json={
                "task": task,
                "input": json.loads(input_json) if isinstance(input_json, str) else input_json,
                "constraints": {"max_cost": max_cost},
            },
            headers=_headers(),
            timeout=60,
        )
        data = resp.json()
        if resp.status_code == 200:
            return json.dumps({
                "status": data.get("status"),
                "provider": data.get("provider", {}).get("name"),
                "output": data.get("output"),
                "cost_usdc": data.get("cost"),
            }, indent=2)
        return json.dumps({"error": data.get("error"), "message": data.get("message")})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def agoragentic_match(task: str, max_cost: float = 1.0) -> str:
    """Preview which providers the router would select — dry run, no charge.

    Args:
        task: What you need done.
        max_cost: Budget cap in USDC.
    """
    try:
        resp = requests.get(
            f"{AGORAGENTIC_API}/api/execute/match",
            params={"task": task, "max_cost": max_cost},
            headers=_headers(),
            timeout=15,
        )
        data = resp.json()
        providers = [
            {"name": p["name"], "price": p["price"], "score": p["score"]["composite"]}
            for p in data.get("providers", [])[:5]
        ]
        return json.dumps(
            {"task": task, "matches": data.get("matches"), "top_providers": providers},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    agent = AssistantAgent(
        name="marketplace_agent",
        model_client=model_client,
        tools=[agoragentic_execute, agoragentic_match],
        system_message=(
            "You are an AI agent with access to the Agoragentic capability marketplace. "
            "When asked to perform a task, use agoragentic_execute to route it to the best "
            "available provider. Use agoragentic_match first if the user wants to preview "
            "options before committing. Report the result clearly."
        ),
        reflect_on_tool_use=True,
    )

    await Console(
        agent.run_stream(
            task="Find the best provider to summarize text, then summarize this: "
                 "'Agoragentic is an API-first marketplace where AI agents discover, "
                 "invoke, and pay for services from other agents using USDC on Base L2.'"
        )
    )

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
